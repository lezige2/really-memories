# -*- coding: utf-8 -*-
"""M3 -- Python-side pin table for memory blocks.

Why this file exists
--------------------
The engine does NOT refuse `reset()` on a block sequence that the dialogue still references.
Measured (run_m3_50.json, pin_test): the call returns normally with no exception and no error
code; the block's own sequence goes 21 cells -> 0 while the dialogue keeps its 51 shared cells
and still answers correctly. So the danger is not immediate corruption -- it is the SILENT loss
of the block's handle: the next `share(block_seq, ...)` attaches nothing, the dialogue loses the
memory, and the model answers from thin air (that is exactly how run 1 of this experiment
produced 74 minutes of worthless data: every round attached 0 cells).

The DLL is not patched on purpose: rebuilding it would change the measured sha 9edbafa1... and
invalidate every baseline recorded tonight. The guard therefore lives here.

Correct order (tools/chat.py does this): drop the dialogue reference FIRST, then reset the block
sequence, then reload it from its pristine file. This module makes the wrong order fail loudly
instead of silently.
"""
from __future__ import annotations

import functools
import json
import time


class LeaseError(RuntimeError):
    """Raised when something tries to reset a block sequence that is still referenced."""


# M6a-fix I2: 移动被共享块的位置 = 静默改所有 referrer 的位置窗口（M6A-PROBE 实证）。
# 守卫是 fail-closed 的：默认在 BlockLeases 构造期装上；装不上 = 构造失败（raise）。
# 唯一的关闭方式是显式构造参数 `move_guard=False`（只给变体红证脚本；product 路径不传）。
# （旧的环境变量缝已删：env 里出现一个值就能全局静默关守卫，且不落 move_refusals。）


