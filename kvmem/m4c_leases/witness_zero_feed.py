"""覆盖见证的喂错验收：构造一个 cells_of != 0 的引擎，确认 _m4c_witness_cells_zero 会 die。

不响 ⇒ 判据无效，不许接入。产物带 run_id，与五跑同层。
"""
import io, json, os, sys, time, uuid, contextlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "tools")))
LOG = os.path.join(HERE, "out", "asserts-feed-%s.json" % uuid.uuid4().hex[:8])
os.environ["M4C_ASSERT_LOG_PATH"] = LOG
import chat


class FakeLeases:
    """只实现 cells_of：本判据唯一的输入。返回非 0 ⇒ 覆盖见证必须响。"""

    def __init__(self, cells):
        self._cells = cells

    def cells_of(self, seq):
        return self._cells


def main():
    rid = uuid.uuid4().hex[:8]
    rec = {"schema": "m4c_witness_zero_feed", "run_id": rid, "level": "unit",
           "level_note": "单元级：import chat 直接调私有函数并喂 FakeLeases。只证'能喂错时能红'，不证'接入之后它会红'",
           "target": "_m4c_witness_cells_zero", "cells_of_returned": 3,
           "chat_py_sha16": chat.__dict__["__loader__"].get_filename() and
           __import__("hashlib").sha256(open(chat.__file__, "rb").read()).hexdigest()[:16],
           "sampled_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            chat._m4c_witness_cells_zero(FakeLeases(3), 1, "feed.unit", "喂错演练")
        rec["exit"], rec["died"] = 0, False
    except SystemExit as exc:
        rec["exit"], rec["died"] = exc.code, True
    except Exception as exc:
        rec["exit"], rec["died"] = -1, False
        rec["note"] = "%s: %s" % (type(exc).__name__, exc)
    rec["die_message"] = None
    rec["log_entries"] = json.load(open(LOG, encoding="utf-8")) if os.path.exists(LOG) else []
    for a in rec["log_entries"]:
        if a.get("status") == "assertion_failed":
            rec["die_message"] = a.get("message")
    rec["exit_code"] = rec["exit"]
    rec["log_has_assertion_failed"] = any(a.get("status") == "assertion_failed"
                                          for a in rec["log_entries"])
    ok = rec["died"] and rec["exit"] == 1 and rec["log_has_assertion_failed"]
    rec["criterion_valid"] = ok
    out = os.path.join(HERE, "out", "WITNESS-ZERO-feed-%s.json" % rid)
    json.dump(rec, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(json.dumps({k: rec[k] for k in ("died", "exit", "log_has_assertion_failed",
                                          "criterion_valid")}, ensure_ascii=False))
    print("wrote", out)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
