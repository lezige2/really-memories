# -*- coding: utf-8 -*-
"""M4 §11/§12 -- the frozen sample dialogue, sentence by sentence, plus the four boundaries.

  python -X utf8 kvmem/m2_visibility/m4/_test_m4.py
"""
import io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import m4_extract as X                                            # noqa: E402

TS = "2026-10-25T09:00:00"

SAMPLE = [
    {"role": "user", "text": "你好呀！", "ts": TS},
    {"role": "assistant", "text": "你好！有什么可以帮你？", "ts": TS},
    {"role": "user", "text": "我住在广陵路 12 号 2 单元 602。", "ts": TS},
    {"role": "user", "text": "我每天早上七点半出门，别在那个时候给我推消息。", "ts": TS},
    {"role": "user", "text": "我车牌是浙B-3F19K。", "ts": TS},
    {"role": "assistant", "text": "记住了。", "ts": TS},
    {"role": "user", "text": "帮我查下明天天气。", "ts": TS},
    {"role": "user", "text": "谢谢，就这样吧。", "ts": TS},
    {"role": "user", "text": "对了，我女儿小名叫豆豆，下周三她生日，提醒我买蛋糕。", "ts": TS},
]

# §11 table, frozen. code expectation is a set: "K1+K5" needs both codes present.
EXPECT = [
    ("drop", {"D1"}, 0),
    ("drop", {"D4"}, 0),
    ("keep", {"K1"}, 1),
    ("keep", {"K1", "K5"}, 2),
    ("keep", {"K1"}, 1),
    ("drop", {"D4"}, 0),
    ("drop", {"D3", "D6"}, 0),
    ("drop", {"D1"}, 0),
    ("keep", {"K4", "K3"}, 2),
]

BOUNDARY = [
    ("我不吃辣。", "keep", {"K2"}, 1),
    ("我不喜欢那个。", "undecidable", {"U4"}, 0),
    ("我好累。", "drop", {"D7"}, 0),
    ("我长期失眠。", "keep", {"K1"}, 1),
    ("如果我搬到杭州，你会记得吗？", "undecidable", {"U2"}, 0),
]


def codes_of(code):
    return set((code or "").split("+"))


def by_turn(rows):
    """Roll sentence rows up to the turn the frozen §11 table counts."""
    turns = {}
    for r in rows:
        t = turns.setdefault(r["turn"], {"turn": r["turn"], "role": r["role"],
                                        "text": "", "verdicts": [], "codes": set(),
                                        "memories": []})
        t["text"] += r["text"]
        t["verdicts"].append(r["verdict"])
        t["codes"] |= codes_of(r["code"])
        t["memories"].extend(r["memories"])
    for t in turns.values():
        if "keep" in t["verdicts"]:
            t["verdict"] = "keep"
        elif "undecidable" in t["verdicts"]:
            t["verdict"] = "undecidable"
        else:
            t["verdict"] = "drop"
        t["codes"] = sorted(t["codes"])
    return [turns[k] for k in sorted(turns)]


