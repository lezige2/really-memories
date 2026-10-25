# -*- coding: utf-8 -*-
"""注入单因子核验 + T/F/U 分层普查 + 引用存在性核验。

三个问题各有自己的仪器，混在一起就会互相掩护:
  inject/unit  这条判据在这个注入下真的红了吗？而且只动了那一个输入？（#31）
  census       15 条里真正能被证伪的有几条？U 必须由声明给出并附理由（#34）
  citations    每条 T 声称的红证据，指向的 case id / 产物 真的存在吗？它在那里真的红了吗？（#27 的推广）

退出码由调用方 `cmd > file; echo rc=$?` 读取（#29）。
"""
import argparse, json, io, os, re, sys

VOLATILE = {"secs", "round", "invalid_reasons", "answer", "answer_sha16", "ask_rc"}


def load(p):
    return json.load(io.open(p, encoding="utf-8"))


def round_fields(doc):
    return {r.get("round", i + 1): r for i, r in enumerate(doc.get("rounds") or [])}


def compare_checks(cc, ic, target, problems, notes):
    if set(cc) != set(ic):
        problems.append("CHECKS: the two sides do not judge the same criteria: only-control %s / only-injected %s"
                        % (sorted(set(cc) - set(ic)), sorted(set(ic) - set(cc))))
    if target in cc and target in ic:
        if not cc[target]:
            problems.append("TARGET: %s was already red on the control side -- the case proves nothing" % target)
        elif ic[target]:
            problems.append("TARGET: %s did not turn red under the injection" % target)
        else:
            notes.append("target %s: control T -> injected F" % target)
    else:
        problems.append("TARGET: %r is not a check on both sides" % target)
    other = sorted(n for n in cc if n in ic and n != target and cc[n] != ic[n])
    if other:
        problems.append("COLLATERAL: other criteria also changed: %s" % other)
    else:
        notes.append("all other criteria unchanged")


def mode_inject(control_p, injected_p, field, target, allow_derived):
    c, i = load(control_p), load(injected_p)
    problems, notes = [], []
    rc, ri = round_fields(c), round_fields(i)
    if sorted(rc) != sorted(ri):
        problems.append("ROUNDS: round sets differ %s vs %s" % (sorted(rc), sorted(ri)))
    allowed = {field} | set(allow_derived or [])
    diff = {}
    for n in sorted(rc):
        a, b = rc[n], ri.get(n) or {}
        for k in sorted(set(a) | set(b)):
            if k in VOLATILE:
                continue
            if a.get(k) != b.get(k):
                diff.setdefault(k, []).append(n)
    unexpected = {k: v for k, v in diff.items() if k not in allowed}
    notes.append("round fields that differ: %s" % ({k: len(v) for k, v in sorted(diff.items())} or "none"))
    if unexpected:
        problems.append("SINGLE-FACTOR: fields outside the declared set changed too: %s"
                        % {k: ("rounds " + str(v[:4])) for k, v in sorted(unexpected.items())})
    if field not in diff:
        problems.append("SINGLE-FACTOR: declared injection field %r did not change at all -- the input was not actually injected" % field)
    compare_checks((c.get("judgement") or {}).get("checks") or {},
                   (i.get("judgement") or {}).get("checks") or {}, target, problems, notes)
    return problems, notes


def mode_unit(path):
    d = load(path)
    problems, notes = [], []
    field = d.get("field")
    ci, ii = d.get("control_inputs") or {}, d.get("injected_inputs") or {}
    if not field:
        problems.append("UNIT: no `field` key -- cannot tell which single input was injected")
        return problems, notes
    diff = sorted(k for k in set(ci) | set(ii) if ci.get(k) != ii.get(k))
    notes.append("input fields that differ: %s" % (diff or "none"))
    if diff != [field]:
        problems.append("SINGLE-FACTOR: injected inputs differ on %s, declared %r -- exactly one field may differ" % (diff, field))
    notes.append("control %r -> injected %r" % (ci.get(field), ii.get(field)))
    target = d.get("target") or d.get("expect_red")
    if not target:
        problems.append("UNIT: no `target` / `expect_red` key")
        return problems, notes
    compare_checks(d.get("control_checks") or {}, d.get("injected_checks") or {}, target, problems, notes)
    return problems, notes


