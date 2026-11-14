# -*- coding: utf-8 -*-
"""scale40k 子库构建：分层抽样 200 块 → 插入独立 chat.db → 逐块 build_block。

只读 out/scale40k/{blocks_200,queries_100}.jsonl；写 dst/（独立 chat.db + blocks/）。
--dry-run 全程不加载模型、不建块，仅打印/落盘抽样与映射结果。

用法：
  python -X utf8 out/scale40k_build.py --n 20 --dst kvmem/scale40k/n20 --dry-run
  python -X utf8 out/scale40k_build.py --n 20 --dst kvmem/scale40k/n20
"""
import argparse
import json
import os
import random
import sqlite3
import sys
import unicodedata
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT, "out", "scale40k")
BLOCKS_SRC = os.path.join(SRC_DIR, "blocks_200.jsonl")
QUERIES_SRC = os.path.join(SRC_DIR, "queries_100.jsonl")
MANIFEST_SRC = os.path.join(SRC_DIR, "manifest.json")

SEED = 40000
NBINS = 5
DEFAULT_MODEL = os.environ.get("SCALE40K_MODEL") or \
    r"D:\models\Qwen2.5-14B-Instruct-Q4_K_M.gguf"
ENGINE_CFG = {"n_ctx": 32768, "n_seq": 8, "gpu": 28, "kv": "q8_0"}
BUILD_SEQ = 6
BASE_TS = datetime(2026, 10, 1, 9, 0, 0)      # 固定时间锚，保证可重复

# n -> (链数, 事实数, 噪声数)；链 = 完整 A→B→C→D 4 块
QUOTA = {
    20: (2, 9, 3),
    50: (5, 22, 8),
    100: (10, 45, 15),
    200: (10, 120, 40),
}
REVERSE_CHAINS = 2          # 反序用例：D 的 created_at 早于 C，但 id 更大
PAD_COUNT = 10              # 长块数量：优先序列前 10 块填到 ~800 token
PAD_CHARS = 800
QS_PER_BAND = 40            # 每档固定 40 条：30 正常 + 10 旧值负例

# 5 对“全角/空格差异”脏数据：norm 后完全相同，source_hash 不同 ->
# 用于证明 norm_hash 未实现（库里去重只看精确 sha256）。
DIRTY_PAIRS = [
    ("储物柜密码是 4821，别跟别人说。", "储物柜密码是　４８２１，别跟别人说。"),
    ("门禁卡号 A7-2231，前台登记过。", "门禁卡号 Ａ７－２２３１，前台登记过。"),
    ("快递放 3 号楼 2 层货架。", "快递放 ３号楼２层货架。"),
    ("会员号 KX7781，积分别过期。", "会员号 KX 7781，积分别过期。"),
    ("备用钥匙在 501 抽屉里。", "备用钥匙在 ５０１ 抽屉里。"),
]
FILLER = ("说到这儿我又想起一点别的，前几天收拾屋子翻出不少旧东西，扔了可惜留着又占地方，"
          "最后挑了几样收进箱子，剩下的都处理掉了。这两天天气反复，早上凉中午热，"
          "出门得多带一件外套，免得回来路上着凉。晚上打算早点睡，最近总觉得睡不够，"
          "白天脑子发沉，做事也慢半拍，还是得把作息调回来。")

