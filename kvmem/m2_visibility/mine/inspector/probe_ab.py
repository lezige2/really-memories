import os, shutil, sqlite3, sys, hashlib

M4 = "D:/llama-mem/kvmem/m2_visibility/m4"
sys.path.insert(0, M4)
import m5_bridge as B

L2 = os.path.join(M4, "m4_memory.db")
ABL = os.path.join(M4, "_ablate", "m4_memory_noplate.db")
TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_probe_tmp")
os.makedirs(TMP, exist_ok=True)

NEEDLE = "m4_layer2_link"          # copied from m5_bridge.py:173 / :190, never from prose
NEEDLE_SRC = "m5_bridge.py:173 (case-1 raise), :190 (new-row rejection)"

rows = []   # (name, expect, got, status PASS/FAIL/REC, extra)
def rec(name, expect, got, ok, extra="", recorded=False):
    rows.append((name, expect, got, "REC" if recorded else ("PASS" if ok else "FAIL"), extra))

def run(fn):
    try:
        return ("NO-RAISE", fn())
    except Exception as e:
        return (type(e).__name__, str(e))

reg = sqlite3.connect(B.REG_DB)
l2 = sqlite3.connect(L2)
sid = l2.execute("SELECT id FROM memory_source LIMIT 1").fetchone()[0]
blk = l2.execute("SELECT block_id FROM block LIMIT 1").fetchone()[0]
abl = sqlite3.connect(ABL)
asid = abl.execute("SELECT id FROM memory_source LIMIT 1").fetchone()[0]
ablk = abl.execute("SELECT block_id FROM block LIMIT 1").fetchone()[0]

def clone(name, stmts):
    p = os.path.join(TMP, name)
    if os.path.exists(p):
        os.remove(p)
    shutil.copyfile(L2, p)
    c = sqlite3.connect(p)
    for q in stmts:
        c.execute(q)
    c.commit(); c.close()
    return sqlite3.connect(p)

old = B.REG_DB
B.REG_DB = os.path.join(TMP, "NOSUCH_chat.db")
k, m = run(lambda: B.ensure_db(db=os.path.join(TMP, "probeA.db")))
B.REG_DB = old
rec("A1 registry missing", "OriginError naming path", k, k == "OriginError" and "registry db missing at" in m, m[:52])
k, m = run(lambda: B.select_m5_source(None, l2, sid, blk))
rec("A2 regcon None", "AssertionError", k, k == "AssertionError", m[:48])

nocol = clone("main_nocol.db", ["ALTER TABLE memory_source RENAME COLUMN registry_source_id TO registry_source_id_rn"])
k, m = run(lambda: B.select_m5_source(reg, nocol, sid, blk, declared_synthetic_db=False))
rec("B1 renamed, not declared", "SCHEMA ACCIDENT", k, "SCHEMA ACCIDENT" in m, m[:48])
k2, m2 = run(lambda: B.select_m5_source(reg, nocol, sid, blk, declared_synthetic_db=True))
rec("B2 renamed + declared", "refuse, no silent exemption", k2, k2 != "NO-RAISE", m2[:48])
k3, r3 = run(lambda: B.select_m5_source(reg, abl, asid, ablk, declared_synthetic_db=True))
rec("B3 ablation + declared", "exempt, declared_synthetic:", k3,
    k3 == "NO-RAISE" and r3["synthetic"] is True and r3["origin"].startswith("declared_synthetic:"),
    "len=%s" % (len(r3) if k3 == "NO-RAISE" else "n/a"))
k4, m4s = run(lambda: B.select_m5_source(reg, abl, asid, ablk, declared_synthetic_db=False))
rec("B4 ablation not declared", "SCHEMA ACCIDENT", k4, "SCHEMA ACCIDENT" in m4s, m4s[:48])

unlinked = clone("main_unlinked.db", ["UPDATE memory_source SET registry_source_id=NULL WHERE id=%d" % sid])
k5, m5s = run(lambda: B.select_m5_source(reg, unlinked, sid, blk, declared_synthetic_db=False))
needle_live = (k5 != "NO-RAISE") and (NEEDLE in m5s)

misdecl = clone("main_nocol2.db", ["ALTER TABLE memory_source RENAME COLUMN registry_source_id TO registry_source_id_rn"])
k6, m6s = run(lambda: B.select_m5_source(reg, misdecl, sid, blk, declared_synthetic_db=True))
needle_absent = (k6 != "NO-RAISE") and (NEEDLE not in m6s)

rec("P7 case-2 declaration wrong", "refuse, needle ABSENT, blames declaration", k6,
    needle_absent and "declaration itself is wrong" in m6s, m6s[:52])
rec("P8 case-1 linking", "refuse, needle PRESENT", k5, needle_live, m5s[:52])

# P9 ~ recorded negative: source_hash NULL does NOT reach the unlinked branch
hashhole = clone("main_nohash.db", ["UPDATE memory_source SET source_hash=NULL WHERE id=%d" % sid])
k7, r7 = run(lambda: B.select_m5_source(reg, hashhole, sid, blk, declared_synthetic_db=False))
o7 = r7["origin"] if k7 == "NO-RAISE" else ""
rec("P9 hash NULL => container path", "not the unlinked branch (关闭该猜想)", k7,
    "declared_human_turns:" in o7, o7[:40], recorded=True)

# P10 -> direction-aware: the normal unfinished state must be rejected with the REAL condition
ghost = clone("main_unlinked_newname.db", [
    "UPDATE memory_source SET registry_source_id=NULL, name='conv_2026-99-99_ghost' WHERE id=%d" % sid])
k10, m10 = run(lambda: B.select_m5_source(reg, ghost, sid, blk, declared_synthetic_db=False))
p10a = not ("invariant" in m10.lower() or "Unreachable" in m10)
p10b = ("has no registry link" in m10) and ("not in layer 1" in m10)
p10c = NEEDLE in m10
rec("P10 normal unfinished row", "real condition, no 'invariant' claim, correct action", k10,
    (k10 != "NO-RAISE") and p10a and p10b and p10c, m10[:56])

w = max(len(r[0]) for r in rows)
ab = 0
for name, expect, got, status, extra in rows:
    if status == "PASS" and name[0] in "AB":
        ab += 1
    print("%-4s %-*s expect=%-46s got=%-11s %s" % (status, w, name, expect, got, extra))

print()
print("needle               = %r" % NEEDLE)
print("needle_source        = %s" % NEEDLE_SRC)
print("needle_live          = %s   (present in case-1 text)" % needle_live)
print("needle_absent        = %s   (absent  in case-2 text)" % needle_absent)
print("needle_discriminates = %s" % (needle_live and needle_absent))
print("p10_no_invariant_claim = %s | p10_real_condition = %s | p10_correct_action = %s" % (p10a, p10b, p10c))
print("A+B probes           = %d/6 pass" % ab)
print("m5_bridge.py sha16   = %s" % hashlib.sha256(open(os.path.join(M4, "m5_bridge.py"), "rb").read()).hexdigest()[:16])
