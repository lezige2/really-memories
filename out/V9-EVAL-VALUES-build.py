# -*- coding: utf-8 -*-
"""TASK-091：生成 out/V9-EVAL-VALUES.json（独立值池 + fixture 实体分离 + 机械断言）。
- eval_values_independent：来自当前 MT20（20 条）expect 的独立值（值→来源 case）
- fixture_entities：只取 MEM: 前缀实体值（v2/v3/v3-dempty/MT20；不含 heldout 产品 fixture）
- fixture_values：全部 fixture 值（含 81/heldout），供参考/排除
- assertions：independent∩train_blob=∅、fixture_entities∩train_blob=∅、independent∩reserved=∅
只读现有文件，不重写 MT20。
用法：python -X utf8 out/V9-EVAL-VALUES-build.py
"""
import glob
import hashlib
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out")
DST = os.path.join(OUT, "SFT-EXTRA-CASES-v9-MT20.jsonl")
VALUES = os.path.join(OUT, "V9-EVAL-VALUES.json")
RESERVED = ["雪梨", "商汤", "闽D74185", "18 号", "18号", "洛阳", "137-0000-9527", "E区9号", "E 区 9 号",
            "布洛芬", "十点", "银川", "银色", "两厢", "7418", "豆豆", "字节跳动"]
# 通用时间/序数/方位词不算“实体值”，与实体分开标注（B：fixture_entities 与通用语料词分开）
GENERIC_TOKENS = {"周一", "周二", "周三", "周四", "周五", "周六", "周日", "上午", "下午", "晚上", "点", "号",
                  "B区", "C区", "11号", "7号", "9号", "10号", "几号", "几点"}
GENERIC_TIME = set()   # 纯钟点/序数（10点/22点/8点/周二…）视为通用词，不作实体断言
import re as _re
GENERIC_TIME_RE = _re.compile(r"^[0-9一二三四五六七八九十]{1,2}(点|时|号|日|月|年)$|^[0-9]{4}-[0-9]{2}-[0-9]{2}$")


STOPWORDS = {"做不了", "没法", "帮不了", "记不清", "不知道", "没有", "不能", "谢谢", "在吗", "随便聊聊吧",
             "城市", "没告诉", "没提过", "没说", "记不起来", "忘记了", "想不起", "记不得",
             "嗯嗯", "好的", "收到", "没问题", "记下", "知道了", "什么", "具体", "型号", "名字", "哪个",
             "哪家", "开会", "出差", "车牌", "工位", "老家", "健身", "游泳", "建议", "不确定", "抱歉",
             "查不到", "本地", "助手", "记忆", "AI", "DeepSeek", "GPT", "不联网", "天气", "代码", "排序",
             "def", "pivot", "你好", "哈喽", "有啥", "在的", "晚上好", "早上好", "在呢", "你好呀",
             "宠物", "猫", "狗", "花", "草", "鱼", "鸟", "兔", "仓鼠", "乌龟", "品", "型号", "品牌"}


def entities_from_case(c, out, source):
    """事实实体：remember 文本 + expect 的 contains_any/contains_all/conflict_if_all + 非疑问的“我…”输入陈述。"""
    cid = c.get("id")
    for a in c.get("pre_state") or []:
        if a.get("action") == "remember" and a.get("text"):
            out.setdefault(str(a["text"]).strip(), []).append({"source": source, "id": cid, "kind": "remember"})
    exp = c.get("expect") or {}
    groups = [exp.get("contains_any") or [], exp.get("contains_all") or []]
    groups += [[x for pair in (exp.get("conflict_if_all") or []) for x in pair]]
    for vals in groups:
        for v in vals:
            out.setdefault(str(v).strip(), []).append({"source": source, "id": cid, "kind": "expect"})
    inp = str(c.get("input") or "").strip()
    if inp.startswith("我") and not inp.endswith(("？", "?")):
        out.setdefault(inp, []).append({"source": source, "id": cid, "kind": "input_fact"})