# 链的 C 块原文是“再后来又换成…”，不含族关键词，k2_family 认不出族 → 反序用例失效。
# 反序链的 C 块在插入时补一句带族关键词的前缀（text override，不改产品代码）。
FAMILY_WORD = {"plate": "车牌号", "company": "公司", "phone": "手机号",
               "bank": "银行卡号", "meeting": "会议时间", "seat": "座位号",
               "car_color": "车身颜色"}

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# 读入
# ---------------------------------------------------------------------------
def load_jsonl(path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_manifest():
    if os.path.exists(MANIFEST_SRC):
        with open(MANIFEST_SRC, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def compact(s):
    """去掉空白/间隔符/常见标点，用于“同值不同写法”比对。"""
    out = []
    for ch in str(s or ""):
        if ch.isspace() or ch in "·-—–_.。,，、":
            continue
        out.append(ch)
    return "".join(out)


def variants(value):
    vs = []
    for v in (str(value or ""), compact(value)):
        if v and v not in vs:
            vs.append(v)
    return vs


# ---------------------------------------------------------------------------
# 分层抽样（固定 seed=40000）
# ---------------------------------------------------------------------------
def pos_bin(r):
    return min(NBINS - 1, int(float(r.get("position") or 0.0) * NBINS))


def chain_groups(blocks):
    groups = {}
    for r in blocks:
        if r.get("kind") == "chain" and r.get("chain_id"):
            groups.setdefault(r["chain_id"], []).append(r)
    for k in groups:
        groups[k].sort(key=lambda x: int(x.get("chain_seq") or 0))
    return groups


def choose_chains(groups, count, rng):
    """先定反序链（同族唯一、非 slot 族，保证 K2 真的会介入），再补足其余链。"""
    fam_count = {}
    for g in groups.values():
        fam = g[0].get("family")
        fam_count[fam] = fam_count.get(fam, 0) + 1
    # meeting/seat 等 slot 族需要 query 带日期槽 K2 才介入，bank/car_color 更干净
    clean = sorted(cid for cid, g in groups.items()
                   if fam_count.get(g[0].get("family")) == 1
                   and g[0].get("family") not in ("meeting", "travel"))
    reverse = sorted(rng.sample(clean, min(REVERSE_CHAINS, len(clean))))
    pool = sorted(cid for cid in groups if cid not in reverse)
    rest = rng.sample(pool, max(0, count - len(reverse)))
    return reverse + rest, set(reverse)


def sample_facts(pool, count, rng):
    """事实块：family × position 五分位双层分层，family 轮转 + 分位轮转。"""
    fams = sorted({r["family"] for r in pool})
    rng.shuffle(fams)
    by = {}
    for r in pool:
        by.setdefault((r["family"], pos_bin(r)), []).append(r)
    for v in by.values():
        v.sort(key=lambda x: x["id"])
        rng.shuffle(v)
    out, p = [], 0
    while len(out) < count:
        progressed = False
        for fi, fam in enumerate(fams):
            if len(out) >= count:
                break
            bins = sorted(b for (f, b) in by if f == fam and by[(f, b)])
            if not bins:
                continue
            b = bins[(p + fi) % len(bins)]
            out.append(by[(fam, b)].pop())
            progressed = True
        if not progressed:
            break
        p += 1
    return out


def sample_noise(pool, count, rng):
    """噪声块：只按位置五分位分层。"""
    by = {}
    for r in pool:
        by.setdefault(pos_bin(r), []).append(r)
    for v in by.values():
        rng.shuffle(v)
    order = sorted(by)
    rng.shuffle(order)
    out, p = [], 0
    while len(out) < count and any(by.values()):
        progressed = False
        for b in order:
            if len(out) >= count:
                break
            if by[b]:
                out.append(by[b].pop())
                progressed = True
        if not progressed:
            break
        p += 1
    return out


def sample(n, blocks, groups, rng):
    """20/50/100/200 共用一条固定优先级序列并取其前缀 → 子库嵌套可比。"""
    chains, facts, noise, reverse = priority_order(blocks, groups, rng)
    n_chain, n_fact, n_noise = QUOTA[n]
    chosen = sorted(chains[:n_chain])
    chain_rows = []
    for cid in chosen:
        chain_rows.extend(groups[cid])
    return chain_rows, facts[:n_fact], noise[:n_noise], chosen, reverse


def priority_order(blocks, groups, rng):
    """一次性排出全局优先级：反序链在最前，其余链/事实/噪声各自分层。
    20/50/100 都取同一条序列的前缀 → 三个子库互相嵌套，退化斜率可比。"""
    chains, reverse = choose_chains(groups, len(groups), rng)
    facts = sample_facts([r for r in blocks if r["kind"] == "fact"],
                         sum(1 for r in blocks if r["kind"] == "fact"), rng)
    noise = sample_noise([r for r in blocks if r["kind"] == "noise"],
                         sum(1 for r in blocks if r["kind"] == "noise"), rng)
    return chains, facts, noise, reverse


# ---------------------------------------------------------------------------
# 时间戳与插入顺序
# ---------------------------------------------------------------------------
def assign_times(sample_rows, blocks, groups, chosen, reverse):
    """普通块按位置线性给时间；链按 A/B/C/D 阶梯给时间。
    反序链：D = C - 1.5h（仍晚于 B），而 id 仍按插入顺序 > C。"""
    idx = {r["id"]: i for i, r in enumerate(sorted(blocks, key=lambda x: float(x["position"])))}
    created = {}
    for r in sample_rows:
        if r.get("kind") != "chain":
            created[r["id"]] = (BASE_TS + timedelta(minutes=30 * idx[r["id"]])).isoformat(
                timespec="seconds")
    chain_idx = {cid: i for i, cid in enumerate(sorted(groups), start=1)}
    for cid in sorted(chosen):
        g = groups[cid]
        t = BASE_TS + timedelta(days=2 * chain_idx[cid])   # 与 n 无关，子库间稳定
        offs = [timedelta(0), timedelta(hours=3), timedelta(hours=6), timedelta(hours=9)]
        for pos, r in enumerate(g):
            delta = offs[min(pos, len(offs) - 1)]
            if cid in reverse and pos == len(g) - 1:      # D 回拨到 C 之前
                delta = timedelta(hours=4, minutes=30)
            created[r["id"]] = (t + delta).isoformat(timespec="seconds")
    return created


def apply_reverse_text(chain_rows, groups, reverse):
    """反序链的 C 块补族关键词前缀，让 k2_family 能把它认回本族。"""
    overrides = {}
    for cid in sorted(reverse):
        g = groups[cid]
        if len(g) < 2:
            continue
        src = g[-2]
        word = FAMILY_WORD.get(src.get("family"))
        if not word:
            continue
        new_text = "顺便说一下，%s的%s后来又有变化：%s" % (src.get("owner") or "", word,
                                                          src["text"])
        overrides[cid] = {"block_id": src["id"], "word": word, "text": new_text}
    out = []
    for r in chain_rows:
        ov = overrides.get(r.get("chain_id"))
        if ov and ov["block_id"] == r["id"]:
            r = dict(r)
            r["text"] = ov["text"]
            r["text_override"] = True
        out.append(r)
    return out, overrides


def norm_text(s):
    """NFKC + 去空白/间隔符；与 source_hash 无关，仅用于检测脏重复。"""
    s = unicodedata.normalize("NFKC", str(s or ""))
    return "".join(ch for ch in s
                   if not ch.isspace() and ch not in "\u00b7-\u2014\u2013_.\u3002\uff0c\u3001")


def pad_text(text, target=PAD_CHARS):
    """把块填到约 target 字符（中文约 1 token/字），不改开头的原始事实。"""
    t = str(text or "").rstrip()
    if len(t) >= target:
        return t
    while len(t) < target:
        t += FILLER
    cut = t.rfind("\u3002", 0, target + 40)
    return t[:cut + 1] if cut > 0 else t[:target]


def slice_order(chains, facts, noise, n, groups):
    """从固定优先级序列切出前 n 档：链完整、事实/噪声取前缀。"""
    n_chain, n_fact, n_noise = QUOTA[n]
    chosen = sorted(chains[:n_chain])
    chain_rows = [r for cid in chosen for r in groups[cid]]
    return chain_rows, facts[:n_fact], noise[:n_noise], chosen


def sample_qset(queries, base_ids, want=QS_PER_BAND, n_neg=10):
    """固定 40 条：10 条旧值负例 + 30 条正常（优先目标在 20 档内的，再按 kind 轮转补齐）。
    该集合只依赖 20 档块集合，与 n 无关 -> 20/50 用同一套题。"""
    neg = [q for q in queries if q.get("kind") == "negative"][:n_neg]
    norm = [q for q in queries if q.get("kind") != "negative"]
    mapped = [q for q in norm if q.get("target_block_id") in base_ids]
    rest = [q for q in norm if q.get("target_block_id") not in base_ids]
    want_pos = max(0, want - len(neg))
    sel = sorted(mapped, key=lambda q: q["id"])[:want_pos]
    pools = {k: sorted([q for q in rest if q.get("kind") == k], key=lambda q: q["id"])
             for k in ("direct", "paraphrase", "chain_last")}
    rng = random.Random(SEED + 1)
    for v in pools.values():
        rng.shuffle(v)
    order = ["direct", "paraphrase", "chain_last"]
    while len(sel) < want_pos and any(pools.values()):
        for k in order:
            if len(sel) >= want_pos:
                break
            if pools[k]:
                sel.append(pools[k].pop())
    return sorted(neg + sel, key=lambda q: q["id"])


def db_stats(path):
    """审计库内行数/块数/精确重复/norm 重复（脏数据证据）。"""
    if not path or not os.path.exists(path):
        return None
    con = sqlite3.connect(path)
    try:
        rows = list(con.execute("SELECT id,name,text,source_hash FROM memory_source"))
        nblocks = con.execute("SELECT COUNT(*) FROM memory_block").fetchone()[0]
    finally:
        con.close()
    exact, norm = {}, {}
    for sid, name, text, h in rows:
        exact.setdefault(h, []).append(int(sid))
        norm.setdefault(norm_text(text), []).append(int(sid))
    edup = {k: v for k, v in exact.items() if len(v) > 1}
    ndup = {k: v for k, v in norm.items() if len(v) > 1}
    return {
        "rows": len(rows), "blocks": int(nblocks),
        "distinct_exact_hash": len(exact),
        "exact_dup_groups": len(edup),
        "exact_dup_rows": sum(len(v) for v in edup.values()),
        "norm_dup_groups": len(ndup),
        "norm_dup_rows": sum(len(v) for v in ndup.values()),
        "norm_dup_pairs": [v for v in ndup.values()],
    }


def ordered_sample(chain_rows, facts, noise):
    return sorted(chain_rows + facts + noise, key=lambda r: (float(r["position"]), r["id"]))


# ---------------------------------------------------------------------------
# 查询映射
# ---------------------------------------------------------------------------
def remap_queries(queries, blocks_by_id, idmap, groups, reverse, qset_mode=False):
    """target -> 新 DB id；反序链把“最新值”期望改到 C（created_at 最新），
    D（id 更大但时间更早）成为必须被 K2 隐掉的幽灵值。"""
    ghost = {}
    latest = {}
    for cid in reverse:
        g = groups[cid]
        if len(g) < 2:
            continue
        last, new_latest = g[-1], g[-2]
        ghost[last["id"]] = last
        latest[last["id"]] = new_latest
    out = []
    stats = {"total": len(queries), "mapped": 0, "null_target": 0,
             "unmapped": 0, "remapped": 0}
    for q in queries:
        src = q.get("target_block_id")
        rec = dict(q)
        rec["src_target_block_id"] = src
        src_block = blocks_by_id.get(src) if src else None
        rec["family"] = (src_block or {}).get("family") or "none"
        if src is None:
            rec.update(target_block_id=None, in_sample=True, target_in_library=True,
                       reverse_chain=False, ghost_block_id=None)
            stats["null_target"] += 1
        elif src in idmap:
            rec.update(target_block_id=idmap[src]["new_id"], in_sample=True,
                       target_in_library=True,
                       reverse_chain=False, ghost_block_id=None)
            stats["mapped"] += 1
            if src in ghost:
                new_latest = latest[src]
                others = [b for b in groups[src_block["chain_id"]] if b["id"] != new_latest["id"]]
                expect, notc = [], []
                for v in variants(new_latest["value"]):
                    if v not in expect:
                        expect.append(v)
                for b in others:
                    for v in variants(b["value"]):
                        if v not in notc:
                            notc.append(v)
                rec.update(expect_any=expect, not_contains=notc,
                           reverse_chain=True,
                           ghost_block_id=idmap[src]["new_id"],
                           target_block_id=idmap[new_latest["id"]]["new_id"],
                           reverse_note=("created_at 最新=%s(%s)；id 更大但时间更早=%s(%s)"
                                         % (new_latest["id"], new_latest["value"],
                                            src, src_block["value"])))
                stats["remapped"] += 1
        else:
            rec.update(target_block_id=None, in_sample=bool(qset_mode),
                       target_in_library=False,
                       reverse_chain=False, ghost_block_id=None)
            stats["unmapped"] += 1
        out.append(rec)
    return out, stats


# ---------------------------------------------------------------------------
# 摘要
# ---------------------------------------------------------------------------
def summarize(sample_rows, chains, reverse, qstats):
    kinds, fams, bins = {}, {}, {}
    for r in sample_rows:
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
        fams[r["family"]] = fams.get(r["family"], 0) + 1
        b = "%d" % pos_bin(r)
        bins[b] = bins.get(b, 0) + 1
    return {
        "blocks": len(sample_rows),
        "kind": dict(sorted(kinds.items())),
        "family": dict(sorted(fams.items())),
        "position_bin": dict(sorted(bins.items())),
        "chains": chains,
        "reverse_chains": sorted(reverse),
        "queries": qstats,
    }


def k2_check(groups, reverse, overrides):
    """dry-run 自检：反序链 4 块必须被 k2_family 认成同一族（否则 K2 看不到 C）。"""
    try:
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        import k2_family as K
    except Exception as exc:                             # noqa: BLE001
        return {"skipped": "%s: %s" % (type(exc).__name__, exc)}
    out = {}
    for cid in sorted(reverse):
        texts = []
        for r in groups[cid]:
            ov = overrides.get(cid)
            texts.append(ov["text"] if ov and ov["block_id"] == r["id"] else r["text"])
        fams = [K.classify_row(t)["family"] for t in texts]
        out[cid] = {"families": fams,
                    "ok": len(set(fams)) == 1 and fams[0] is not None}
    return out


def print_dry(summary, plan, dst):
    print("=== scale40k dry-run (n=%d, seed=%d) ===" % (plan["n"], SEED))
    print("dst        :", os.path.abspath(dst), "(未建库、未加载模型)")
    print("block ids  :", " ".join(summary["block_ids"]))
    print("kind       :", summary["kind"])
    print("family     :", summary["family"])
    print("pos bin(5) :", summary["position_bin"])
    print("chains     : %d 条 / %d 块" % (len(summary["chains"]), plan["chain_blocks"]))
    for c in summary["chains"]:
        print("   %s %-9s %-4s reverse=%s seq=%s created=%s" %
              (c["chain_id"], c["family"], c["owner"], c["reverse"],
               c["ids"], c["created_at"]))
    print("reverse    :", summary["reverse_chains"],
          "→ D 早于 C，但 id(D) > id(C)（插入序）")
    if summary.get("k2_check"):
        for cid, chk in summary["k2_check"].items():
            print("k2 check   : %s %s ok=%s" % (cid, chk.get("families"), chk.get("ok")))
    for cid, ov in (summary.get("text_override") or {}).items():
        print("text ovr   : %s %s += '%s'（原文无族关键词）"
              % (cid, ov["block_id"], ov["word"]))
    print("protocol   : padded=%d×~%d字, dirty=%d对/%d行, qset=%d"
          % (summary["plan"]["padded_blocks"], summary["protocol"]["pad_chars"],
             summary["protocol"]["dirty_pairs"], summary["plan"]["dirty_rows"],
             summary["protocol"]["qset"]))
    print("queries    :", summary["queries"])
    print("est rows   : %d（%d 块 + %d 脏行）"
          % (summary["plan"]["rows"], summary["plan"]["blocks"], summary["plan"]["dirty_rows"]))
    if summary.get("key_facts"):
        kf = summary["key_facts"]
        print("key facts  : %d/%d 覆盖 %s" % (len(kf["included"]), kf["total"],
                                             kf["included"] or "-"))
    print("plan       : 插入 %d 行(按 position 升序) → KVEngine → build_block ×%d → queries.jsonl"
          % (plan["blocks"], plan["blocks"]))
    print("estimate   : ~%s 分钟（按 3–9 s/块）" % plan["est_min"])
    return 0


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, choices=sorted(QUOTA), required=True)
    ap.add_argument("--dst", default=None, help="默认 kvmem/scale40k/nN")
    ap.add_argument("--dry-run", action="store_true", help="只抽样/映射，不加载模型不建块")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--force", action="store_true", help="目标 chat.db 已存在时覆盖重建")
    ap.add_argument("--max-blocks", type=int, default=0, help="调试：只建前 K 块")
    ap.add_argument("--pad-count", type=int, default=PAD_COUNT, help="长块数（优先序列前 K 块）")
    ap.add_argument("--pad-chars", type=int, default=PAD_CHARS, help="长块目标字符数≈token")
    ap.add_argument("--dirty-pairs", type=int, default=len(DIRTY_PAIRS))
    ap.add_argument("--qset", type=int, default=QS_PER_BAND,
                    help="每档固定查询数（30 正常 + 10 负例），0=沿用全部已映射")
    ap.add_argument("--row-cap", type=int, default=0,
                    help="库总行数上限（含脏行）；n>=200 默认 200，先裁噪声再裁事实")
    args = ap.parse_args(argv)

    dst = os.path.abspath(args.dst or os.path.join(ROOT, "kvmem", "scale40k", "n%d" % args.n))
    blocks_dir = os.path.join(dst, "blocks")
    db_path = os.path.join(dst, "chat.db")
    qpath = os.path.join(dst, "queries.jsonl")

    blocks = load_jsonl(BLOCKS_SRC)
    queries = load_jsonl(QUERIES_SRC)
    manifest = load_manifest()
    by_id = {r["id"]: r for r in blocks}
    groups = chain_groups(blocks)

    # 固定优先级序列（seed 40000）；20/50/100 都是它的前缀 -> 子库嵌套
    chains, fact_order, noise_order, reverse = priority_order(blocks, groups,
                                                              random.Random(SEED))
    n20_chain, n20_fact, n20_noise, n20_chosen = slice_order(
        chains, fact_order, noise_order, 20, groups)
    n20_rows = ordered_sample(n20_chain, n20_fact, n20_noise)
    n20_ids = {r["id"] for r in n20_rows}
    pad_ids = {r["id"] for r in sorted(n20_rows,
                                       key=lambda x: (float(x["position"]), x["id"]))[:args.pad_count]}

    chain_rows, facts_sel, noise_sel, chosen = slice_order(chains, fact_order,
                                                           noise_order, args.n, groups)
    chain_rows, overrides = apply_reverse_text(chain_rows, groups, reverse)
    rows0 = ordered_sample(chain_rows, facts_sel, noise_sel)
    row_cap = args.row_cap or (200 if args.n >= 200 else 0)
    sample_rows = []
    for r in rows0:
        if r["id"] in pad_ids:
            r = dict(r)
            r["text"] = pad_text(r["text"], args.pad_chars)
            r["padded"] = True
        sample_rows.append(r)
    created = assign_times(sample_rows, blocks, groups, chosen, reverse)

    if row_cap and len(sample_rows) + 2 * args.dirty_pairs > row_cap:
        excess = len(sample_rows) + 2 * args.dirty_pairs - row_cap
        out = list(sample_rows)
        for kind in ("noise", "fact"):
            i = len(out) - 1
            while excess > 0 and i >= 0:
                if out[i]["kind"] == kind:
                    out.pop(i)
                    excess -= 1
                i -= 1
        sample_rows = out
        idmap_trim_note = "trimmed %d rows to cap %d" % (
            len(rows0) - len(sample_rows), row_cap)
    else:
        idmap_trim_note = ""
    idmap = {}
    for i, r in enumerate(sample_rows, start=1):
        idmap[r["id"]] = {"new_id": i, "name": "s40_" + r["id"],
                          "created_at": created[r["id"]]}
    dirty = []
    for i, (a, b) in enumerate(DIRTY_PAIRS[:args.dirty_pairs], start=1):
        for tag, txt in (("a", a), ("b", b)):
            dirty.append({"name": "s40_dirty_%02d%s" % (i, tag),
                          "label": "scale40k dirty pair %d%s" % (i, tag),
                          "text": txt,
                          "created_at": (BASE_TS + timedelta(minutes=30 * len(sample_rows) + i))
                          .isoformat(timespec="seconds")})

    if args.qset:
        qsel = sample_qset(queries, n20_ids, args.qset)
        qrows, qstats = remap_queries(qsel, by_id, idmap, groups, reverse, qset_mode=True)
        qstats["selected"] = len(qsel)
    else:
        qrows, qstats = remap_queries(queries, by_id, idmap, groups, reverse)

    chains_summary = []
    for cid in sorted(chosen):
        g = groups[cid]
        chains_summary.append({
            "chain_id": cid, "family": g[0].get("family"),
            "owner": g[0].get("owner"), "reverse": cid in reverse,
            "text_override": cid in overrides,
            "ids": [r["id"] for r in g],
            "new_ids": [idmap[r["id"]]["new_id"] for r in g],
            "created_at": [idmap[r["id"]]["created_at"] for r in g],
        })

    qstat_out = dict(qstats)
    qstat_out["asked"] = len(qrows)
    summary = summarize(sample_rows, chains_summary, reverse, qstat_out)
    summary["block_ids"] = [r["id"] for r in sample_rows]
    summary["sample"] = [{"id": r["id"], "new_id": idmap[r["id"]]["new_id"],
                          "kind": r["kind"], "family": r["family"],
                          "position": r["position"], "value": r.get("value"),
                          "text_override": bool(r.get("text_override")),
                          "padded": bool(r.get("padded")),
                          "created_at": idmap[r["id"]]["created_at"]}
                         for r in sample_rows]
    kf = [k.get("id") for k in (manifest.get("key_facts") or [])]
    summary["key_facts"] = {"total": len(kf),
                            "included": [i for i in kf if i in idmap],
                            "missing": [i for i in kf if i not in idmap]}
    est_lo = max(1, round((len(sample_rows) + len(dirty)) * 3 / 60.0))
    est_hi = max(1, round((len(sample_rows) + len(dirty)) * 9 / 60.0))
    plan = {"n": args.n, "blocks": len(sample_rows), "rows": len(sample_rows) + len(dirty),
            "row_cap": row_cap, "trim_note": idmap_trim_note,
            "chain_blocks": len(chain_rows), "fact_blocks": len(facts_sel),
            "noise_blocks": len(noise_sel), "padded_blocks": len(pad_ids),
            "dirty_rows": len(dirty), "est_min": "%d-%d" % (est_lo, est_hi)}
    summary["plan"] = plan
    summary["protocol"] = {"pad_count": len(pad_ids), "pad_chars": args.pad_chars,
                           "dirty_pairs": len(dirty) // 2, "qset": args.qset}
    summary["dirty_pairs"] = [{"pair": i + 1, "a": a, "b": b}
                              for i, (a, b) in enumerate(DIRTY_PAIRS[:args.dirty_pairs])]
    summary["text_override"] = {cid: {"block_id": ov["block_id"], "word": ov["word"]}
                                for cid, ov in sorted(overrides.items())}
    summary["k2_check"] = k2_check(groups, reverse, overrides)
    summary["seed"] = SEED
    summary["dst"] = dst
    summary["queries_file"] = qpath
    summary["notes"] = [
        "seed 固定 40000；20/50/100 取同一优先级序列前缀，子库嵌套。",
        "长块：n20 前 %d 块填充到 ~%d 字符（约 800 token），其余 ~200。" % (len(pad_ids), args.pad_chars),
        "脏数据：%d 对全角/空格差异行入同一库，exact sha 不同、norm 相同。" % (len(dirty) // 2),
        "反序链 D 的 created_at 早于 C 但 id 更大；期望值按 created_at 最新（=C）。",
        "K2 不识别任意人名 owner：K2-off 本轮不受影响；K2-on 时 plate/company/phone 会跨人互踩。",
    ]
    os.makedirs(dst, exist_ok=True)
    with open(qpath, "w", encoding="utf-8") as f:
        for q in qrows:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")

    if args.dry_run:
        summary["reverse_evidence"] = []
        for c in chains_summary:
            if c["reverse"]:
                summary["reverse_evidence"].append({
                    "chain_id": c["chain_id"],
                    "seq": [{"src_id": s, "new_id": n, "created_at": t}
                            for s, n, t in zip(c["ids"], c["new_ids"], c["created_at"])],
                    "check": "id(D)>id(C) and created_at(D)<created_at(C)",
                })
        summary["db"] = None
        with open(os.path.join(dst, "DRYRUN.json"), "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=1)
        return print_dry(summary, plan, dst)

    # ---- 非 dry-run：真建库 ----
    if os.path.exists(db_path) and not args.force:
        print("ERROR: %s 已存在；确认重建请加 --force" % db_path, file=sys.stderr)
        return 2
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import kvslots                                    # noqa: E402  仅非 dry-run 导入
    import memory_source as ms                        # noqa: E402

    os.makedirs(blocks_dir, exist_ok=True)
    os.makedirs(os.path.join(dst, "sessions"), exist_ok=True)
    if os.path.exists(db_path):
        os.remove(db_path)
    for f in os.listdir(blocks_dir):
        if f.startswith("s40_") and f.endswith(".kvmem"):
            os.remove(os.path.join(blocks_dir, f))
    con = ms.connect(db_path)
    ins = ("INSERT INTO memory_source (tenant,scope,mode,name,label,text,source_hash,"
           "created_at,text_kind,contains_model_turns,is_excerpt,derived_from) "
           "VALUES ('default','private','chat',?,?,?,?,?,'human_memory',0,0,NULL)")
    try:
        for r in sample_rows:
            rec = idmap[r["id"]]
            label = "scale40k %s %s %s" % (r["id"], r["family"], r["kind"])
            cur = con.execute(ins, (rec["name"], label, r["text"],
                                    ms.sha256_text(r["text"]), rec["created_at"]))
            assert int(cur.lastrowid) == rec["new_id"], (cur.lastrowid, rec["new_id"])
        for d in dirty:
            cur = con.execute(ins, (d["name"], d["label"], d["text"],
                                    ms.sha256_text(d["text"]), d["created_at"]))
            d["new_id"] = int(cur.lastrowid)
        con.commit()
        total_rows = con.execute("SELECT COUNT(*) FROM memory_source").fetchone()[0]
        assert int(total_rows) == len(sample_rows) + len(dirty), (total_rows, len(sample_rows))
    except Exception:
        con.close()
        raise

    eng = kvslots.KVEngine(args.model, **ENGINE_CFG)
    t0 = datetime.now()
    built = []
    try:
        todo = sample_rows[:args.max_blocks] if args.max_blocks else sample_rows
        for r in todo:
            rec = idmap[r["id"]]
            row = ms.get_source(con, rec["name"])
            info = ms.build_block(eng, con, row, blocks_dir=blocks_dir,
                                  kv_type="q8_0", model_path=args.model, seq=BUILD_SEQ)
            built.append({"src_id": r["id"], "new_id": rec["new_id"],
                          "n_tokens": info.get("n_tokens"), "n_bytes": info.get("n_bytes"),
                          "padded": bool(r.get("padded"))})
            print("built %3d/%3d %s %s tokens=%s" %
                  (len(built), len(todo), rec["name"], r["family"], info.get("n_tokens")))
        if not args.max_blocks:
            for d in dirty:
                row = ms.get_source(con, d["name"])
                info = ms.build_block(eng, con, row, blocks_dir=blocks_dir,
                                      kv_type="q8_0", model_path=args.model, seq=BUILD_SEQ)
                built.append({"src_id": None, "new_id": d["new_id"],
                              "n_tokens": info.get("n_tokens"), "n_bytes": info.get("n_bytes"),
                              "padded": False})
                print("built dirty %s tokens=%s" % (d["name"], info.get("n_tokens")))
    finally:
        eng.close()
    stats = db_stats(db_path)
    con.close()

    toks = [b["n_tokens"] for b in built]
    summary.update({
        "built": len(built), "built_blocks": built,
        "tokens": {"min": min(toks), "max": max(toks),
                   "mean": round(sum(toks) / float(len(toks)), 1),
                   "long_blocks": sum(1 for t in toks if t and t >= 600)},
        "db": stats,
        "engine": dict(ENGINE_CFG, model=args.model),
        "elapsed_s": round((datetime.now() - t0).total_seconds(), 1),
        "schema_version": 1,
    })
    with open(os.path.join(dst, "build.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)
    print("DB      :", db_path)
    print("blocks  :", blocks_dir)
    print("rows    :", stats["rows"], "blocks:", stats["blocks"],
          "norm_dup_groups:", stats["norm_dup_groups"])
    print("tokens  : min=%s max=%s mean=%s long>=600=%s"
          % (summary["tokens"]["min"], summary["tokens"]["max"],
             summary["tokens"]["mean"], summary["tokens"]["long_blocks"]))
    print("queries :", qpath, len(qrows))
    print("built   : %d / %.1f s" % (len(built), summary["elapsed_s"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