class BlockLeases:
    """Tracks who references which block cells, and gates destructive resets.

    Only `attach`/`detach` may touch block cells; `reset` refuses while any lease is live.

    `strict`（默认 True，L2 起）**只影响是否 raise**：`detach` 未命中 `ranges` 时，记账
    （`unbooked_count` + `unbooked_detach` 事件）在**两种模式都不关**，可观测性不受 strict 影响；
    strict=False 只是把「拒绝 + 不 drop」降级为「留痕 + 照旧 drop」，用于兼容旧调用序列。
    """

    def __init__(self, eng, log=None, strict=True, move_guard=True):
        self.eng = eng
        self.log = log
        self.strict = bool(strict)             # L2: 未命中 detach 默认抛错（不是静默 pass）
        self.move_guard = bool(move_guard)     # M6a-fix I2：装/不装共享-cell 移动守卫
        self.guard_installed = False
        self.guard_install_note = None
        self.blocks = {}                       # block_seq -> block_id
        self.holders = {}                      # block_seq -> {dst_seq, ...}
        self.ranges = {}                       # (dst_seq, lo, hi) -> block_seq
        self.unbooked_count = 0                # L2: 未命中 detach 的累计次数（初值 0，不是 None）
        self.events = []
        # M6a-fix I2：拒绝过的 move 记录（可见拒绝要能落到表字段，不能只在 try 里抛）
        self.move_refusals = []
        if self.move_guard:
            self.guard_installed = self._guard_engine_move()
        else:
            self._note("move_guard_disabled_by_ctor")

    # -- bookkeeping -------------------------------------------------------
    def _note(self, kind, **kw):
        self.events.append(dict(kind=kind, at=time.strftime("%H:%M:%S"), **kw))
        if self.log is not None:
            self.log.write("  [lease] %-8s %s\n" % (kind, json.dumps(kw, ensure_ascii=False)))

    def register_block(self, block_seq, block_id):
        self.blocks[int(block_seq)] = block_id
        self.holders.setdefault(int(block_seq), set())
        return self

    def referrers(self, block_seq):
        return sorted(self.holders.get(int(block_seq), ()))

    # -- M6a-fix I2: fail-closed move guard --------------------------------
    #
    # 事实（M6A-REACHABILITY I2 = 可达（未修），M6A-PROBE 实证）：seq_cp 同 stream 只做
    # `seq_add`，cell 同时属于块 seq 与对话 seq，无 refcount。块被 attach 之后若对块 seq
    # 调 `repos_local`，引擎会静默改掉所有 referrer 看到的位置窗口 —— 不报错、不返回失败。
    #
    # 为什么在**实例层**包住 `eng.repos_local`：product 的 move 调用点（tools/chat.py
    # :286/:394/:637/:1021）直接打在 `eng` 上，改 chat.py 不在本单写权限内，也不该
    # 为一个检查去动产品文件；包一层实例方法 = 引擎外部守卫，DLL/引擎一个字节不动
    # （理由同本模块开头：rebuild 会改 DLL sha、作废全部基线）。
    # 未注册块 / 没有 referrer / delta==0 ⇒ 原样放行；守卫装不上 = 构造失败（fail-closed）。
    def _guard_engine_move(self):
        eng = self.eng
        orig = getattr(eng, "repos_local", None)
        if orig is None:
            # 唯一不装守卫的情形：engine 根本没有 repos_local ⇒ product 调 eng.repos_local 会
            # AttributeError，不存在可被"静默绕过"的 move 路径（这本身是 fail-closed）。
            # 仍要可见：事件 + guard_installed=false 写进产物/台账。
            self.guard_install_note = ("engine %s has no repos_local (no move API; AttributeError "
                                       "if called)" % type(eng).__name__)
            self._note("move_guard_not_applicable", engine=type(eng).__name__)
            return False
        if not callable(orig):
            raise LeaseError(
                "M6a-fix I2 fail-closed: %s.repos_local exists but is not callable (%r); "
                "cannot install move guard [m3_lease.py:_guard_engine_move]"
                % (type(eng).__name__, orig))
        owner = getattr(orig, "_m3_move_guard_table", None)
        if owner is not None:
            # 同一 engine 已有表装过守卫：守卫语义已生效（幂等），记事件而不是静默返回。
            self.guard_installed = True
            self.guard_install_note = ("already guarded by table for %r (idempotent)"
                                       % (owner,))
            self._note("move_guard_already_installed", engine=type(eng).__name__)
            return True
        table = self

        @functools.wraps(orig)
        def guarded_repos_local(seq, delta, *a, **kw):
            table.check_move(seq, delta, *a, **kw)
            return orig(seq, delta, *a, **kw)

        guarded_repos_local._m3_move_guard_table = table
        guarded_repos_local._m3_move_guard_original = orig
        try:
            eng.repos_local = guarded_repos_local
        except Exception as exc:                            # noqa: BLE001
            raise LeaseError(
                "M6a-fix I2 fail-closed: cannot install move guard on %s (%s: %s); refusing to "
                "start unguarded [m3_lease.py:_guard_engine_move]"
                % (type(eng).__name__, type(exc).__name__, exc)) from exc
        self.guard_installed = True
        return True

    def check_move(self, seq, delta, p0=0, p1=-1):
        """Refuse to move a block sequence while any dialogue seq references its cells.

        The engine would happily move the shared cells (silent), so the only safe signal
        is this table: `holders[block_seq]` is exactly the set of referrers. Refusal is
        recorded on `move_refusals` BEFORE raising, so a caller that catches the error can
        still put `refused=true` + reason into its own artifact (判据不靠异常表达).
        """
        seq = int(seq)
        if delta == 0 or not self.move_guard:
            return None
        refs = self.referrers(seq)
        if not refs:
            return None
        block = self.blocks.get(seq, "?")
        ranges = sorted([[int(d), int(lo), int(hi)]
                         for (d, lo, hi), bseq in self.ranges.items() if bseq == seq])
        rec = {"seq": seq, "delta": int(delta), "p0": p0, "p1": p1,
               "block": block, "referrers": refs, "ranges": ranges}
        rec["reason"] = (
            "refusing repos_local(block seq %d %r, delta %+d, p0=%s, p1=%s): still referenced "
            "by dialogue seq(s) %s via attach range(s) %s. Moving shared cells would silently "
            "shift every referrer's position window (M6a I2). Detach first, or move before "
            "attaching. (Guard is fail-closed; only the variant arm constructs the table with "
            "move_guard=False.)"
            % (seq, block, int(delta), p0, p1, refs, ranges))
        self.move_refusals.append(rec)
        self._note("refused_move", **{k: rec[k] for k in
                                      ("seq", "delta", "block", "referrers", "ranges")})
        raise LeaseError(rec["reason"])

    def leased(self, block_seq):
        return bool(self.holders.get(int(block_seq)))

    # -- the two legal operations -----------------------------------------
    def attach(self, block_seq, dst_seq, lo, hi):
        block_seq, dst_seq = int(block_seq), int(dst_seq)
        lo, hi = int(lo), int(hi)
        if block_seq not in self.blocks:
            raise LeaseError("seq %d is not a registered block; register it first" % block_seq)
        if not self.cells_of(block_seq):
            raise LeaseError(
                "block %r (seq %d) is EMPTY, refusing to attach: this is the silent-loss "
                "signature -- reload it from its file before sharing"
                % (self.blocks[block_seq], block_seq))
        # M2 完整 L1（位置租约重叠校验）：同一 dst_seq 上两块区间相交 ⇒ 后者静默覆盖前者的
        # cells，而 `ranges` 只留后者键 ⇒ detach 前者时记账漂移。检查**必须在 eng.share
        # 之前**：拒绝不得先做破坏动作（holders / ranges 都不许变）。
        # 不同 dst_seq 的重叠合法（同一块挂多 seq 是 M2 并发形态）；同块同区间重放幂等。
        if self.ranges.get((dst_seq, lo, hi)) == block_seq:
            self._note("attach_replay", block=self.blocks[block_seq], block_seq=block_seq,
                       dst_seq=dst_seq, lo=lo, hi=hi)
            return
        for (kdst, klo, khi), kseq in sorted(self.ranges.items()):
            if kdst != dst_seq:
                continue
            if klo < hi and lo < khi:
                raise LeaseError(
                    "refusing attach(block %r seq %d) onto dst_seq %d at [%d,%d): it overlaps "
                    "an existing lease of block %r (seq %d) at [%d,%d). Different dst_seq may "
                    "overlap; same dst_seq must not (detach the old range first)."
                    % (self.blocks[block_seq], block_seq, dst_seq, lo, hi,
                       self.blocks.get(kseq, "?"), kseq, klo, khi))
        self.eng.share(block_seq, dst_seq, lo, hi)
        self.holders[block_seq].add(dst_seq)
        self.ranges[(dst_seq, int(lo), int(hi))] = block_seq
        self._note("attach", block=self.blocks[block_seq], block_seq=block_seq,
                   dst_seq=dst_seq, lo=lo, hi=hi)

    def detach(self, dst_seq, lo, hi):
        dst_seq, lo, hi = int(dst_seq), int(lo), int(hi)
        block_seq = self.ranges.get((dst_seq, lo, hi))
        # M2 完整 L2（记账一致性）：`ranges` 未命中时旧代码仍然 `eng.drop` ⇒ 静默丢引用、
        # 记账漂移查不出。未命中必须**先记账**（事件 + 计数），strict 下再抛错且**不 drop**；
        # 非 strict 保留旧行为（照 drop）但同样留痕，绝不静默。
        if block_seq is None:
            self.unbooked_count += 1
            self._note("unbooked_detach", dst_seq=dst_seq, lo=lo, hi=hi,
                       strict=self.strict)
            if self.strict:
                raise LeaseError(
                    "refusing detach(dst_seq %d, [%d,%d)): no such range is booked, so the "
                    "engine call would drop cells this table does not track (silent drift). "
                    "Check the detach/drop pair, or pass strict=False to log-and-drop."
                    % (dst_seq, lo, hi))
            self.eng.drop(dst_seq, lo, hi)
            return None
        self.ranges.pop((dst_seq, lo, hi), None)
        self.eng.drop(dst_seq, lo, hi)
        self.holders[block_seq].discard(dst_seq)
        self._note("detach", block=self.blocks[block_seq], block_seq=block_seq,
                   dst_seq=dst_seq, lo=lo, hi=hi)
        if not self.holders[block_seq]:
            self._note("released", block=self.blocks[block_seq], block_seq=block_seq)
        return block_seq

    # -- gated destruction -------------------------------------------------
    def reset(self, seq, force=False):
        seq = int(seq)
        refs = self.referrers(seq) if seq in self.blocks else []
        if refs and not force:
            raise LeaseError(
                "refusing reset(seq %d, block %r): still referenced by dialogue seq(s) %s. "
                "Detach first (detach-before-save), then reset, then reload from file. "
                "Pass force=True only if you accept losing the block handle."
                % (seq, self.blocks[seq], refs))
        if refs and force:
            self._note("force_reset", block=self.blocks[seq], seq=seq, refs=refs)
        self.eng.reset(seq)
        if seq in self.blocks:
            self._note("reset_block", block=self.blocks[seq], seq=seq, forced=bool(refs))
        return True

    def safe_reset_all(self, seqs, skip=()):
        """What the probe's reset_all should have been: never touches block seqs.

        The probe's helper is a bare loop over range(N_SEQ); on an attached engine that
        silently wipes every block slot.
        """
        skip = set(int(s) for s in skip) | set(self.blocks)
        done, skipped = [], []
        for s in seqs:
            if int(s) in skip:
                skipped.append(int(s))
                continue
            self.eng.reset(int(s))
            done.append(int(s))
        self._note("safe_reset_all", done=done, skipped=skipped)
        return {"reset": done, "skipped": skipped}

    # -- introspection -----------------------------------------------------
    def cells_of(self, seq):
        """Own-token count of a sequence. A loaded block reports its cells; a reset one 0."""
        try:
            return int(self.eng.n_tokens(int(seq)))
        except Exception:                                       # noqa: BLE001
            return 1                                            # unknown: do not block on it

    def status(self):
        return {"blocks": {self.blocks[s]: {"seq": s, "referrers": sorted(self.holders[s])}
                           for s in self.blocks},
                "any_leased": any(self.holders[s] for s in self.blocks),
                "move_refusals": list(self.move_refusals),
                "move_guard": self.move_guard,
                "guard_installed": self.guard_installed,
                "guard_install_note": self.guard_install_note}