def case_list(unit):
    if isinstance(unit, dict):
        cases = unit.get("cases") or []
    else:
        cases = unit or []
    out = {}
    for c in cases:
        cid = c.get("id") or c.get("case") or c.get("name")
        if cid:
            out[cid] = c
    return out


def mode_census(artifact_p, decl_p, unit_p):
    problems, notes = [], []
    d = load(artifact_p)
    j = d.get("judgement") or {}
    status = j.get("criterion_status") or {}
    if not status:
        problems.append("CENSUS: no judgement.criterion_status -- cannot tell a value from a claim")
        return problems, notes
    judged = {}
    for k, v in status.items():
        if k.startswith("_"):
            continue
        judged[k] = (v or {}).get("value") if isinstance(v, dict) else v
    decl = {}
    if decl_p:
        dd = load(decl_p)
        decl = dd.get("criteria") or dd.get("claims") or {}
    else:
        problems.append("CENSUS: no --declarations given -- U cannot be told from 没有红, so every T reads as verified")
    alias, restate = {}, {}
    for k, v in decl.items():
        if not isinstance(v, dict):
            continue
        if v.get("alias_of"):
            alias[k] = v["alias_of"]
        if v.get("restates"):
            restate[k] = v["restates"]
    ids = case_list(load(unit_p)) if unit_p else {}
    rows = []
    for name in sorted(judged):
        dv = decl.get(name) or {}
        unit_v = dv.get("unit", "-")
        e2e_v = dv.get("e2e", "-")
        ev = [x for x in (dv.get("unit_evidence") or []) if x]
        missing = [x for x in ev if ids and x not in ids]
        rows.append((name, judged[name], unit_v, e2e_v, alias.get(name), restate.get(name), ev, missing))
    print("%-46s %-3s %-4s %-4s %s" % ("criterion", "run", "unit", "e2e", "note"))
    for name, val, uv, ev_, al, rs, evid, missing in rows:
        dv = decl.get(name) or {}   # must be re-fetched per row: the rows loop leaves dv pointing at the LAST claim
        note = ""
        if al:
            note = "alias of " + al
        elif rs:
            note = "restates " + rs
        if missing:
            note += ("  MISSING-EVIDENCE:" + str(missing))
        print("%-46s %-3s %-4s %-4s %s" % (name, val, uv, ev_, note))
        if missing:
            problems.append("CENSUS: %s cites unit evidence that does not exist: %s" % (name, missing))
        if uv == "-" and ev_ == "-":
            problems.append("CENSUS: %s has neither unit nor e2e declaration -- its T is unbacked" % name)
        if ev_ == "U" and not str(dv.get("why") or "").strip():
            problems.append("CENSUS: %s is e2e=U without a reason -- U 不计入通过数, 理由必须写下来" % name)
    distinct = [r for r in rows if not r[4] and not r[5]]
    n_e2e = [r[0] for r in distinct if r[3] == "T"]
    n_unit = [r[0] for r in distinct if r[3] != "T" and r[2] == "T"]
    n_none = [r[0] for r in distinct if r[3] != "T" and r[2] != "T"]
    n_notfail = [r[0] for r in distinct if r[3] != "T"]
    if len(n_e2e) + len(n_unit) + len(n_none) != len(distinct):
        problems.append("CENSUS ARITHMETIC: e2e %d + unit-only %d + unbacked %d != distinct claims %d"
                        % (len(n_e2e), len(n_unit), len(n_none), len(distinct)))
    if len(n_notfail) != len(n_unit) + len(n_none):
        problems.append("CENSUS ARITHMETIC: not_falsifiable_e2e %d != unit-only %d + unbacked %d"
                        % (len(n_notfail), len(n_unit), len(n_none)))
    notes.append("N+M+K = %d+%d+%d = %d distinct claims (checked)"
                 % (len(n_e2e), len(n_unit), len(n_none), len(distinct)))
    print()
    print("judged rows                          : %d" % len(rows))
    print("  of which alias(同一算式第二个名字)  : %d  %s" % (len(alias), sorted(alias)))
    print("  of which restates(被另一条蕴含)     : %d  %s" % (len(restate), sorted(restate)))
    print("judged distinct claims               : %d" % len(distinct))
    print("端到端被验证 (e2e=T)                 : %d  %s" % (len(n_e2e), n_e2e))
    print("仅单元被验证 (unit=T, e2e=U)         : %d  %s" % (len(n_unit), n_unit))
    print("not_falsifiable_e2e (e2e!=T)         : %d" % (len([r for r in distinct if r[3] != "T"])))
    if n_none:
        print("无任何证伪证据                       : %d  %s" % (len(n_none), n_none))
    tally = j.get("criterion_tally") or {}
    def as_int(v):
        if isinstance(v, bool):
            return None
        if isinstance(v, int):
            return v
        if isinstance(v, (list, tuple)):
            return len(v)
        return None
    declared = {}
    for k in ("verified_count", "independent_criteria", "total_judged", "T", "F", "U"):
        n = as_int(tally.get(k))
        if n is not None:
            declared[k if not k.isupper() else k + "_count"] = n
    derived = {"verified_count": len(rows),
               "total_judged": len(rows),
               "independent_criteria": len(distinct),
               "T_count": len([r for r in rows if r[1] == "T"]),
               "F_count": len([r for r in rows if r[1] == "F"]),
               "U_count": len([r for r in rows if r[1] == "U"])}
    for k in sorted(declared):
        if k in derived and declared[k] != derived[k]:
            problems.append("DECLARED vs DERIVED: artifact says %s=%r, census derives %r from %s -- first check which file was read"
                            % (k, declared[k], derived[k], os.path.basename(artifact_p)))
        elif k in derived:
            notes.append("declared %s=%r == derived" % (k, declared[k]))
    print()
    print("产物自报 tally: %s | verdict: %r" % (declared, j.get("verdict")))
    print("⇒ 这句话只能这么写: 本次运行真正被端到端验证的判据 %d 条; 仅单元可证伪 %d 条(端到端不可失败, 不计入);" % (len(n_e2e), len(n_unit)))
    print("   另有 %d 条不是独立命题(别名 %d + 复述 %d)。产物 verdict 单独读会把 %d 条一起写成「已验证」。"
          % (len(alias) + len(restate), len(alias), len(restate), len(rows)))
    return problems, notes