def main():
    out = {"schema": "m4_judge_evidence_v1", "ts": TS, "sample": [], "boundaries": [],
           "mismatches": []}
    rows_all = X.run(SAMPLE)
    print("## §11 样例对话：按轮对照冻结判据（ts=%s）" % TS)
    print("| 轮 | role | 原文 | verdict | codes | memories |")
    print("|---|---|---|---|---|---|")
    for t, (ev, ec, en) in zip(by_turn(rows_all), EXPECT):
        ok = (t["verdict"] == ev and set(t["codes"]) == ec and len(t["memories"]) == en)
        out["sample"].append({"turn": t["turn"], "role": t["role"], "text": t["text"],
                              "verdict": t["verdict"], "codes": t["codes"],
                              "memories": t["memories"],
                              "expected_verdict": ev, "expected_codes": sorted(ec),
                              "expected_memory_count": en, "match": ok})
        if not ok:
            out["mismatches"].append({"turn": t["turn"], "text": t["text"],
                                      "got": [t["verdict"], t["codes"], len(t["memories"])],
                                      "want": [ev, sorted(ec), en]})
        print("| %d | %s | %s | **%s** | %s | %s |"
              % (t["turn"], t["role"], t["text"], t["verdict"], "+".join(t["codes"]),
                 "; ".join("%s=%s" % (m["attr"], m["value"]) for m in t["memories"]) or "—"))
    print("\n## §11 逐句输出（规格要求：每句都必须有输出，不许静默跳过）")
    for r in rows_all:
        print("  #%-2d turn%-2d %-9s %-12s %-8s %s"
              % (r["sent_id"], r["turn"], r["role"], r["verdict"], r["code"], r["text"]))
    out["sentences"] = rows_all

    for m in [y for s in out["sample"] for y in s["memories"]]:
        if m.get("anchored_time"):
            print("  anchored: %s=%s -> %s" % (m["attr"], m["value"], m["anchored_time"]))

    print("\n## §11 附加四条边界 + 长期健康")
    for text, ev, ec, en in BOUNDARY:
        r = X.judge({"text": text}, "user", TS)
        ok = (r["verdict"] == ev and codes_of(r["code"]) == ec and len(r["memories"]) == en)
        out["boundaries"].append({"text": text, "verdict": r["verdict"], "code": r["code"],
                                  "memories": r["memories"], "expected_verdict": ev,
                                  "expected_codes": sorted(ec), "match": ok})
        if not ok:
            out["mismatches"].append({"text": text, "got": [r["verdict"], r["code"]],
                                      "want": [ev, sorted(ec)]})
        print("  %-18s %-12s %-6s %s" % (text, r["verdict"], r["code"],
                                          "OK" if ok else "MISMATCH"))

    print("\n## §12.3 时间锚定（第 9 句，必须 2026-10-28）")
    plan = [m for r in out["sample"] for m in r["memories"] if m["attr"] == "计划"]
    anchored = plan[0]["anchored_time"] if plan else None
    out["anchoring"] = {"phrase": "下周三", "ts": TS, "anchored_time": anchored,
                        "expected": "2026-10-28", "ok": anchored == "2026-10-28"}
    print("  下周三 + ts=%s -> %s (期望 2026-10-28) %s"
          % (TS, anchored, "OK" if out["anchoring"]["ok"] else "MISMATCH"))
    if not out["anchoring"]["ok"]:
        out["mismatches"].append({"anchoring": out["anchoring"]})

    print("\n## §12.4 去重（同一句重复一遍）")
    dup = SAMPLE + [{"role": "user", "text": "我住在广陵路 12 号 2 单元 602。", "ts": TS}]
    rows = X.run(dup)
    out["dedup"] = {"sentences": len(rows),
                    "residence_keep_sentences": [r["sent_id"] for r in rows
                                                 if any(m["attr"] == "住址"
                                                        for m in r["memories"])]}
    print("  住址出现在句 %s（去重由 m4_store 的 (subject,attr,value) 唯一键完成）"
          % out["dedup"]["residence_keep_sentences"])

    print("\n## §12.5 多值（先住广陵路，后搬到文昌路）")
    mv = [{"role": "user", "text": "我住在广陵路 12 号 2 单元 602。", "ts": TS},
          {"role": "user", "text": "我搬到文昌路 5 号了。", "ts": TS}]
    rows = X.run(mv)
    vals = [m["value"] for r in rows for m in r["memories"] if m["attr"] == "住址"]
    out["multi_value"] = {"values": vals, "count": len(vals),
                          "ok": len(vals) == 2}
    print("  住址两条：%s %s" % (vals, "OK" if out["multi_value"]["ok"] else "MISMATCH"))
    if not out["multi_value"]["ok"]:
        out["mismatches"].append({"multi_value": out["multi_value"]})

    out["summary"] = {"sample_all_match": all(s["match"] for s in out["sample"]),
                      "boundaries_all_match": all(b["match"] for b in out["boundaries"]),
                      "mismatch_count": len(out["mismatches"])}
    out["summary"]["all_pass"] = (out["summary"]["sample_all_match"]
                                  and out["summary"]["boundaries_all_match"]
                                  and out["anchoring"]["ok"] and out["multi_value"]["ok"])
    json.dump(out, io.open(os.path.join(HERE, "evidence_m4_judge.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("\nsummary:", json.dumps(out["summary"], ensure_ascii=False))
    if out["mismatches"]:
        print("mismatches:", json.dumps(out["mismatches"], ensure_ascii=False, indent=1))
    return 0 if out["summary"]["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