def probe_entities(path, out):
    """从探针脚本模块级 FACTS/SFT_FACTS 常量收集事实文本与 expect 词。"""
    import ast
    tree = ast.parse(open(path, encoding="utf-8").read())
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id in ("FACTS", "SFT_FACTS"):
                    try:
                        val = ast.literal_eval(node.value)
                    except Exception:
                        continue
                    for item in val or []:
                        if not isinstance(item, (list, tuple)):
                            continue
                        if len(item) >= 2 and isinstance(item[1], str):       # fact 文本
                            out.setdefault(item[1].strip(), []).append(
                                {"source": os.path.basename(path), "id": "FACT", "kind": "probe_fact"})
                        if len(item) >= 4 and isinstance(item[3], (list, tuple)):  # expect 词
                            for y in item[3]:
                                if isinstance(y, str) and len(y) >= 2:
                                    out.setdefault(y.strip(), []).append(
                                        {"source": os.path.basename(path), "id": "FACT", "kind": "probe_expect"})
EXTRA_FILES = ["SFT-EXTRA-CASES-v2.jsonl", "SFT-EXTRA-CASES-v3.jsonl",
               "SFT-EXTRA-CASES-v3-dempty.jsonl", "SFT-EXTRA-CASES-v9-MT20.jsonl"]


def train_files():
    return sorted(glob.glob(os.path.join(ROOT, "training", "sft", "*.jsonl")))


def load_cases(path):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()] if os.path.isfile(path) else []


def values_of(cases, source):
    out = {}
    for c in cases:
        for v in ((c.get("expect") or {}).get("contains_any") or []):
            out.setdefault(str(v), []).append({"source": source, "id": c.get("id"), "kind": "expect"})
        for v in ((c.get("expect") or {}).get("contains_all") or []):
            out.setdefault(str(v), []).append({"source": source, "id": c.get("id"), "kind": "contains_all"})
        for v in ((c.get("expect") or {}).get("not_contains") or []):
            out.setdefault(str(v), []).append({"source": source, "id": c.get("id"), "kind": "not_contains"})
        for pair in ((c.get("expect") or {}).get("conflict_if_all") or []):
            for v in pair:
                out.setdefault(str(v), []).append({"source": source, "id": c.get("id"), "kind": "conflict_if_all"})
        for a in c.get("pre_state") or []:
            if a.get("action") == "remember" and a.get("text"):
                out.setdefault("MEM:" + str(a["text"]), []).append({"source": source, "id": c.get("id"),
                                                                   "kind": "remember"})
    return out


