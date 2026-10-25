# -*- coding: utf-8 -*-
"""M6b B2a：产物/台账**元数据补注**（不改任何读数，不跑引擎）。

inspector 要求补 4 个结构化字段 + 登记一处"与预登记的构造偏差"：
  - chat 产物：chat_arm / synthetic_state / block_not_detached / load_rc
  - 台账：arms.chat 同步这 4 字段；deviations[] 登记 P1 构造偏差
红线：
  - 不动 block 臂产物（d96c561a 保持）；不改读数字段（before/after/size/kill_point）
  - 预登记**不改**；偏差只登记在产物/台账里
  - 生成读数的脚本仍是 `_run_m6b_b2.py`（sha 2b73a648）；本脚本只补元数据，
    因此台账 `code_sha16.script` 保留 2b73a648，并另记 `metadata_augmentation`
"""
import hashlib
import json
import os
import sys
import time

ROOT = r"D:\llama-mem"
M6B = os.path.join(ROOT, "kvmem", "m2_visibility", "m6b")
OUT = os.path.join(M6B, "out")
CHAT_ART = os.path.join(OUT, "M6B-B2A-CHAT-RED.json")
BLOCK_ART = os.path.join(OUT, "M6B-B2A-RED.json")
LEDGER = os.path.join(M6B, "LANDED-m6b-b2a.json")
RUN_SCRIPT = os.path.join(M6B, "_run_m6b_b2.py")
RUN_SHA_EXPECTED = "2b73a648e1a371d9"


def sha16(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


def ent(p):
    return {"path": os.path.relpath(p, ROOT).replace("\\", "/"),
            "sha16": sha16(p), "bytes": os.path.getsize(p)}


DEVIATION = {
    "where": "P1 构造",
    "prereg": "chatA→chatB 两次新写",
    "actual": "真实 live.chat.kvmem 作 old、profile 作新写",
    "why": "真实 chat 作 old 才能证明'不可重建的既有文件被毁'；比预登记构造更强",
    "impact": "不改变判据四项，不改变四态",
}

CHAT_EXTRAS = {
    "chat_arm": "synthetic_state",
    "synthetic_state": {
        "source_seq_data": "profile 载入 seq0 作为新写入内容（合成状态，非真实对话 token）",
        "old_content": "真实 kvmem/sessions/live.chat.kvmem 副本",
        "note": "只为命中 session_state.py:229 eng.save(0, chat_file) 的 wb 直写截断路径；"
                "新写入内容是合成的，old 文件是真的。",
    },
    "block_not_detached": True,
    "block_not_detached_note":
        "产品 save_session 在 session_state.py:227 先 drop 块再 save(0,·)；本构造没有块可 drop，"
        "未做 detach ⇒ 标边界。不改变'wb 打开即截断'的危害，只说明 seq0 内容来源与产品不同。",
    "load_rc": "not_judged",
    "deviation_from_prereg": DEVIATION,
}


def main():
    run_sha = sha16(RUN_SCRIPT)
    assert run_sha == RUN_SHA_EXPECTED, (run_sha, RUN_SHA_EXPECTED)

    # 1) chat 产物：只加元数据字段，读数原样保留
    chat = json.load(open(CHAT_ART, encoding="utf-8"))
    assert chat["arm"] == "chat", chat.get("arm")
    before = {k: json.dumps(chat.get(k), sort_keys=True)
              for k in ("before_sha", "after_sha", "size_before", "size_after",
                        "final_size", "existed", "truncated", "kill_point")}
    chat.update(CHAT_EXTRAS)
    for k, v in before.items():
        assert json.dumps(chat.get(k), sort_keys=True) == v, k     # 读数不得变
    chat["metadata_augmentation"] = {
        "script": ent(os.path.abspath(__file__)),
        "readings_changed": False,
        "fields_added": list(CHAT_EXTRAS),
        "generated_with_script_sha16": run_sha,
        "note": "读数仍由 _run_m6b_b2.py（2b73a648）产生；本步只补 inspector 要求的标注",
    }
    with open(CHAT_ART, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(chat, fh, ensure_ascii=False, indent=1)

    # 2) 台账：arms.chat 同步字段 + deviations[]（与 corrections 分开）
    led = json.load(open(LEDGER, encoding="utf-8"))
    assert led["arms"]["block"]["artifact"]["sha16"] == "d96c561ac8ed3ee7", \
        led["arms"]["block"]["artifact"]
    assert led["code_sha16"]["sha16"] == run_sha, led["code_sha16"]
    led["arms"]["chat"].update(CHAT_EXTRAS)
    led["deviations"] = [DEVIATION]
    led["metadata_augmentation"] = chat["metadata_augmentation"]
    led["at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    with open(LEDGER, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(led, fh, ensure_ascii=False, indent=1)

    print("chat artifact:", CHAT_ART, os.path.getsize(CHAT_ART), sha16(CHAT_ART))
    print("ledger:       ", LEDGER, os.path.getsize(LEDGER), sha16(LEDGER))
    print("block (untouched):", BLOCK_ART, sha16(BLOCK_ART))
    print("run script:", run_sha, "| augment script:", sha16(os.path.abspath(__file__)),
          os.path.getsize(os.path.abspath(__file__)))
    return 0


if __name__ == "__main__":
    sys.exit(main())