import os, shutil, sqlite3, sys, hashlib

M4 = "D:/llama-mem/kvmem/m2_visibility/m4"
sys.path.insert(0, M4)
import m5_bridge as B

L2 = os.path.join(M4, "m4_memory.db")
ABL = os.path.join(M4, "_ablate", "m4_memory_noplate.db")
TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_probe_tmp")
os.makedirs(TMP, exist_ok=True)

def sha16(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]

rows = []

def rec(name, expect, got, ok, extra=""):
    rows.append((name, expect, got, ok, extra))

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

# ---- A1: registry missing -> refuse, message names the path
old_reg = B.REG_DB
B.REG_DB = os.path.join(TMP, "NOSUCH_chat.db")
k, m = run(lambda: B.ensure_db(db=os.path.join(TMP, "probeA.db")))
B.REG_DB = old_reg
rec("A1 registry missing", "OriginError + 'registry db missing at'", k,
    k == "OriginError" and "registry db missing at" in m, m[:70])

# ---- A2: gate refuses a None registry connection
k, m = run(lambda: B.select_m5_source(None, l2, sid, blk))
rec("A2 regcon None", "AssertionError", k, k == "AssertionError", m[:60])

# ---- fixture: main copy with the registry column renamed away
main_copy = os.path.join(TMP, "main_nocol.db")
shutil.copyfile(L2, main_copy)
c = sqlite3.connect(main_copy)
c.execute("ALTER TABLE memory_source RENAME COLUMN registry_source_id TO registry_source_id_rn")
c.commit(); c.close()
mc = sqlite3.connect(main_copy)

k, m = run(lambda: B.select_m5_source(reg, mc, sid, blk, declared_synthetic_db=False))
rec("B1 renamed, not declared", "SCHEMA ACCIDENT", k, "SCHEMA ACCIDENT" in m, m[:70])

k, m = run(lambda: B.select_m5_source(reg, mc, sid, blk, declared_synthetic_db=True))
rec("B2 renamed + declared", "refuse, no silent exemption", k, k != "NO-RAISE", m[:70])

k, r = run(lambda: B.select_m5_source(reg, abl, asid, ablk, declared_synthetic_db=True))
ok3 = k == "NO-RAISE" and r["synthetic"] is True and r["origin"].startswith("declared_synthetic:")
rec("B3 ablation + declared", "exempt with declared_synthetic: origin", k,
    ok3, "len=%s" % (len(r) if k == "NO-RAISE" else "n/a"))

k, m = run(lambda: B.select_m5_source(reg, abl, asid, ablk, declared_synthetic_db=False))
rec("B4 ablation not declared", "SCHEMA ACCIDENT", k, "SCHEMA ACCIDENT" in m, m[:70])

# ---- P7: misdeclared main db => case-2 error (fix the DECLARATION), no link action
k, m = run(lambda: B.select_m5_source(reg, mc, sid, blk, declared_synthetic_db=True))
case2 = ("DECLARED an ablation" in m) or ("declaration" in m.lower() and "ablate" in m.lower())
rec("P7 misdeclared main db", "case-2 error, no link-action string", k,
    k != "NO-RAISE" and case2 and ("m4_layer2_link.py --apply" not in m), m[:80])

# ---- P8: case-1 (column present, value NULL, not declared) => link action IS correct
unlinked = os.path.join(TMP, "main_unlinked.db")
shutil.copyfile(L2, unlinked)
u = sqlite3.connect(unlinked)
u.execute("UPDATE memory_source SET registry_source_id=NULL WHERE id=?", (sid,))
u.commit(); u.close()
uc = sqlite3.connect(unlinked)
k, m = run(lambda: B.select_m5_source(reg, uc, sid, blk, declared_synthetic_db=False))
rec("P8 unlinked, not declared", "case-1 error naming m4_layer2_link.py --apply", k,
    ("m4_layer2_link.py --apply" in m), m[:80])

w = max(len(r[0]) for r in rows)
abpass = 0
for name, expect, got, ok, extra in rows:
    if ok and name[0] in "AB":
        abpass += 1
    print("%-4s %-*s expect=%-38s got=%-13s %s" % ("PASS" if ok else "FAIL", w, name, expect, got, extra))

split_ok = rows[-2][3] and rows[-1][3]
print()
print("m5_bridge.py sha16 =", sha16(os.path.join(M4, "m5_bridge.py")))
print("A+B probes: %d/6 pass" % abpass)
print("split (#18): %s  (P7 case-2=%s, P8 case-1=%s)" % ("PASS" if split_ok else "FAIL", rows[-2][3], rows[-1][3]))
