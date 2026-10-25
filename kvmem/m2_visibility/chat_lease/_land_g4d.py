# -*- coding: utf-8 -*-
"""task-36 G4d 落账：`out/M4C-fixture-rerun.json` + `LANDED-g4d.json`。

只读复算 + 汇总（臂由 redcheck_delete.py / run_site3.py 已跑，batch=g4d）。
口径：sha16=二进制 sha256[:16]；本台账不登记自身 sha。
"""
import glob
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
TOOLS = os.path.join(ROOT, "tools")
OUT = os.path.join(HERE, "out")
TMP = os.path.join(HERE, "tmp_db")
M4OUT = os.path.join(ROOT, "kvmem", "m4c_leases", "out")
PRODUCT = os.path.join(OUT, "M4C-fixture-rerun.json")
LEDGER = os.path.join(HERE, "LANDED-g4d.json")
SPEC = os.path.join(ROOT, "docs", "_work", "M2-FULL-S1-SPEC-lead.md")
BLOCKS = {k: os.path.join(ROOT, "kvmem", "m2_v1_14b", k + ".kvmem")
          for k in ("home", "project", "habit")}
FROZEN = {"analysis.py": os.path.join(TOOLS, "analysis.py"),
          "retrieval.py": os.path.join(TOOLS, "retrieval.py"),
          "evidence.py": os.path.join(TOOLS, "evidence.py")}
READ_KEYS = ("mode", "exit", "is_red", "expected_red", "die_kind", "assertions_status",
             "coverage_ok", "covers_declared", "covers_observed", "attaches_done",
             "attach_events_ok", "attaches_expected_min", "asserts_ran", "identity",
             "selfev", "hits")


def sha16(p):
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:16]


def ent(p):
    return {"path": os.path.relpath(p, ROOT).replace("\\", "/"),
            "sha16": sha16(p), "bytes": os.path.getsize(p)}


def one(pat):
    hits = sorted(glob.glob(pat))
    if not hits:
        raise SystemExit("missing product: %s" % pat)
    return hits[-1]


def load(p):
    return json.load(open(p, encoding="utf-8"))


def needles():
    lines = open(os.path.join(TOOLS, "chat.py"), encoding="utf-8").read().split("\n")
    res = {}
    for key, needle in (("site1_place_fresh", 'leases.reset(i, site="chat.place.fresh")'),
                        ("site3_unmount_after_detach",
                         'leases.reset(seq, site="m1.unmount.after_detach")'),
                        ("site4_mount_before_load",
                         'leases.reset(seq, site="m1.mount.before_load")')):
        hits = [i + 1 for i, ln in enumerate(lines) if needle in ln]
        res[key] = {"needle": needle, "line_nos": hits, "hit_count": len(hits),
                    "unique": len(hits) == 1}
    return res


def orphans(logp):
    if not logp or not os.path.exists(logp):
        return None
    out = []
    for e in load(logp):
        if e.get("id") == "site3.turn_orphan":
            out.append({"eval_point": e.get("eval_point"), "orphan": e.get("orphan"),
                        "chat_n": e.get("chat_n"), "status": e.get("status")})
    return out


def norm(rec):
    return {k: rec.get(k) for k in READ_KEYS}


def cmp_arm(name, pat, signed_path, db_copy):
    p = one(pat)
    rec = load(p)
    out = {"arm": name, "product": ent(p), "observed": norm(rec),
           "loads": rec.get("loads"), "orphans": orphans(rec.get("assert_log_path")),
           "db_copy": {"name": os.path.basename(db_copy), "sha16": sha16(db_copy),
                       "bytes": os.path.getsize(db_copy)},
           "signed_product": None, "diff_fields": None, "readings_match": None}
    if signed_path and os.path.exists(signed_path):
        s = load(signed_path)
        out["signed_product"] = ent(signed_path)
        diff = {k: {"signed": s.get(k), "observed": rec.get(k)}
                for k in READ_KEYS if s.get(k) != rec.get(k)}
        out["diff_fields"] = diff
        out["readings_match"] = not diff
    out["lineage"] = {"deleted_line_no": rec.get("deleted_line_no"),
                      "src_line_count": rec.get("src_line_count"),
                      "variant_line_count": rec.get("variant_line_count"),
                      "variant_sha16": rec.get("variant_sha16")}
    die = None
    logp = rec.get("assert_log_path")
    if logp and os.path.exists(logp):
        for e in load(logp):
            if e.get("id") == "die":
                die = e
    out["die"] = die
    return out


