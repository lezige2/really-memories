# -*- coding: utf-8 -*-
"""真实链路 debug：组级配对 + 挂载层 block_id（测试夹具，不改 schema/产品）。"""
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import temporal_pairing as TP          # noqa: E402
import chat_daily as D                 # noqa: E402

NOW = "2026-11-06T09:00:00"
ROW1 = "下周一我要去北京开会"
ROW2 = "北京开会地点在国贸"


def main():
    rows = [{"id": 1, "text": ROW1, "created_at": NOW, "group_id": "001"},
            {"id": 2, "text": ROW2, "created_at": NOW, "group_id": "001"}]
    r = TP.retrieve("我下周去哪？", NOW, rows)
    kept_ids = [b["id"] for g in r["groups"] for b in g["blocks"]]
    out = {"query": "我下周去哪？", "query_intervals": r["query_intervals"],
           "kept_group_ids": [g["group_id"] for g in r["groups"]],
           "kept_block_ids": kept_ids, "order": kept_ids,
           "order": kept_ids,
           "group_text": "\n".join(b["text"] for g in r["groups"] for b in g["blocks"]),
           "groups": r["groups"], "abstain": r["abstain"], "reason": r["reason"],
           "architecture_note": "prompt 只含指令+问题；记忆以 KV 块挂载；不存在把完整上下文原文拼进 prompt；本文件只记录 block_ids、块文本与挂载顺序。"}
    tmp = tempfile.mkdtemp(prefix="pairdbg_")
    model = os.path.join(tmp, "model.stub")
    D.install_fake_model(model)
    app = D.DailyApp(D.StubEngine(), db_path=os.path.join(tmp, "d.db"),
                     blocks_dir=os.path.join(tmp, "b"),
                     sessions_dir=os.path.join(tmp, "s"),
                     model_path=model, restore=False,
                     retrieval_mode="topk", topk=4, logger=False)
    ids = [app.remember(ROW1)["id"], app.remember(ROW2)["id"]]
    rows_db = {int(r[0]): r for r in app._rows()}
    mount_order = [i for i in kept_ids if i in rows_db] or ids
    app._last_selection = [{"source_id": i, "name": rows_db[i][1], "score": 1.0,
                            "signals": {}} for i in mount_order if i in rows_db]
    app._sync_mounts()
    mounted = [{"seq": b.get("seq"), "source_id": b.get("source_id"),
                "name": b.get("name")} for b in app.mounted_blocks]
    out["mounted_blocks"] = mounted
    out["mounted_order"] = [b["source_id"] for b in mounted]
    out["duplicate_blocks"] = len(mounted) - len({b["source_id"] for b in mounted})
    ok = (len(kept_ids) == 2 and len(set(kept_ids)) == 2
          and out["mounted_order"][:2] == kept_ids[:2])
    out["result"] = "pass" if ok else "fail"
    out["failure_note"] = "" if ok else "块数/顺序不满足（仅 1 块或顺序不符）"
    json.dump(out, open(os.path.join(ROOT, "out", "PAIRING-DEBUG.json"), "w",
                        encoding="utf-8"), ensure_ascii=False, indent=2)
    md = ["# 组级配对真实链路 debug", "", "- query: 我下周去哪？",
          "- kept_group_ids: %s" % out["kept_group_ids"],
          "- kept_block_ids/顺序: %s" % out["kept_block_ids"],
          "- mounted_blocks: %s" % mounted,
          "- duplicate_blocks: %s" % out["duplicate_blocks"],
          "- result: **%s** %s" % (out["result"], out["failure_note"]),
          "", "## 组内拼接文本", "```", out["group_text"], "```",
          "", "## 每块 intervals/anchor/phrase/reason"]
    for g in out["groups"]:
        for b in g["blocks"]:
            md.append("- block %s: intervals=%s anchor=%s phrase=%s reason=%s" % (
                b["id"], g["intervals"], g["anchor"], g["phrases"], g["reason"]))
    md += ["", "## 架构说明", out["architecture_note"]]
    open(os.path.join(ROOT, "out", "PAIRING-DEBUG.md"), "w",
         encoding="utf-8").write("\n".join(md) + "\n")
    print(json.dumps({k: out[k] for k in ("kept_group_ids", "kept_block_ids",
                                          "mounted_order", "result")},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
