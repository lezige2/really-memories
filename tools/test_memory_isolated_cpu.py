#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""CPU-only unit tests for tools/memory_isolated.py (fake engine, zero GPU).

Run: python -X utf8 tools/test_memory_isolated_cpu.py
Exit: 0 all pass, 1 failure.
"""
import os
import sys

sys.dont_write_bytecode = True
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "tools"))

import memory_isolated as MI  # noqa: E402


class FakeEngine:
    """Minimal engine mirroring kvslots' sequence semantics.

    state[seq] = {pos: token_str}.  share() is zero-copy: dst receives references
    (copies the position map entries; the src can be reset afterwards).
    """

    def __init__(self, n_seq=8, blocks=None):
        self.n_seq = n_seq
        self.blocks = dict(blocks or {})     # path -> n_tokens
        self.state = {s: {} for s in range(n_seq)}
        self.calls = {"reset": [], "load": [], "repos": [], "share": [],
                      "ask": [], "write_at": []}
        self.fail_load_paths = set()
        self.answer_for = {}                 # path fragment -> answer

    # -- engine surface ---------------------------------------------------
    def reset(self, seq):
        self.calls["reset"].append(int(seq))
        self.state[int(seq)] = {}

    def load(self, seq, path):
        seq = int(seq)
        self.calls["load"].append((seq, path))
        if path in self.fail_load_paths:
            raise RuntimeError("fake incompatible block: %s" % path)
        self.reset(seq)                      # kvshim_load resets the seq first
        n = int(self.blocks[path])
        self.state[seq] = {i: "%s#%d" % (path, i) for i in range(n)}
        return n

    def repos_local(self, seq, delta, p0=0, p1=-1):
        seq = int(seq)
        self.calls["repos"].append((seq, int(delta), p0, p1))
        cell = self.state[seq]
        lo = 0 if p0 is None else int(p0)
        hi = (max(cell) + 1) if (p1 is None or int(p1) < 0) else int(p1)
        moved = 0
        new = {}
        for pos, tok in cell.items():
            if lo <= pos < hi:
                new[pos + int(delta)] = tok
                moved += 1
            else:
                new[pos] = tok
        self.state[seq] = new
        return moved

    def share(self, src, dst, lo, hi):
        src, dst, lo, hi = int(src), int(dst), int(lo), int(hi)
        self.calls["share"].append((src, dst, lo, hi))
        for pos, tok in self.state[src].items():
            if lo <= pos < hi:
                self.state[dst][pos] = tok

    def ask(self, seq, text, n_predict=32, pos=None):
        seq = int(seq)
        self.calls["ask"].append({"seq": seq, "text": text,
                                  "pos": None if pos is None else int(pos),
                                  "n_predict": int(n_predict)})
        # the answer is determined by the newest mounted block (max pos)
        cell = self.state[seq]
        if not cell:
            # 真实引擎在 pos=0 写入问题后仍会生成；fake 用固定串模拟"空上下文也能答"
            return "EMPTY_CTX_ANSWER" if pos == 0 else ""
        top_pos = max(cell)
        top_tok = cell[top_pos]
        for frag, ans in self.answer_for.items():
            if frag in top_tok:
                return ans
        return "UNKNOWN"

    def write_at(self, seq, text, pos):
        self.calls["write_at"].append((int(seq), text, int(pos)))
        self.state[int(seq)][int(pos)] = text

    def n_tokens(self, seq):
        return len(self.state[int(seq)])

    def pos_max(self, seq):
        cell = self.state[int(seq)]
        return max(cell) if cell else -1


def _row(sid, name, path, n):
    # memory_source.block_rows() tuple shape (only the used slots matter here)
    return (sid, name, name, "text of " + name, "hash", sid, path, n)


def _install_fake_loader(eng):
    """memory_isolated calls ms.load_into(eng,row,seq,model_path=...); patch it."""
    def fake_load_into(_eng, row, seq, model_path=None, kv_type="q8_0"):
        assert _eng is eng, "unexpected engine"
        return eng.load(seq, row[6])
    MI.ms.load_into = fake_load_into


def test_positions_and_isolation():
    blocks = {"old.kvmem": 5, "new.kvmem": 7}
    eng = FakeEngine(blocks=blocks)
    eng.answer_for = {"new.kvmem": "上海", "old.kvmem": "B座302"}
    _install_fake_loader(eng)
    rows = [_row(1, "old", "old.kvmem", 5), _row(2, "new", "new.kvmem", 7)]
    ans, prov = MI.answer_isolated(eng, rows, "下周三去哪开会", n_predict=64,
                                   scratch=6, model_path="fake.gguf")
    assert ans == "上海", ans
    assert prov["fallback"] is None
    assert prov["isolated_seq"] == 7 and prov["scratch_seq"] == 6
    assert [b["name"] for b in prov["blocks"]] == ["old", "new"]
    assert [(b["lo"], b["hi"]) for b in prov["blocks"]] == [(0, 5), (5, 12)]
    assert prov["question_pos"] == 12
    asks = eng.calls["ask"]
    assert len(asks) == 1 and asks[0]["seq"] == 7 and asks[0]["pos"] == 12
    assert asks[0]["text"] == "下周三去哪开会"      # no history, no prompt rewrite
    # cleanup: both sequences empty after the call
    assert eng.state[7] == {} and eng.state[6] == {}
    assert eng.calls["reset"][:2] == [7, 6], eng.calls["reset"]
    assert eng.calls["reset"][-2:] == [6, 7] or eng.calls["reset"][-2:] == [6, 7]
    # only seqs 6 and 7 were touched (no dialogue-seq writes)
    touched = set(eng.calls["reset"]) | {s for s, _ in eng.calls["load"]} \
        | {s for s, *_ in eng.calls["repos"]} \
        | {d for _s, d, _lo, _hi in eng.calls["share"]}
    assert touched <= {6, 7}, touched


def test_order_is_preserved():
    eng = FakeEngine(blocks={"a.kvmem": 3, "b.kvmem": 4})
    eng.answer_for = {"a.kvmem": "A", "b.kvmem": "B"}
    _install_fake_loader(eng)
    ans, prov = MI.answer_isolated(
        eng, [_row(1, "b", "b.kvmem", 4), _row(2, "a", "a.kvmem", 3)],
        "q", n_predict=8, scratch=6)
    assert ans == "A"                 # last mounted (highest pos) is a.kvmem
    assert [(b["lo"], b["hi"]) for b in prov["blocks"]] == [(0, 4), (4, 7)]


def test_failure_rolls_back():
    eng = FakeEngine(blocks={"old.kvmem": 5, "bad.kvmem": 3})
    eng.fail_load_paths.add("bad.kvmem")
    _install_fake_loader(eng)
    ans, prov = MI.answer_isolated(
        eng, [_row(1, "old", "old.kvmem", 5), _row(2, "bad", "bad.kvmem", 3)],
        "q", n_predict=8, scratch=6)
    assert ans is None
    assert prov["fallback"] == "normal_path"
    assert "fake incompatible block" in prov["error"]
    assert eng.state[7] == {} and eng.state[6] == {}
    assert eng.calls["ask"] == []      # never generated on a broken context


def test_token_count_mismatch_falls_back():
    eng = FakeEngine(blocks={"x.kvmem": 5})
    _install_fake_loader(eng)
    ans, prov = MI.answer_isolated(eng, [_row(1, "x", "x.kvmem", 99)],
                                   "q", n_predict=8, scratch=6)
    assert ans is None and prov["fallback"] == "normal_path"
    assert "token" in prov["error"]
    assert eng.state[7] == {} and eng.state[6] == {}


def test_empty_answer_falls_back():
    eng = FakeEngine(blocks={"empty.kvmem": 2})
    _install_fake_loader(eng)

    class NoAnswer(FakeEngine):
        def ask(self, seq, text, n_predict=32, pos=None):
            self.calls["ask"].append({"seq": int(seq), "text": text, "pos": pos})
            return ""
    eng2 = NoAnswer(blocks={"empty.kvmem": 2})
    _install_fake_loader(eng2)
    ans, prov = MI.answer_isolated(eng2, [_row(1, "e", "empty.kvmem", 2)],
                                   "q", n_predict=8, scratch=6)
    assert ans is None and prov["fallback"] == "normal_path"
    assert "empty answer" in prov["error"]
    assert eng2.state[7] == {} and eng2.state[6] == {}


def test_bad_arguments():
    eng = FakeEngine()
    for args in (
        ([_row(1, "x", "x.kvmem", 1)], "", 6),      # empty question
        ([_row(1, "x", "x.kvmem", 1)], "q", 7),     # scratch == isolated seq
    ):
        rows, q, scratch = args
        try:
            MI.answer_isolated(eng, rows, q, n_predict=4, scratch=scratch)
            raise AssertionError("expected ValueError for %r" % (args,))
        except ValueError:
            pass


def test_empty_rows_allowed():
    """空记忆 + 问题也要能隔离作答（no dialogue history）。"""
    eng = FakeEngine()
    ans, prov = MI.answer_isolated(eng, [], "q", n_predict=4, scratch=6, gen_seq=7)
    assert ans == "EMPTY_CTX_ANSWER" and prov["n_rows"] == 0
    assert eng.state[7] == {} and eng.state[6] == {}
    assert eng.calls["reset"][0] == 7


def main():
    tests = [test_positions_and_isolation, test_order_is_preserved,
             test_failure_rolls_back, test_token_count_mismatch_falls_back,
             test_empty_answer_falls_back, test_bad_arguments,
             test_empty_rows_allowed]
    failed = []
    for t in tests:
        try:
            t()
            print("PASS", t.__name__)
        except Exception as exc:  # noqa: BLE001
            failed.append((t.__name__, repr(exc)))
            print("FAIL", t.__name__, "->", repr(exc))
    print("\n%d/%d passed" % (len(tests) - len(failed), len(tests)))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())