def main():
    base = cmp_arm("site1-base", os.path.join(M4OUT, "M4C-DELETE-SITE1-base-g4d-base-*.json"),
                   os.path.join(M4OUT, "M4C-DELETE-SITE1-base-b09-base-e6463aa2.json"),
                   os.path.join(TMP, "chat@g4d-site1base.db"))
    s3g = cmp_arm("site3-green", os.path.join(M4OUT, "M4C-SITE3-green-g4d-s3green-*.json"),
                  os.path.join(M4OUT, "M4C-SITE3-green-b09-green-b11f1875.json"),
                  os.path.join(TMP, "chat@g4d-s3green.db"))
    s3r = cmp_arm("site3-red(deleted unmount.after_detach)",
                  os.path.join(M4OUT, "M4C-SITE3-red-g4d-s3red-*.json"),
                  os.path.join(M4OUT, "M4C-SITE3-red-b09-red-1b6187f9.json"),
                  os.path.join(TMP, "chat@g4d-s3red.db"))
    s4b = cmp_arm("site4-base(字面 needle 的对照)",
                  os.path.join(M4OUT, "M4C-DELETE-SITE4-base-g4d-s4base-*.json"),
                  None, os.path.join(TMP, "chat@g4d-site4base.db"))
    s4d = cmp_arm("site4-deleted(删 m1.mount.before_load)",
                  os.path.join(M4OUT, "M4C-DELETE-SITE4-deleted-g4d-s4del-*.json"),
                  None, os.path.join(TMP, "chat@g4d-site4del.db"))
    same_s4 = {"loads_identical": s4b["loads"] == s4d["loads"],
               "orphans_identical": s4b["orphans"] == s4d["orphans"],
               "assertions_status_identical": s4b["observed"]["assertions_status"]
                                               == s4d["observed"]["assertions_status"],
               "no_red": s4d["observed"]["is_red"] is False
                         and s4d["observed"]["die_kind"] is None}
    ns = needles()
    prod = {
        "schema": "m4c_fixture_rerun_v1",
        "task": "task-36 G4d：M4-C 夹具臂重跑恢复回归链",
        "at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "batch": {"batch_id": "g4d", "ledger": ent(os.path.join(M4OUT, "LANDED-g4d.json")),
                  "note": "chat.py=22081c41 下新批台账（旧 b09/b10 与现盘不符，verify_landed 会 exit 3）"},
        "chat_py": ent(os.path.join(TOOLS, "chat.py")),
        "spec": dict(ent(SPEC), lines=132),
        "repo_db": ent(os.path.join(ROOT, "kvmem", "chat.db")),
        "needles": ns,
        "arms": {"site1_base": base, "site3_green": s3g, "site3_red": s3r,
                 "site4_base": s4b, "site4_deleted": s4d},
        "site4_no_effect": same_s4,
        "conclusion": {
            "base_一致": base["readings_match"],
            "承重红臂_site3_仍红": (s3r["observed"]["is_red"] is True
                                    and s3r["observed"]["assertions_status"] == "assertion_failed"
                                    and s3r["observed"]["die_kind"] == "assertion"),
            "site3_red_die_same_as_signed": (s3r["die"] or {}).get("message")
                                            == "M4-C 范围断言红 @m1.unmount: 调用流 hits=[]（0 条）"
                                               " != dropped=[2]（1 条）",
            "site3_green_readings_match": s3g["readings_match"],
            "site4_字面红臂无观测效果": same_s4["no_red"] and same_s4["loads_identical"]
                                        and same_s4["orphans_identical"],
            "回归链": "恢复：base 读数与 §2 逐项同（仅 chat_py_sha16 随修复变）；"
                      "承重红臂（site3 删 unmount.after_detach）仍红且 die 文案同签名；"
                      "green 全 0。字面 site4 红臂无效与 CLOSURE §site4『判据作废/被 site3 掩码』一致。",
        },
        "stop_item": {
            "asked": "task-36 字面要求『删 m1.mount.before_load ⇒ orphan 36→86 / green 0』",
            "observed": "site4-deleted：loads/orphan/assertions 与 base 逐项相同，无 die、无红；"
                        "orphan 读数为 0/0/0；而 green 臂（site3-green）也是 0/0/0。"
                        "『orphan 36→86』在 DELETE 产品里无落点（该读数属 CLOSURE §site3 的 "
                        "M4-C-4 测量臂，不是 before_load needle）。",
            "action": "停手报 lead：不调断言、不改夹具期望；请裁『红臂』是否指 site3 承重臂"
                      "（已实测仍红）而非 site4 字面 needle。",
            "orphan_36_86_scope": {
                "verdict": "未做（沿用 b10 历史读数，未重跑）",
                "why_not_this_task": "G4d 的 DELETE red/green 两臂 orphan 全 0/0/0；36→86 不在 G4d "
                                     "重跑范围",
                "belongs_to": "M4C-CLOSURE-lead.md §4.3 的 M4-C-4 测量臂（b10："
                              "m4c4/M4C4-deleted 4ada6cec / green 08a197d2）",
                "rerun_this_round": False,
                "inspector_recheck": "inspector 复算一致，但本轮未重跑，不把 b10 写成本轮读数",
                "non_blocking": "G4d 复验的是『删了必须红（die）』，不是『36→86 复现』",
                "if_wanted": "要补跑该臂另单报 lead",
            },
        },
        "four_state": {
            "base（site1）": "通过（与 §2 逐项同；chat_py sha 随修复变，属预期）",
            "承重红臂（site3 unmount.after_detach）": "通过（is_red true / assertion_failed / "
                                                      "die 文案同签名）",
            "green 臂（site3）": "通过（readings 与签名同；orphan 0/0/0）",
            "字面 site4 红臂": "未通过（删 before_load 无观测效果；CLOSURE 已判 site4 判据作废）",
            "site4 臂 coverage": "未接上（covers_declared site4 vs observed site3 ⇒ "
                                 "coverage_not_met，属夹具结构性，非本单引入）",
            "36→86（M4-C-4 测量臂）": "未做（沿用 b10 历史读数，未重跑；见 stop_item.orphan_36_86_scope）",
        },
        "no_self_sha": True,
    }
    with open(PRODUCT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(prod, fh, ensure_ascii=False, indent=1)
    fz = subprocess.run([sys.executable, "-X", "utf8", os.path.join(TOOLS, "freeze_check.py")],
                        capture_output=True, text=True, encoding="utf-8", errors="replace")
    ledger = {
        "schema": "landed_g4d_v1",
        "task": "task-36 G4d",
        "at": prod["at"],
        "product": ent(PRODUCT),
        "batch": prod["batch"],
        "chat_py": prod["chat_py"],
        "spec": prod["spec"],
        "repo_db": prod["repo_db"],
        "block_files": {k: ent(v) for k, v in BLOCKS.items()},
        "frozen_three": {k: ent(v) for k, v in FROZEN.items()},
        "code_change": {"changed": False,
                        "note": "本单未改代码；chat.py 保持 22081c41（task-35 G4a-2/G4a-3 后态）"},
        "needles": ns,
        "arms": prod["arms"],
        "site4_no_effect": same_s4,
        "conclusion": prod["conclusion"],
        "stop_item": prod["stop_item"],
        "db_copies": {"note": "m1 臂会无条件 rebuild 派生索引（G3 记法）：副本 before/after 不同属预期；"
                              "仓库 chat.db 未变",
                      "repo": ent(os.path.join(ROOT, "kvmem", "chat.db")),
                      "copies": {k: {"sha16": v["db_copy"]["sha16"]}
                                 for k, v in prod["arms"].items()}},
        "gaps": {
            "index_meta_docs": "index_meta.docs='2' 与 doc 10 行不一致（旧构建器遗留、M1.8 缺口、"
                               "非 KeyError 直接原因）；本单不修，继续登记",
            "site4_coverage": "site4 臂 covers_declared=['site4'] 但 cmd_m1 只产 site3 crit ⇒ "
                              "coverage_not_met（结构性，非本单引入）",
            "orphan_expectation": "『orphan 36→86』属 CLOSURE §site3 的 M4-C-4 测量臂，"
                                  "不在 DELETE 产品读数里；本单如实报 observed=0/0/0。"
                                  "本轮未重跑（rerun_this_round=false）；36→86 属 "
                                  "M4C-CLOSURE-lead.md §4.3 的 M4-C-4 测量臂"
                                  "（b10 4ada6cec / green 08a197d2），沿用历史读数",
        },
        "regressions": {"freeze_check": {
            "exit": fz.returncode,
            "first_line": (fz.stdout.strip().splitlines() or [""])[0],
            "status": "FROZEN" if "FROZEN" in fz.stdout else "RED",
        }},
        "four_state": prod["four_state"],
        "no_self_sha": True,
    }
    with open(LEDGER, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(ledger, fh, ensure_ascii=False, indent=1)
    print("product: %s (%d B, sha16=%s)" % (PRODUCT, os.path.getsize(PRODUCT), sha16(PRODUCT)))
    print("ledger:  %s (%d B, sha16=%s)" % (LEDGER, os.path.getsize(LEDGER), sha16(LEDGER)))
    print("base match:", base["readings_match"], "| s3red red:", prod["conclusion"]["承重红臂_site3_仍红"],
          "| s3red die same:", prod["conclusion"]["site3_red_die_same_as_signed"],
          "| site4 no effect:", prod["conclusion"]["site4_字面红臂无观测效果"])
    return 0


if __name__ == "__main__":
    sys.exit(main())