def mode_citations(artifact_p, unit_p, decl_p):
    problems, notes = [], []
    d = load(artifact_p)
    j = d.get("judgement") or {}
    status = j.get("criterion_status") or {}
    ids = case_list(load(unit_p)) if unit_p else {}
    decl = {}
    if decl_p:
        dd = load(decl_p)
        decl = dd.get("criteria") or dd.get("claims") or {}
    artdir = os.path.dirname(os.path.abspath(artifact_p))
    resolved = {}
    for name, v in sorted(status.items()):
        if name.startswith("_"):
            continue
        refs = (v or {}).get("falsified_by") or []
        if not refs:
            problems.append("CITATIONS: %s has no falsified_by -- its T claims a falsifier that is not named" % name)
            continue
        kinds = []
        for r in refs:
            if r in ids:
                c = ids[r]
                fl = c.get("flipped") or c.get("expected_flipped") or []
                if name in fl and not c.get("pass", True) is False:
                    kinds.append("unit:" + r)
                elif name in fl:
                    problems.append("CITATIONS: %s cites %s, which lists it but the case failed its own check" % (name, r))
                else:
                    problems.append("CITATIONS: %s cites %s, but that case%s flipped set does not contain it" % (name, r, ""))
                continue
            m = re.search(r"\(([^)]+\.json)\)", r)
            if m:
                p = os.path.join(artdir, os.path.basename(m.group(1)))
                if not os.path.isfile(p):
                    problems.append("CITATIONS: %s cites %r but %s does not exist" % (name, r, os.path.basename(m.group(1))))
                    continue
                other = load(p)
                other_checks = (other.get("judgement") or {}).get("checks") or {}
                if other_checks.get(name) is False:
                    kinds.append("e2e:" + os.path.basename(m.group(1)))
                else:
                    problems.append("CITATIONS: %s cites %r as its e2e falsifier, but there it is %r, not False"
                                    % (name, os.path.basename(m.group(1)), other_checks.get(name)))
                continue
            problems.append("CITATIONS: %s cites %r, which is neither a case id nor a (file.json) reference" % (name, r))
        resolved[name] = kinds
        dv = decl.get(name) or {}
        e2e_decl = dv.get("e2e")
        has_e2e = any(k.startswith("e2e:") for k in kinds)
        if e2e_decl == "T" and not has_e2e:
            problems.append("CITATIONS: declaration says %s e2e=T but no citation points at an e2e artifact" % name)
        if e2e_decl == "U" and has_e2e:
            problems.append("CITATIONS: declaration says %s e2e=U but it cites an e2e artifact where it is False" % name)
    for name in sorted(resolved):
        print("%-46s %s" % (name, ", ".join(resolved[name]) if resolved[name] else "NO RESOLVED CITATION"))
    print()
    print("resolvable citations: %d / %d criteria" % (len([n for n in resolved if resolved[n]]), len(resolved)))
    return problems, notes


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["inject", "unit", "census", "citations"], required=True)
    ap.add_argument("--control")
    ap.add_argument("--injected")
    ap.add_argument("--field")
    ap.add_argument("--target")
    ap.add_argument("--unit-file")
    ap.add_argument("--allow-derived", nargs="*", default=[])
    ap.add_argument("--artifact", "--run", dest="artifact")
    ap.add_argument("--artifacts", nargs="*", default=None)
    ap.add_argument("--declarations")
    ap.add_argument("--unit-falsifiers")
    a = ap.parse_args(argv)
    if not a.artifact and a.artifacts:
        a.artifact = a.artifacts[0]
    if a.mode == "inject":
        for k in ("control", "injected", "field", "target"):
            if not getattr(a, k):
                print("RED: --%s is required in inject mode" % k)
                return 2
        problems, notes = mode_inject(a.control, a.injected, a.field, a.target, a.allow_derived)
    elif a.mode == "unit":
        if not a.unit_file:
            print("RED: --unit-file is required in unit mode")
            return 2
        problems, notes = mode_unit(a.unit_file)
    elif a.mode == "census":
        if not a.artifact:
            print("RED: --artifact is required in census mode")
            return 2
        problems, notes = mode_census(a.artifact, a.declarations, a.unit_falsifiers)
    else:
        if not (a.artifact and a.unit_falsifiers):
            print("RED: --artifact and --unit-falsifiers are required in citations mode")
            return 2
        problems, notes = mode_citations(a.artifact, a.unit_falsifiers, a.declarations)
    for n in notes:
        print("  note:", n)
    if problems:
        print()
        for p in problems:
            print("  RED:", p)
    print()
    print("INJECTION/CENSUS:", "PASS" if not problems else "FAIL (%d problem(s))" % len(problems))
    print("UNCOVERED (by design):")
    print("  1. 单因子只在产物字段层核验; 不核验驱动源码里是否还有第二个被改的量")
    print("  2. 普查只认声明文件里的 unit/e2e; 不判断某条 U 是否本该能失败")
    print("  3. 引用核验只证明「被引用的对象里它确实红过」; 不证明那次注入本身是单因子的（那是 unit 模式的事）")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))