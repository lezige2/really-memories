# -*- coding: utf-8 -*-
"""判据的第二份副本必须钉在声明原文上（纪律 14 / #17 / #22 / #24 / #29 / #31）。

判据有两份副本: M3-PREREG.md 与执行者的驱动代码。只记 sha 不够 ——
sha 说明【声明变了】，不说明【代码实现的是不是新那版】。

期望值不写在本文件里: 从 PREREG §11.5 解析 NAME = "STRING"（期望只有一份副本，就在声明里）。

七件事，每件单独能红（#31 单因子），红时指名:
  1. 重算 prereg sha16 与行数，与产物自报的比（#22；行数写明口径）
  2. §11.5 必须解析出 >=4 条，否则期望值本身失锚
  3. effective_criteria 每条必须与 §11.5 逐字相等（不做归一化）
  4. judgement.checks 必须是逐条命名的布尔表，S1/S2/S3/T1/T2/C1..C5/L1..L4 每族至少一条
  5. judgement.failed 必须由 checks 派生（#17）；_rejected_* 必须被 retired_criteria 或
     criteria_ruling.rejected_forms_kept_as_evidence 声明
  6. 换行自证三条: ① 归一化放在解析函数内部（不依赖调用方）② 打印每个被解析文件的换行风格
     ③ 文本模式与二进制 decode 各解析一次，断言条数相等且 > 0 —— 症状是「文本 4 / 二进制 0」，
     而两条路都成功返回，只有相等断言能红。--selftest 证明这条自证是承重的（4 vs 0）。
  7. 冻结须由登记断言，不是散文: PREREG-CHANGES.json 的 frozen 必须等于重算值，
     且当前 sha16 必须出现在某条 changes 的 to 里，且每条 changes 必须有 invalidates。

退出码由调用方 `cmd > file; echo rc=$?` 读取（#29）。
"""
import argparse, hashlib, io, json, os, re, shutil, sys, tempfile

Q = chr(34)
PREREG = "D:/llama-mem/kvmem/m2_visibility/mine/inspector/M3-PREREG.md"
REGISTER = "D:/llama-mem/kvmem/m2_visibility/mine/inspector/PREREG-CHANGES.json"
FAMILIES = ["S1", "S2", "S3", "T1", "T2", "C1", "C2", "C3", "C4", "C5", "L1", "L2", "L3", "L4"]


def nl_style(blob):
    crlf = blob.count(b"\r\n")
    lf = blob.count(b"\n") - crlf
    if crlf and lf:
        return "mixed (crlf=%d lf=%d)" % (crlf, lf)
    if crlf:
        return "CRLF (crlf=%d)" % crlf
    return "LF (lf=%d)" % lf


def normalize(text):
    return text.replace(chr(13) + chr(10), chr(10))


def sha16_of(path):
    b = io.open(path, "rb").read()
    return hashlib.sha256(b).hexdigest()[:16], b


def section(text, n, do_normalize=True):
    t = normalize(text) if do_normalize else text
    m = re.search(r"(?ms)^## %d .*?(?=^## |\Z)" % n, t)
    return m.group(0) if m else ""


def parse_pairs(text, do_normalize=True):
    sec = section(text, 11, do_normalize=do_normalize)
    m = re.search(r"(?ms)^### 11\.5 .*?(?=^### |\Z)", sec)
    if not m:
        return {}
    pat = r"(?m)^(\w+) = " + Q + r"([^" + Q + r"]*)" + Q + r"$"
    return dict(re.findall(pat, m.group(0)))


def two_reader_proof(prereg_path):
    raw_b = io.open(prereg_path, "rb").read()
    via_bytes = parse_pairs(raw_b.decode("utf-8"))
    via_text = parse_pairs(io.open(prereg_path, encoding="utf-8").read())
    problems = []
    if not via_bytes:
        problems.append("NEWLINE: binary-decode read parsed 0 criteria from %s" % prereg_path)
    if not via_text:
        problems.append("NEWLINE: text-mode read parsed 0 criteria from %s" % prereg_path)
    if via_bytes != via_text:
        problems.append("NEWLINE: two readers disagree -- bytes %s vs text %s"
                        % (sorted(via_bytes), sorted(via_text)))
    return via_bytes, problems


