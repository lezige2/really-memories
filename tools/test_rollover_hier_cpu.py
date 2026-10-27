# -*- coding: utf-8 -*-
"""test_rollover_hier_cpu.py -- T14 分层 rollover 验收（零 GPU，fake engine）。

强制 `--rollover-at 0.05` 跑 5 轮：
  - 最旧 30–40% 原文逐轮写成 auto_turn 记忆块（原文 + KV 块）
  - 1 条 auto_summary 索引块，related_ids 指向原文块 + auto_archive 全文块
  - 全文归档 daily/archive/*.txt + *.meta.json sidecar（id/path 交叉引用）
  - 双向 related：原文/归档 -> 摘要；摘要 -> 原文/归档
  - 保留最近 60–70% 原文（kept_ratio），/status 暴露 before/after
  - 检索命中摘要 => related 1 跳展开 => 原文块被挂载，块路径可回查原文

Run: python -X utf8 tools/test_rollover_hier_cpu.py ; exit 0 = pass.
"""
import hashlib
import json
import os
import sys
import tempfile

os.environ["LLAMA_MEM_MODE"] = "strict"      # rollover 在 ask 前统一触发
os.environ["LLAMA_MEM_VERIFY"] = "0"

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import chat_daily as D  # noqa: E402
import memory_source as ms  # noqa: E402

FAILS = []


def check(name, cond, detail=""):
    if cond:
        print("ok   %s" % name)
    else:
        FAILS.append(name)
        print("FAIL %s %s" % (name, detail))


def main():
    tmp = tempfile.mkdtemp(prefix="roll_hier_")
    model = os.path.join(tmp, "model.stub")
    D.install_fake_model(model)
    app = D.DailyApp(
        D.StubEngine(),
        db_path=os.path.join(tmp, "daily.db"),
        blocks_dir=os.path.join(tmp, "blocks"),
        sessions_dir=os.path.join(tmp, "sessions"),
        model_path=model,
        restore=False,
        rollover_at=0.05,          # 验收要求的强制阈值
        n_ctx=1024,                # chat_budget=512 -> threshold=max(64, 25)=64
        chat_start=512,
        retrieval_mode="topk",
        topk=4,
        logger=False,
    )
    notices = []
    try:
        for i in range(5):
            r = app.ask("介绍一下第%d个历史景点的情况。" % (i + 1))
            if r.get("notice"):
                notices.append(r["notice"])
        check("five_rounds_triggered", len(notices) >= 1, str(notices[:2]))
        st = app.status()
        last = (st.get("rollover") or {}).get("last")
        check("status_rollover_last", isinstance(last, dict), str(last))
        check("status_before_gt_after",
              last and last["before_tokens"] > last["after_tokens"] > 0, str(last))
        check("kept_ratio_60_70", last and 0.60 <= last["kept_ratio"] <= 0.78,
              last and last["kept_ratio"])

        # -- 三类块都存在 ------------------------------------------------
        def rows(mode):
            return app.con.execute("SELECT id,text,path FROM memory_source s "
                                   "JOIN memory_block b ON b.source_id=s.id "
                                   "WHERE s.mode=?", (mode,)).fetchall()
        turns = rows("auto_turn")
        archs = rows("auto_archive")
        summ = rows("auto_summary")
        check("original_blocks_exist", len(turns) >= 1, len(turns))
        check("archive_block_exist", len(archs) >= 1, len(archs))
        check("summary_block_exist", len(summ) == 1, len(summ))
        check("original_text_preserved",
              turns and "用户：" in turns[0][1] and "助手：" in turns[0][1],
              turns[:1])

        # -- 归档文件 + sidecar（以最后一次 rollover 为准）----------------
        last = app._last_rollover
        summ_id = int(last["summary_id"])
        arch_id = int(last["archive_id"])
        turn_ids = [int(t) for t in last["turn_ids"]]
        last_txt = os.path.basename(last["archive_path"])
        adir = app._archive_dir()
        txts = sorted(f for f in os.listdir(adir) if f.endswith(".txt"))
        metas = sorted(f for f in os.listdir(adir) if f.endswith(".meta.json"))
        check("archive_file", len(txts) >= 1, txts)
        check("archive_sidecar", len(metas) == len(txts), "%s vs %s" % (txts, metas))
        sc = json.load(open(os.path.join(adir, last_txt + ".meta.json"),
                            encoding="utf-8"))
        check("sidecar_cross_ref",
              sc["summary_id"] == summ_id and sc["archive_id"] == arch_id
              and sc["turn_ids"] == turn_ids, str(sc))

        # -- 双向 related（最后一次 rollover 的三元组）---------------------
        rel = app._meta_get(summ_id)["related_ids"]
        check("summary_related_all",
              arch_id in rel and all(t in rel for t in turn_ids), str(rel))
        check("turn_to_summary_bidi",
              all(app._meta_get(t)["related_ids"] == [summ_id] for t in turn_ids),
              str([app._meta_get(t)["related_ids"] for t in turn_ids]))
        check("archive_to_summary_bidi",
              app._meta_get(arch_id)["related_ids"] == [summ_id],
              str(app._meta_get(arch_id)))
        check("archive_path_in_tags",
              ("archive:%s" % last_txt) in app._meta_get(summ_id)["tags"]
              and all(("archive:%s" % last_txt) in app._meta_get(t)["tags"]
                      for t in turn_ids), str(app._meta_get(summ_id)["tags"]))
        arch_row = app.con.execute("SELECT text FROM memory_source WHERE id=?",
                                   (arch_id,)).fetchone()
        check("archive_block_preserves_text",
              bool(arch_row) and "用户：" in arch_row[0], str(arch_row)[:80])

        # -- 块地址回查原文：source_hash 与 block path 都真实存在 ---------
        row = app._row_by_id(turn_ids[0])
        check("block_path_exists", os.path.exists(row[6]), row[6])
        check("original_text_hash_ok",
              ms.sha256_text(str(row[3])) == str(row[4]), row[4])

        # -- 检索：摘要命中 => 1 跳展开原文块并挂载 ----------------------
        app.rollover_at = 1.0        # 冻结 rollover，避免查询轮再压缩改变三元组
        sel = app._retrieval_select("自动摘要")
        ids = [s["source_id"] for s in sel]
        check("summary_hit", summ_id in ids, str(sel))
        check("related_expanded", any(t in ids for t in turn_ids), str(sel))
        check("related_deduped", len(ids) == len(set(ids)), str(sorted(ids)))
        app.ask("自动摘要里都记了什么？")
        mounted = [b["source_id"] for b in app.mounted_blocks]
        check("related_mounted", any(t in mounted for t in turn_ids), str(mounted))
        check("mounted_paths_exist",
              all(os.path.exists(b["path"]) for b in app.mounted_blocks),
              str([b["path"] for b in app.mounted_blocks]))

        print("\n%s" % ("ALL PASS" if not FAILS else "FAILURES: %r" % (FAILS,)))
        return 0 if not FAILS else 1
    finally:
        app.close()


if __name__ == "__main__":
    sys.exit(main())