def main():
    blob = "".join(open(f, encoding="utf-8", errors="replace").read() for f in train_files())
    fixtures, mem_entities = {}, {}
    # 全量字段收集（input/pre_state/history/expect/remember）——extra 文件含 MT20
    for name in EXTRA_FILES:
        cs = load_cases(os.path.join(OUT, name))
        part = values_of(cs, name)
        fixtures.update(part)
        for c in cs:
            entities_from_case(c, fixtures, name)
        for k, v in part.items():
            if k.startswith("MEM:"):
                mem_entities.setdefault(k, []).extend(v)
    # 探针脚本 FACT/事实常量
    for name in ("BASE-VERIFY-PROBES.py",):
        path = os.path.join(OUT, name)
        if os.path.isfile(path):
            probe_entities(path, fixtures)
    fixture_entities_raw = dict(fixtures)   # 仅评测侧 fixture（out/ extra v2/v3/dempty/MT20 + 探针 FACT）
    # 81 + heldout（仅入 fixture_values 供参考，不参与 fixture_entities 断言）
    cs = load_cases(os.path.join(ROOT, "training", "dialog_cases.jsonl"))
    fixtures.update(values_of(cs, "dialog_cases.jsonl"))
    import importlib.util
    spec = importlib.util.spec_from_file_location("rh_v", os.path.join(ROOT, "training/heldout/run_heldout.py"))
    rh = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rh)
    fixtures.update(values_of([dict(c, id=c.get("id")) for c in rh.CASES], "run_heldout.py:CASES"))
    independent = values_of(load_cases(DST), "SFT-EXTRA-CASES-v9-MT20.jsonl")
    independent = {k: v for k, v in independent.items() if not k.startswith("MEM:")}
    ALLOWED = {"remember", "expect", "contains_all", "conflict_if_all", "input_fact", "probe_fact", "probe_expect"}
    gen = {k for k in fixture_entities_raw if k in GENERIC_TOKENS or k in STOPWORDS or GENERIC_TIME_RE.match(k)
           or _re.match(r"^[0-9]{1,2}点.*$", k) or _re.match(r"^[0-9]+\s*号$", k)}
    fixture_entities = {k: v for k, v in fixture_entities_raw.items()
                        if k not in gen and len(k) >= 2 and not k.startswith("MEM:")
                        and not k.endswith(("？", "?"))
                        and any(x.get("kind") in ALLOWED for x in v)}
    independent_entities = {v: src for v, src in independent.items()
                            if v not in GENERIC_TOKENS and not v.isdigit() and len(v) >= 2}
    generic_tokens = {v: src for v, src in independent.items() if v in GENERIC_TOKENS or v.isdigit()}
    overlap_ind = {v: blob.count(v) for v in independent_entities if blob.count(v)}
    overlap_ent = {k: blob.count(k) for k in fixture_entities if blob.count(k)}
    overlap_res = {v: r for v in independent_entities for r in RESERVED if r in v}
    ev = {"schema": "v9_eval_values_v1", "task": "TASK-099",
          "generated_at": __import__("datetime").datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
          "train_blob": {"files": [os.path.basename(f) for f in train_files()],
                         "bytes": len(blob.encode("utf-8")),
                         "sha16": hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16],
                         "sha256": hashlib.sha256(blob.encode("utf-8")).hexdigest(),
                         "files_detail": [{"name": os.path.basename(f), "bytes": os.path.getsize(f),
                                           "sha256": hashlib.sha256(open(f, "rb").read()).hexdigest()}
                                          for f in train_files()],
                         "note": "train_blob=12 个训练 jsonl 按文件名排序拼接后的 sha256（非单文件哈希；单文件哈希见 files_detail，train_v9.jsonl 应为 c3d0d156…）"},
          "eval_values_independent": independent,
          "independent_entities": independent_entities,
          "independent_generic_tokens": generic_tokens,
          "fixture_entities": fixture_entities,
          "fixture_mem_entities": mem_entities,
          "fixture_values": fixtures,
          "assertions": {"independent_values_n": len(independent),
                         "independent_entities_n": len(independent_entities),
                         "generic_tokens_n": len(generic_tokens),
                         "fixture_entities_n": len(fixture_entities),
                         "fixture_mem_entities_n": len(mem_entities),
                         "independent_entities_vs_train_blob": overlap_ind,
                         "fixture_entities_vs_train_blob": overlap_ent,
                         "independent_entities_vs_reserved": overlap_res,
                         "pass": not overlap_ind and not overlap_ent and not overlap_res},
          "mt20": {"path": os.path.basename(DST), "rows": len(load_cases(DST)),
                   "sha256": hashlib.sha256(open(DST, "rb").read()).hexdigest(),
                   "sha16": hashlib.sha256(open(DST, "rb").read()).hexdigest()[:16]}}
    json.dump(ev, open(VALUES, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if not ev["assertions"]["pass"]:
        raise SystemExit("V9_EVAL_VALUES_ASSERT_FAIL: %r" % ev["assertions"])
    print(json.dumps({"values_file": VALUES, "sha16": hashlib.sha256(open(VALUES, "rb").read()).hexdigest()[:16],
                      "mt20_sha16": ev["mt20"]["sha16"], "independent_n": len(independent),
                      "fixture_entities_n": len(fixture_entities),
                      "fixture_mem_entities_n": len(mem_entities),
                      "assertions": ev["assertions"]}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()