def register_problems(sha16, lines):
    if not os.path.isfile(REGISTER):
        return ["REGISTER: %s missing -- the freeze is prose again" % REGISTER], []
    reg = json.loads(io.open(REGISTER, encoding="utf-8").read())
    fz = reg.get("frozen") or {}
    probs, notes = [], []
    if fz.get("sha16") != sha16 or fz.get("lines") != lines:
        probs.append("REGISTER: frozen says %r/%r but file is %r/%r"
                     % (fz.get("sha16"), fz.get("lines"), sha16, lines))
    else:
        notes.append("register freeze matches the file (sha16/lines)")
    changes = reg.get("changes") or []
    toes = [c.get("to", {}).get("sha16") for c in changes]
    if sha16 not in toes:
        probs.append("REGISTER: current sha16 %r appears in no changes entry to -- this edit was not registered first" % sha16)
    else:
        notes.append("register has a changes entry landing on the current sha16")
    for c in changes:
        if not str(c.get("invalidates") or "").strip():
            probs.append("REGISTER: a changes entry has no invalidates -- the next reader cannot tell what it voided")
    return probs, notes


def check(prereg_path, run_path):
    problems, notes = [], []
    sha16, blob = sha16_of(prereg_path)
    text = blob.decode("utf-8")
    lines = len(normalize(text).splitlines())
    notes.append("prereg newlines: %s" % nl_style(blob))
    notes.append("prereg lines: %d (splitlines on normalized text; ends_with_newline=%s)"
                 % (lines, blob.endswith(b"\n")))

    rp, rn = register_problems(sha16, lines)
    problems.extend(rp)
    notes.extend(rn)

    exp, nl_problems = two_reader_proof(prereg_path)
    problems.extend(nl_problems)
    if not exp:
        problems.append("PREREG: section 11.5 yielded 0 string(s), expected >= 4")
    elif len(exp) < 4:
        problems.append("PREREG: section 11.5 yielded %d string(s), expected >= 4" % len(exp))
    notes.append("expectations parsed from PREREG 11.5: %s" % sorted(exp))

    res = {"prereg_sha16": sha16, "prereg_lines": lines, "newlines": nl_style(blob)}
    if not run_path:
        return {"ok": not problems, "problems": problems + ["RUN: no artifact given"],
                "notes": notes, "recomputed": res}

    run_blob = io.open(run_path, "rb").read()
    notes.append("artifact newlines: %s" % nl_style(run_blob))
    d = json.loads(run_blob.decode("utf-8"))
    pre = d.get("prereg") if isinstance(d.get("prereg"), dict) else {}
    rep_sha = pre.get("sha16", d.get("prereg_sha16"))
    rep_lines = pre.get("lines", d.get("prereg_lines"))
    if rep_sha is None:
        problems.append("RUN: prereg sha16 missing -- cannot tell which declaration the code implemented")
    elif rep_sha != sha16:
        problems.append("RUN: prereg sha16 reported %r != recomputed %r" % (rep_sha, sha16))
    else:
        notes.append("prereg sha16 matches recomputation")
    if rep_lines is None:
        problems.append("RUN: prereg lines missing")
    elif rep_lines != lines:
        problems.append("RUN: prereg lines reported %r != recomputed %r (splitlines)" % (rep_lines, lines))

    eff = d.get("effective_criteria")
    if not isinstance(eff, dict):
        problems.append("RUN: effective_criteria missing or not an object -- the code copy cannot be compared")
    else:
        for k in sorted(exp):
            got = eff.get(k)
            if got is None:
                problems.append("RUN: effective_criteria lacks %r" % k)
            elif got != exp[k]:
                problems.append("RUN: effective_criteria[%r] = %r != declaration %r" % (k, got, exp[k]))
            else:
                notes.append("verbatim match: %s" % k)
        extra = sorted(set(eff) - set(exp))
        if extra:
            notes.append("effective_criteria also carries: %s" % extra)

    j = d.get("judgement") or {}
    checks = j.get("checks")
    if not isinstance(checks, dict):
        problems.append("RUN: judgement.checks is not a per-criterion table -- a blanket FAIL cannot say WHICH criterion is red")
        checks = {}
    else:
        retired0 = sorted(set(list(d.get("retired_criteria") or [])
                           + list((d.get("criteria_ruling") or {}).get("rejected_forms_kept_as_evidence") or [])))
        evidence_only = set(j.get("evidence_only") or []) | set(retired0)
        bad_criterion = sorted(n for n, v in checks.items()
                              if not n.startswith("_") and not isinstance(v, bool))
        if bad_criterion:
            problems.append("RUN: non-boolean entries under criterion names (a boolean table cannot be read at a glance): %s" % bad_criterion)
        aux_nonbool = sorted(n for n, v in checks.items()
                            if n.startswith("_") and not isinstance(v, bool) and n not in evidence_only)
        if aux_nonbool:
            problems.append("RUN: auxiliary key(s) %s sit inside the boolean table and are not declared in judgement.evidence_only -- move them out of `checks` or declare them, otherwise a reader cannot tell a criterion row from an annotation" % aux_nonbool)
        retired = list(d.get("retired_criteria") or [])
        ruling = d.get("criteria_ruling") or {}
        retired += list(ruling.get("rejected_forms_kept_as_evidence") or [])
        retired = sorted(set(retired))
        present_rejected = sorted(n for n in checks if n.startswith("_rejected"))
        undeclared = sorted(n for n in present_rejected if n not in retired)
        if undeclared:
            problems.append("RUN: %s look retired but no retired_criteria / criteria_ruling declares them" % undeclared)
        missing_fam = [f for f in FAMILIES
                       if not any(n.startswith(f) and not n.startswith("_rejected") for n in checks)]
        if missing_fam:
            problems.append("RUN: no non-retired check for families: %s" % missing_fam)
        derived = sorted(n for n, v in checks.items() if v is False and n not in retired)
        failed = j.get("failed")
        if not isinstance(failed, list):
            problems.append("RUN: judgement.failed missing -- which criteria are red is not reported")
        elif sorted(failed) != derived:
            problems.append("RUN: judgement.failed %r != derived from checks %r" % (sorted(failed), derived))
        else:
            notes.append("red criteria (derived): %s" % (derived or "none"))

    inv = j.get("invalid_rounds")
    if not isinstance(inv, list):
        problems.append("RUN: judgement.invalid_rounds missing -- validity (rule I) is not reported per round")
    else:
        notes.append("invalid rounds: %d" % len(inv))
    for k in ("rounds_planned", "rounds_valid"):
        if not isinstance(j.get(k), int):
            problems.append("RUN: judgement.%s missing or not an int" % k)

    return {"ok": not problems, "problems": problems, "notes": notes, "recomputed": res}


