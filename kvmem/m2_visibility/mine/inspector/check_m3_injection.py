# -*- coding: utf-8 -*-
"""注入单因子核验 + T/F/U 分层普查 + 引用存在性核验。

三个问题各有自己的仪器，混在一起就会互相掩护:
  inject/unit  这条判据在这个注入下真的红了吗？而且只动了那一个输入？（#31）
  census       15 条里真正能被证伪的有几条？U 必须由声明给出并附理由（#34）
  citations    每条 T 声称的红证据，指向的 case id / 产物 真的存在吗？它在那里真的红了吗？（#27 的推广）

退出码由调用方 `cmd > file; echo rc=$?` 读取（#29）；语义分离见 #E4:
  0 = PASS（全部核验通过）
  1 = 判据红（problems 非空）
  2 = 用法错（缺必填参数；argparse 自身的 exit(2) 同义）
  3 = 环境或编码错（打印/编码/IO 异常）—— 不许被读成「判据红」
"""
import argparse, json, io, os, re, sys

VOLATILE = {"secs", "round", "invalid_reasons", "answer", "answer_sha16", "ask_rc"}


def _safe_stdio():
    """cp936（中文 Windows 默认）控制台编不出 '⇒' 之类字符时会抛 UnicodeEncodeError,
    进程被解释器用 rc=1 收场 —— 与「判据红」同一个码、含义相反（#E4）。
    这里把两个流改成 errors='replace': 宁可个别字符打成 '?', 也不许整份汇总行消失。
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except Exception:
            pass


def _warn_if_output_degraded():
    """降级可以, 静默不行(#S2)。载荷(13/5/8/I1..I6/T/F/U)本身是 ASCII, 硬失败只会让 CI
    在怪环境里误报; 但「悄悄把 274 个中文变成 ?」才是不能接受的那种沉默。
    """
    enc = getattr(sys.stdout, "encoding", None) or "?"
    try:
        "中".encode(enc)
        return
    except Exception:
        pass
    try:
        # 这条警告本身必须是纯 ASCII: 它要在一个连中文都印不出的环境里保持可读
        print("WARN: stdout encoding %r cannot represent CJK text; non-ASCII characters in this"
              " report are printed as '?'. The criteria payload (counts / I1..I6 / T/F/U) is pure"
              " ASCII and stays readable, so this is NOT a failure (#S2)." % (enc,), file=sys.stderr)
    except Exception:
        pass


def _report_env_error(kind, exc):
    try:
        print("  ENV-ERROR (%s): %s: %s" % (kind, type(exc).__name__, exc), file=sys.stderr)
        print("INJECTION/CENSUS: ENV-ERROR (rc=3) -- 这不是判据红, 是环境/编码问题", file=sys.stderr)
    except Exception:
        pass


class UsageError(Exception):
    """「你给错了东西」—— 用法错, rc=2, 不是判据红也不是环境错。"""


def _err(msg=""):
    """所有错误与警告的唯一出口(#S1'): 只抓一路日志的调用方(CI 常只存 stderr)
    否则会漏掉一半用法错 —— 信息跑到错误的流里, 等于没报。"""
    print(msg, file=sys.stderr)


def load(p):
    if os.path.isdir(p):
        raise UsageError("输入是目录，不是文件: %s" % p)   # 用法错 rc=2, 不是权限问题
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
    decl, dd = {}, {}
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
    print("==> 这句话只能这么写: 本次运行真正被端到端验证的判据 %d 条; 仅单元可证伪 %d 条(端到端不可失败, 不计入);" % (len(n_e2e), len(n_unit)))
    print("   另有 %d 条不是独立命题(别名 %d + 复述 %d)。产物 verdict 单独读会把 %d 条一起写成「已验证」。"
          % (len(alias) + len(restate), len(alias), len(restate), len(rows)))
    census_io_rules(dd, ids, problems, notes)                 # §0 第五行: I1..I6 分两档
    census_layered_sentence(dd, distinct, n_e2e, n_unit, n_notfail, problems, notes)
    census_counting_rule(dd, judged, distinct, alias, restate, problems, notes)
    return problems, notes


def _rule_ids(which):
    """'I3 (red control B)' -> 'I3'；不认得的原样保留（宁可红，不许静默吞掉）。"""
    out = []
    for w in which or []:
        m = re.match(r"\s*(I\d+)", str(w))
        out.append(m.group(1) if m else str(w))
    return out


def census_io_rules(dd, ids, problems, notes):
    """M3-ACCEPT §0 的第五行: I1..I6 的两档红。

    三份数据交叉, 一个数都不硬编码:
      键集  <- declarations.io_criteria（每条自己的 unit/e2e 决定档位）
      档位  <- 上面的机械分档
      第二来源 <- declarations.summary.layered_sentence.invalid_round_rules
    两处不一致 = 双真相 双真相即红(N5); io_criteria 少一条即红(N1); 档位改了即红(N2)。
    """
    io = dd.get("io_criteria") or {}
    layered = ((dd.get("summary") or {}).get("layered_sentence") or {})
    irr = layered.get("invalid_round_rules") or {}
    declared_e2e = _rule_ids((irr.get("red_e2e") or {}).get("which"))
    declared_unit = _rule_ids((irr.get("red_unit_only") or {}).get("which"))

    if not io:
        problems.append("CENSUS-IO: declarations 里没有 io_criteria -- §0 第五行(I1..I6 分两档)无来源可核")
        return
    if not irr:
        problems.append("CENSUS-IO: declarations.summary.layered_sentence.invalid_round_rules 缺失 -- 第五行没有第二来源, 双真相无法排除")
        return

    keys = sorted(io)
    e2e = [k for k in keys if (io.get(k) or {}).get("e2e") == "T"]
    unit_only = [k for k in keys if (io.get(k) or {}).get("e2e") != "T" and (io.get(k) or {}).get("unit") == "T"]
    neither = [k for k in keys if (io.get(k) or {}).get("e2e") != "T" and (io.get(k) or {}).get("unit") != "T"]

    print()
    print("无效轮规则（来源 declarations.io_criteria, 按每条自己的 unit/e2e 分档）")
    print("  端到端红过     %d 条 : %s" % (len(e2e), " ".join(e2e) if e2e else "-"))
    print("  仅单元红过     %d 条 : %s" % (len(unit_only), " ".join(unit_only) if unit_only else "-"))
    if neither:
        print("  两档都没红     %d 条 : %s" % (len(neither), " ".join(neither)))

    if len(e2e) + len(unit_only) + len(neither) != len(keys):
        problems.append("CENSUS-IO ARITHMETIC: %d + %d + %d != io_criteria 的 %d 条"
                        % (len(e2e), len(unit_only), len(neither), len(keys)))

    declared_all = sorted(set(declared_e2e) | set(declared_unit))
    if keys != declared_all:
        problems.append("CENSUS-IO KEYS: io_criteria 只有 %d 条 %s, 而 layered_sentence.invalid_round_rules 列了 %d 条 %s"
                        " (少 %s / 多 %s) -- 第五行的键集不一致"
                        % (len(keys), keys, len(declared_all), declared_all,
                           sorted(set(declared_all) - set(keys)), sorted(set(keys) - set(declared_all))))
    if set(e2e) != set(declared_e2e):
        problems.append("CENSUS-IO 双真相: io_criteria 算出「端到端红过」= %s, 声明 = %s"
                        % (sorted(e2e), declared_e2e))
    if set(unit_only) != set(declared_unit):
        problems.append("CENSUS-IO 双真相: io_criteria 算出「仅单元红过」= %s, 声明 = %s"
                        % (sorted(unit_only), declared_unit))
    # 第三来源: 单元 falsifier 的 cases[].invalid_reasons 前缀 —— 声明说 unit=T, 就必须真有 case 让这条红过
    seen = {}
    for cid, c in (ids or {}).items():
        for reason in (c.get("invalid_reasons") or []):
            m = re.match(r"\s*(I\d+)", str(reason))
            if m:
                seen.setdefault(m.group(1), []).append(cid)
    if not ids:
        problems.append("CENSUS-IO EVIDENCE: 单元 falsifier 里没有任何可识别的 case -- 第三来源为空, 第五行无法三源核对(#S1)")
    else:
        declared_unit = [k for k in keys if (io.get(k) or {}).get("unit") == "T"]
        unbacked = [k for k in declared_unit if k not in seen]
        overclaimed = [k for k in keys if (io.get(k) or {}).get("unit") != "T" and k in seen]
        if unbacked:
            problems.append("CENSUS-IO EVIDENCE: %s 声明 unit=T, 但单元 falsifier 里没有任何 case 让它们红过 (invalid_reasons 前缀缺失)" % unbacked)
        if overclaimed:
            problems.append("CENSUS-IO EVIDENCE: %s 声明 unit!=T, 但单元 falsifier 里已有 case 让它们红过 %s -- 声明与产物不符"
                            % (overclaimed, {k: seen[k] for k in overclaimed}))
        if not unbacked and not overclaimed:
            notes.append("io rules: unit=T 的 %d 条在单元 falsifier 里都有实际红过的 case（%s）"
                         % (len(declared_unit), " ".join(declared_unit)))
    if keys == declared_all and set(e2e) == set(declared_e2e) and set(unit_only) == set(declared_unit):
        notes.append("io rules: 端到端红过 %d 条 / 仅单元红过 %d 条, 与 layered_sentence 逐条一致"
                     % (len(e2e), len(unit_only)))


def census_layered_sentence(dd, distinct, n_e2e, n_unit, n_notfail, problems, notes):
    """§0 前四行的第二来源核对: declared(summary.layered_sentence) vs derived(census 算)。"""
    ls = ((dd.get("summary") or {}).get("layered_sentence") or {})
    if not ls:
        problems.append("CENSUS-LAYERED: declarations.summary.layered_sentence 缺失 -- §0 前四行没有第二来源可比")
        return
    jd = ls.get("judged") or {}
    pairs = [("judged distinct claims", jd.get("distinct_claims"), len(distinct)),
             ("端到端被验证", (jd.get("verified_e2e_red") or {}).get("count"), len(n_e2e)),
             ("仅单元被验证", (jd.get("verified_unit_only") or {}).get("count"), len(n_unit)),
             ("端到端不可失败", (jd.get("not_falsifiable_e2e") or {}).get("count"), len(n_notfail))]
    bad = 0
    for label, declared, derived in pairs:
        if isinstance(declared, int) and declared != derived:
            problems.append("CENSUS-LAYERED: %s 声明 %d 条, census 算出 %d 条" % (label, declared, derived))
            bad += 1
    we = (jd.get("verified_e2e_red") or {}).get("which") or []
    wu = (jd.get("verified_unit_only") or {}).get("which") or []
    if we and sorted(we) != sorted(n_e2e):
        problems.append("CENSUS-LAYERED: 「端到端被验证」名单不一致: 声明 %s / 算出 %s" % (sorted(we), sorted(n_e2e)))
        bad += 1
    if wu and sorted(wu) != sorted(n_unit):
        problems.append("CENSUS-LAYERED: 「仅单元被验证」名单不一致: 声明 %s / 算出 %s" % (sorted(wu), sorted(n_unit)))
        bad += 1
    if not bad:
        notes.append("layered_sentence 前四行与 census 派生逐项一致（%d / %d / %d）"
                     % (len(distinct), len(n_e2e), len(n_unit)))


def census_counting_rule(dd, judged, distinct, alias, restate, problems, notes):
    """同一事实写两处 = 双真相。counting_rule 与 criteria[*] 必须逐条对得上(N5)。"""
    cr = dd.get("counting_rule") or {}
    if not cr:
        problems.append("CENSUS-COUNT: declarations 缺 counting_rule -- 别名/复述只有一处来源, 双真相无法排除")
        return
    n_judged, n_distinct = cr.get("judged_keys"), cr.get("distinct_claims")
    if isinstance(n_judged, int) and n_judged != len(judged):
        problems.append("DECLARED vs DERIVED: counting_rule.judged_keys=%d, census 读到 %d 条判据"
                        % (n_judged, len(judged)))
    if isinstance(n_distinct, int) and n_distinct != len(distinct):
        problems.append("DECLARED vs DERIVED: counting_rule.distinct_claims=%d, census 算出 %d 条独立命题"
                        % (n_distinct, len(distinct)))
    ca, crs = dict(cr.get("aliases") or {}), dict(cr.get("restatements") or {})
    diff_a = {k: (ca.get(k), alias.get(k)) for k in set(ca) | set(alias) if ca.get(k) != alias.get(k)}
    diff_r = {k: (crs.get(k), restate.get(k)) for k in set(crs) | set(restate) if crs.get(k) != restate.get(k)}
    if diff_a:
        problems.append("CENSUS-COUNT 双真相: counting_rule.aliases 与 criteria[*].alias_of 不一致 %s (counting_rule, criteria)" % diff_a)
    if diff_r:
        problems.append("CENSUS-COUNT 双真相: counting_rule.restatements 与 criteria[*].restates 不一致 %s (counting_rule, criteria)" % diff_r)
    if not diff_a and not diff_r:
        notes.append("counting_rule 与 criteria 的别名/复述逐条一致（%d 别名 / %d 复述）" % (len(ca), len(crs)))


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


def _cli(argv):
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
                _err("RED: --%s is required in inject mode" % k)
                return 2
        problems, notes = mode_inject(a.control, a.injected, a.field, a.target, a.allow_derived)
    elif a.mode == "unit":
        if not a.unit_file:
            _err("RED: --unit-file is required in unit mode")
            return 2
        problems, notes = mode_unit(a.unit_file)
    elif a.mode == "census":
        if not a.artifact:
            _err("RED: --artifact is required in census mode")
            return 2
        if not a.unit_falsifiers:
            _err("RED: --unit-falsifiers is required in census mode -- census 需要第三来源"
                  "(单元 falsifier 的 cases[].invalid_reasons)才能核 §0 第五行 I1..I6 分两档;"
                 " 少了它只剩两源, 第五行会被静默略过(#S1)")
            return 2
        problems, notes = mode_census(a.artifact, a.declarations, a.unit_falsifiers)
    else:
        if not (a.artifact and a.unit_falsifiers):
            _err("RED: --artifact and --unit-falsifiers are required in citations mode")
            return 2
        problems, notes = mode_citations(a.artifact, a.unit_falsifiers, a.declarations)
    for n in notes:
        print("  note:", n)
    if problems:
        _err()
        for p in problems:
            _err("  RED: " + str(p))
    print()
    print("INJECTION/CENSUS:", "PASS" if not problems else "FAIL (%d problem(s))" % len(problems))
    print("UNCOVERED (by design):")
    print("  1. 单因子只在产物字段层核验; 不核验驱动源码里是否还有第二个被改的量")
    print("  2. 普查只认声明文件里的 unit/e2e; 不判断某条 U 是否本该能失败")
    print("  3. 引用核验只证明「被引用的对象里它确实红过」; 不证明那次注入本身是单因子的（那是 unit 模式的事）")
    return 0 if not problems else 1


def main(argv):
    """退出码语义分离（#E4）：0 PASS / 1 判据红 / 2 用法错 / 3 环境或编码错。

    没有这层包装时, cp936 控制台打印 '⇒' 会抛 UnicodeEncodeError, 解释器用 rc=1 收场 --
    与「判据红」同一个码、含义相反, 调用方无从分辨。
    """
    _safe_stdio()
    _warn_if_output_degraded()
    try:
        return _cli(argv)
    except SystemExit:
        raise                      # argparse 的用法错自带 2
    except UsageError as exc:                 # 输入是目录等「给错了东西」= 用法错
        _err("RED: %s" % exc)
        _err("INJECTION/CENSUS: USAGE-ERROR (rc=2)")
        return 2
    except FileNotFoundError as exc:          # 输入路径写错 = 用法错(#S3)
        print("RED: 输入文件不存在: %s -- 这是用法错(路径写错), 既不是判据红也不是环境错" % exc.filename,
              file=sys.stderr)
        print("INJECTION/CENSUS: USAGE-ERROR (rc=2)", file=sys.stderr)
        return 2
    except (UnicodeError, OSError) as exc:   # 权限 / 坏 JSON / 编码 = 环境错
        _report_env_error("环境/编码错", exc)
        return 3
    except ValueError as exc:     # 坏 JSON / 结构不符 = 输入数据坏了, 仍归 3 但别叫「内部错」
        _report_env_error("数据错（坏 JSON 或结构不符）", exc)
        return 3
    except Exception as exc:       # 不许崩栈冒充判据红
        _report_env_error("内部错（非判据红）", exc)
        return 3


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))