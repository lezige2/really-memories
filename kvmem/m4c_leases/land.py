"""落地台账：两次采样 sha 一致才写（'我停了'必须是一个读数，不是一句保证）。

复核只认这里写的 sha16；与当前不符 ⇒ 那份报告作废。行数/字节不记 —— 行数有口径自由度。
"""
import hashlib, json, os, sys, time, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
FILES = ["kvmem/m4c_leases/land.py", "tools/chat.py", "tools/memory_source.py",
         "kvmem/m4c_leases/m4c_verdict.py", "kvmem/m4c_leases/m4c_harness.py",
         "kvmem/m4c_leases/m4c_selfcheck.py", "kvmem/m4c_leases/run_site3.py",
         "kvmem/m4c_leases/redcheck_delete.py", "kvmem/m4c_leases/witness_zero_feed.py",
         "kvmem/m4c_leases/run_m4c4.py"]
GAP_S = 32


def sample():
    out = {}
    for rel in FILES:
        b = open(os.path.join(ROOT, rel), "rb").read()
        out[rel] = {"sha16": hashlib.sha256(b).hexdigest()[:16], "bytes": len(b)}   # 只这两个：行数有口径自由度
    return out


def main():
    batch = os.environ.get("M4C_BATCH_ID") or uuid.uuid4().hex[:8]
    a = sample()
    time.sleep(GAP_S)
    b = sample()
    if a != b:
        diff = [k for k in a if a[k] != b[k]]
        print("仍在变化，不产出 LANDED：", diff)
        return 3
    rec = {"schema": "m4c_landed", "batch_id": batch, "sample_gap_s": GAP_S,
           "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "files": b, "samples": 2, "samples_identical": True,
           "how_to_verify": "复原每份文件 sha16；与这份不符 ⇒ 基于旧 sha 的报告作废，重新报"}
    out = os.path.join(HERE, "out", "LANDED-%s.json" % batch)
    json.dump(rec, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(json.dumps(rec, ensure_ascii=False, indent=1))
    print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