def selftest():
    d = tempfile.mkdtemp(prefix="_nl_selftest_")
    try:
        p = os.path.join(d, "crlf.md")
        raw = io.open(PREREG, "rb").read().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        io.open(p, "wb").write(raw)
        norm = parse_pairs(raw.decode("utf-8"))
        nonorm = parse_pairs(raw.decode("utf-8"), do_normalize=False)
        print("selftest file: %s  (%s)" % (os.path.basename(p), nl_style(raw)))
        print("  normalized parse   : %d entries %s" % (len(norm), sorted(norm)))
        print("  un-normalized parse: %d entries %s" % (len(nonorm), sorted(nonorm)))
        ok = len(norm) >= 4 and len(nonorm) == 0
        print("  guard is load-bearing:", ok, "(needs normalized>=4 AND unnormalized==0)")
        print()
        print("NEWLINE-SELFTEST:", "PASS" if ok else "FAIL")
        return 0 if ok else 1
    finally:
        shutil.rmtree(d, ignore_errors=True)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--prereg", default=PREREG)
    ap.add_argument("--run", default=None)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--register", default=REGISTER)
    a = ap.parse_args(argv)
    globals()["REGISTER"] = a.register
    if a.selftest:
        return selftest()
    r = check(a.prereg, a.run)
    rc = r["recomputed"]
    print("prereg_sha16 (recomputed) = %s" % rc["prereg_sha16"])
    print("prereg_lines (recomputed) = %d  (newlines=%s)" % (rc["prereg_lines"], rc["newlines"]))
    for n in r["notes"]:
        print("  note:", n)
    if r["problems"]:
        print()
        for p in r["problems"]:
            print("  RED:", p)
    print()
    print("PREREG-CONSISTENCY:", "PASS" if r["ok"] else "FAIL (%d problem(s))" % len(r["problems"]))
    print("UNCOVERED (by design):")
    print("  1. 逐字比对只覆盖 §11.5 的四条; §1-§8 的算式与 S1/S2/T1/T2/C/L 的文字描述不在射程内")
    print("  2. 不判断驱动代码里是否还有一份未导出的判据副本")
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))