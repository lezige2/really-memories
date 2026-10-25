# -*- coding: utf-8 -*-
"""快闸（毫秒级、零引擎）：喂合成 rec 验归因表 + 定义指纹 + 复核最近一份慢闸产物。

禁止 import chat / 任何引擎模块。慢闸（真跑 cmd_m1）另行执行，产物由本闸第 4 步复核。
顺序固定：先特异（已知正确对象不误报），后灵敏（人为构造的错误对象能红）。
"""
import ast, glob, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import m4c_verdict as V


def rec(**kw):
    base = {"finalized": True, "asserts_ran": 3, "finalize_error": None,
            "coverage_ok": True, "is_red": False, "expected_red": False,
            "def_mismatch": False, "def_mismatch_detail": [], "mode_unknown": False,
            "asserts_declared": 3,
            "covers_observed": ["site3"], "covers_declared": ["site3"],
            "harness_sha16": kw.pop("harness_id", None)}
    base.update(kw); return base


ROWS = [
    ("pass_green",         rec(),                                    0, None, []),
    ("pass_red",           rec(is_red=True, expected_red=True),     0, None, []),
    ("no_discrimination",  rec(is_red=False, expected_red=True),    5, "no_discrimination", ["no_discrimination"]),
    ("subject_broken",     rec(is_red=True),                        1, None, []),
    ("stale",              rec(harness_id="deadbeef"),              5, "stale", ["stale"]),
    ("not_finalized",      rec(finalized=False, asserts_ran=0),     5, "not_finalized", ["not_finalized", "asserts_short"]),
    ("finalize_error",     rec(finalized=False, asserts_ran=1, finalize_error="AssertionError('x')"),
                                                                    5, "finalize_error", ["finalize_error", "not_finalized", "asserts_short"]),
    ("coverage_shape",     rec(coverage_ok=None),                   5, "coverage_shape", ["coverage_shape"]),
    ("coverage_not_applicable_retired", rec(coverage_ok="not_applicable"), 5, "coverage_shape", ["coverage_shape"]),
    ("coverage_not_met",   rec(coverage_ok=False),                  5, "coverage_not_met", ["coverage_not_met"]),
    ("covered_but_red",    rec(coverage_ok=False, is_red=True),     5, "coverage_not_met", ["coverage_not_met"]),
    ("not_met_and_blind",  rec(coverage_ok=False, is_red=False, expected_red=True),
                                                                    5, "coverage_not_met", ["coverage_not_met", "no_discrimination"]),
    ("self_contradiction", rec(is_red=None),                        5, "self_contradiction", ["self_contradiction"]),
    ("def_mismatch",       rec(def_mismatch=True, def_mismatch_detail=["verdict:source_count=2"]),
                                                                    5, "def_mismatch", ["def_mismatch"]),
    ("def_mismatch_noDetail", rec(def_mismatch=True, def_mismatch_detail=[]),
                                                                    5, "def_mismatch", ["def_mismatch", "self_contradiction"]),
    ("asserts_short",      rec(asserts_declared=4),                 5, "asserts_short", ["asserts_short"]),
    ("asserts_none",       rec(asserts_declared=None),              5, "asserts_short", ["asserts_short"]),

    ("mode_unknown",       rec(mode_unknown=True),                  5, "mode_unknown", ["mode_unknown"]),

    # 配置读数（attaches_done / attach_events_ok）：三个方向 + 一个「不声明就不判」的对照。
    ("attach_config_ok",   rec(attaches_expected_min=1, attaches_done=2, attach_events_ok=True),
                                                                    0, None, []),
    ("attach_zero",        rec(attaches_expected_min=1, attaches_done=0, attach_events_ok=None),
                                                                    5, "attach_config_not_met", ["attach_config_not_met"]),
    ("attach_shape_bad",   rec(attaches_expected_min=1, attaches_done=2, attach_events_ok=False),
                                                                    5, "attach_config_not_met", ["attach_config_not_met"]),
    ("attach_count_missing", rec(attaches_expected_min=1, attaches_done=None),
                                                                    5, "attach_config_not_met", ["attach_config_not_met"]),
    ("attach_not_declared", rec(attaches_done=0),                   0, None, []),
]


def step1_table():
    """特异/灵敏同表：每行断言码 / instrument / hits / is_red 正交。

    合成输入 ⇒ 前提全由表给定 ⇒ 可以断言完整 hits 列表；真实运行只判第一格。
    """
    bad = 0
    cur = V.sha16(V.ME)
    for name, r, want_code, want_inst, want_hits in ROWS:
        r["harness_sha16_now"] = cur
        r["harness_sha16"] = "deadbeef" if name == "stale" else cur
        before = r.get("is_red")
        code = V.verdict(r)
        ok = (code == want_code and r.get("instrument") == want_inst
              and r.get("instrument_hits") == want_hits and r.get("is_red") is before)
        inv = bool(r.get("instrument_hits")) == (code == 5)
        print("  %-22s code=%d want=%d inst=%-18r hits=%s %s"
              % (name, code, want_code, r.get("instrument"), r.get("instrument_hits"),
                 "OK" if (ok and inv) else "FAIL"))
        if not (ok and inv):
            bad += 1
    return bad


def step3_defs():
    inv = V.def_inventory(globals(), os.path.abspath(__file__))
    bad = 0
    for n, c in inv["top"].items():
        if c > 1:
            print("  DUPLICATE def: %s x%d" % (n, c)); bad += 1
    missing = set(inv["top"]) - set(inv["fps"])
    if missing:
        print("  SHADOW (文本有、绑定无): %s" % sorted(missing)); bad += 1
    if not bad:
        print("  top-level defs=%d, all count==1, key sets equal" % len(inv["top"]))
    return bad


def step4_files():
    """归因层的 verdict/_hits 必须住在 m4c_verdict.py；夹具不得各带一份。"""
    bad = 0
    for mod_file in ("run_site3.py", "redcheck_delete.py"):
        p = os.path.join(HERE, mod_file)
        if not os.path.exists(p):
            continue
        txt = open(p, encoding="utf-8").read()
        for name in ("def verdict(", "def _hits(", "def instrument_hits("):
            if name in txt:
                print("  %s 里仍有本地 %s（应只在 m4c_verdict.py）" % (mod_file, name)); bad += 1
    if not bad:
        print("  归因层单点：verdict/_hits 仅存在于 m4c_verdict.py")
    return bad


def step2_guards():
    """守卫演练：三组喂法落盘。绿臂通过不构成证据（is_red=False 时根本看不到 exit）。"""
    feeds = [({"is_red": True, "exit": 2}, False, "能红"),
             ({"is_red": True, "exit": 1}, True, "合法红臂不误报"),
             ({"is_red": None, "exit": 0}, True, "缺失时给结论且不抛")]
    rows, bad = [], 0
    for rec, want, why in feeds:
        got = V.red_guard(rec)
        got_bool = V.bool_guard(rec)                      # 两个被测对象 ⇒ 两列期望，各判各的
        want_bool = isinstance(rec.get("is_red"), bool)
        ok = (got is want) and (got_bool is want_bool)
        rows.append({"rec": rec, "red_guard": got, "want_red": want,
                     "bool_guard": got_bool, "want_bool": want_bool, "why": why, "ok": ok})
        print("  red_guard%r -> %r (want %r) bool_guard -> %r (want %r) %s"
              % (rec, got, want, got_bool, want_bool, "OK" if ok else "FAIL"))
        bad += 0 if ok else 1
    json.dump({"feeds": rows, "contract_ok": True,
               "note": "守卫谓词可单独调用，故不改源文件、不注入即可证它能红"},
              open(os.path.join(HERE, "out", "HARNESS-GUARDS.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    return bad


def step2_order():
    """check_order 能红：喂一对对调的层序，必须报出那一对（纯函数，不改源文件）。"""
    swapped = ("finalize_error", "not_finalized")
    layers = list(V.LAYERS)
    i, j = layers.index(swapped[0]), layers.index(swapped[1])
    layers[i], layers[j] = layers[j], layers[i]
    bad = V.check_order(tuple(layers), V.ORDER_IMPLIES)
    print("  swapped order -> violations:", bad)
    return 0 if bad else 1


DECISION_FIELDS = ("is_red", "exit", "instrument", "instrument_hits", "coverage_ok",
                   "asserts_ran", "asserts_declared", "finalized", "finalize_error",
                   "contract_ok", "mode_unknown", "def_mismatch", "order_violations",
                   "identity_cross_check", "selfevidence", "die_kind",
                   "attaches_done", "attaches_expected_min", "attach_events_ok")
EVIDENCE_ONLY = ("sampled_at", "note", "deleted_line", "deleted_line_no", "assertions",
                 "loads", "run_id", "schema", "selection_per_turn", "want_sequence")


def step6_fields():
    """双向核：判定字段必须有人读；证据字段不得被当成判据。"""
    src = open(V.ME, encoding="utf-8").read() + open(os.path.abspath(__file__), encoding="utf-8").read()
    read = {k for k in DECISION_FIELDS if ('rec.get("%s")' % k) in src or ('rec["%s"]' % k) in src}
    unasserted = sorted(set(DECISION_FIELDS) - read)
    leaked = sorted(k for k in EVIDENCE_ONLY if 'rec.get("%s")' % k in src)
    print("  unasserted_fields:", unasserted, "| evidence_leaked_into_verdict:", leaked)
    return 0 if not unasserted and not leaked else 1


def _cite(p):
    """引用用文件字节算的身份（第三方算），自述单独嵌套：平铺会让下一个读者以为是同一来源。"""
    rec = json.load(open(p, encoding="utf-8"))
    return {"file": os.path.basename(p), "file_sha16": V.sha16(p),
            "kind": "injected" if rec.get("fixture_from_env") else "normal",
            "self": {"instrument": rec.get("instrument"), "exit": rec.get("exit"),
                     "selfevidence": rec.get("selfevidence")}}


def step5_latest():
    """逐类取最新：'最新' 与 '该有哪种形态' 不是同一件事，一旦有两类产物就会互相冒充。"""
    files = sorted(glob.glob(os.path.join(HERE, "out", "M4C-*.json")),
                   key=lambda p: os.path.getmtime(p))
    if not files:
        print("  no slow-gate artifact"); return 1, []
    by_kind = {}
    for p in files:
        d = json.load(open(p, encoding="utf-8"))
        k = "injected" if d.get("fixture_from_env") else "normal"
        by_kind[k] = p                     # 分类来自 run_kind（写于结果之前），不来自 finalize_error
    want = {"normal": (True, True, True), "injected": (True, False, True)}
    bad, cited = 0, []
    for k, p in sorted(by_kind.items()):
        rec = json.load(open(p, encoding="utf-8"))
        se = rec.get("selfevidence") or {}
        shape = (se.get("subject"), se.get("version"), se.get("verdict"))
        exp = want.get(k)
        ok = (exp is not None and shape == exp)
        if k == "normal":
            ok = ok and rec.get("die_kind") in (None, "assertion") \
                and rec.get("finalized") is True \
                and rec.get("asserts_ran") == rec.get("asserts_declared") \
                and rec.get("identity_cross_check") == "ok"
        if k == "injected":
            ok = ok and rec.get("instrument") == "finalize_error"
        print("  %s latest=%s shape=%r want=%r %s"
              % (k, os.path.basename(p), shape, exp, "OK" if ok else "FAIL"))
        cited.append(_cite(p))
        bad += 0 if ok else 1
    return bad, cited


def step8_assert_in_try():
    """try 体内的 assert 一旦失败，看到它的是 except（仪器坏），不是 hits（判据红）。

    可达性按「从 run_main 的 try 体调用可达」算：词法上在不在不等于语义上在不在。
    期望写成谓词名集合（意图），不写条数 —— 条数相等是集合相等的退化形式，一退化就同源。
    """
    src = open(os.path.join(HERE, "m4c_harness.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    fns = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    rm = fns.get("run_main")
    if rm is None:
        print("  run_main 未找到"); return 1
    tries = [n for n in ast.walk(rm) if isinstance(n, ast.Try)]
    if not tries:
        print("  run_main 内无 try"); return 1
    called = {c.func.id for t in tries for c in ast.walk(t)
              if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}
    got = set()
    for name in sorted(called & set(fns)):
        for n in ast.walk(fns[name]):
            if isinstance(n, ast.Assert):
                txt = ast.unparse(n.test)
                got.add(txt.split("(")[0])
    expected = {"V.bool_guard", "V.red_guard"}          # 设计意图，手写，不跟实现走
    print("  可达 assert 谓词=%s 期望=%s" % (sorted(got), sorted(expected)))
    if not expected:
        print("  退休：期望为空 ⇒ 检查本身该退休，不是通过"); return "retired"
    if not got:
        print("  扫空即失败：空结果不是干净，是没扫到"); return "violation: 扫空"
    return "ok" if got == expected else "violation: 集合不等 %s" % sorted(got - expected)


def step9_bypass_writer():
    """底层写入只允许被 _crit/_event 调用：专用入口只是"推荐写法"还是"唯一写法"，只能数调用点。"""
    src = open(os.path.join(os.path.dirname(HERE), "..", "tools", "chat.py"),
               encoding="utf-8").read()
    hits = [(n, ln) for n, ln in enumerate(src.split("\n"), 1) if "_m4c_write(" in ln]
    own = {n for n, ln in hits if ln.lstrip().startswith("def _m4c_write")}
    entry_calls = [n for n, ln in hits if "return _m4c_write(" in ln]
    bad = [n for n, ln in hits if n not in own and "return _m4c_write(" not in ln]
    print("  _m4c_write 调用点=%d（定义 1 + 入口 %d） 绕过=%s" % (len(hits), len(entry_calls), bad))
    return 0 if len(entry_calls) == 2 and not bad else 1


FORMS_SCOPE = ["tools/chat.py", "kvmem/m4c_leases/*.py"]
SCOPE_EXCLUDED = ["vendored/*（llama.cpp 相关脚本，非本次问题）"]


def _vendored_hits():
    """被排除的目录里那 9 条命中：不进缺口清单，但必须出现在扫描报告里。"""
    root = os.path.abspath(os.path.join(HERE, "..", ".."))
    n = 0
    for dirpath, dirnames, names in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__", "tools", "kvmem", "tmp", "out")]
        for f in names:
            if not f.endswith(".py"):
                continue
            try:
                tree = ast.parse(open(os.path.join(dirpath, f), encoding="utf-8").read())
            except (SyntaxError, UnicodeDecodeError):
                continue
            for fn in ast.walk(tree):
                if isinstance(fn, ast.FunctionDef) and len(fn.body) == 1 and isinstance(fn.body[0], ast.Expr):
                    n += 1
    return n


def _py_files():
    """只扫被测面：tools/chat.py + 本目录。别的目录里的 vendored 代码不是本批对象。"""
    root = os.path.abspath(os.path.join(HERE, "..", ".."))
    out = [os.path.join(root, "tools", "chat.py")]
    out += [os.path.join(HERE, n) for n in os.listdir(HERE) if n.endswith(".py")]
    return [p for p in out if os.path.exists(p)]


def step10_dead_after_return():
    """return/raise 之后的同级语句永不执行 —— 一条不可达的判据与一条不存在，在观测上等价。

    一个函数丢了它的 def 行时，函数体就变成"某个 return 之后的同级语句"：这正是它显形的形状。
    """
    hits, scanned = [], 0
    for p in _py_files():
        try:
            tree = ast.parse(open(p, encoding="utf-8").read())
        except (SyntaxError, UnicodeDecodeError):
            continue
        scanned += 1
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            body = fn.body
            for i, st in enumerate(body[:-1]):
                if isinstance(st, (ast.Return, ast.Raise)):
                    hits.append("%s:%d %s (return 后 %d 行死代码)"
                                % (os.path.basename(p), body[i + 1].lineno, fn.name,
                                   body[-1].end_lineno - body[i + 1].lineno + 1))
                    break
    resolved = sorted(os.path.basename(p) for p in _py_files())
    print("  scope_resolved(%d)=%s" % (len(resolved), resolved))
    print("  scope_excluded=%s excluded_hits=%d" % (SCOPE_EXCLUDED, _vendored_hits()))
    print("  dead_after_return: scope=%s files_scanned=%d hits=%s forms_covered=['after_return'] "
          "forms_not_covered=['shadowed','no_caller']"
          % (FORMS_SCOPE, scanned, hits if hits else "0"))
    return 0 if scanned and not hits else 1


def step11_docstring_only():
    """只有 docstring 的函数体：写完声明就没了实现。今天预期 0 条，缺省 ⇒ retired。"""
    hits, scanned = [], 0
    for p in _py_files():
        try:
            tree = ast.parse(open(p, encoding="utf-8").read())
        except (SyntaxError, UnicodeDecodeError):
            continue
        scanned += 1
        for fn in ast.walk(tree):
            if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) and len(fn.body) == 1 \
                    and isinstance(fn.body[0], ast.Expr) and isinstance(fn.body[0].value, ast.Constant):
                hits.append("%s:%d %s" % (os.path.basename(p), fn.lineno, fn.name))
    print("  docstring_only: scope=%s files_scanned=%d hits=%s"
          % (FORMS_SCOPE, scanned, hits if hits else "retired"))
    if not scanned:
        return "violation: 扫空"
    return "retired" if not hits else "violation: %s" % hits


def step12_uncalled_private_fn():
    """私有函数零调用点。0 命中必须配两个分母：扫了多少文件、看到多少私有函数。"""
    seen, bad, with_calls = 0, [], 0
    for p in _py_files():
        try:
            src = open(p, encoding="utf-8").read()
            tree = ast.parse(src)
        except (SyntaxError, UnicodeDecodeError):
            continue
        calls = {n.func.id for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        for fn in ast.walk(tree):
            if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                    and fn.name.startswith("_") and not fn.name.startswith("__"):
                seen += 1
                if calls:
                    with_calls += 1
                if fn.name not in calls:
                    bad.append("%s:%d %s" % (os.path.basename(p), fn.lineno, fn.name))
    print("  uncalled_private_fn: scope=%s files_scanned=%d private_fns_seen=%d with_calls=%d violations=%s"
          % (FORMS_SCOPE, len(_py_files()), seen, with_calls, bad if bad else "0"))
    if not seen or not with_calls:
        print("  no_discrimination：0 违规但没有可违规的对象，不能读成干净")
        return 0 if False else 1
    return 0 if not bad else 1


def attach_event_sites(src_text):
    """chat.py 里 `_event({"id": "chat.attach", ...})` 的调用点：[(行号, 是否带 seq)]。

    AST 而非字符串匹配：格式化/重命名不误报（这条判据的第一次误报决定它能否活到有用）。
    这是 attaches_done 的两个生产者；少一处 ⇒ 有一类 attach 永远不进读数。
    """
    tree = ast.parse(src_text)
    out = []
    for n in ast.walk(tree):
        if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "_event"):
            continue
        if not n.args or not isinstance(n.args[0], ast.Dict):
            continue
        entry = n.args[0]
        keys = [k.value for k in entry.keys if isinstance(k, ast.Constant)]
        consts = {k.value: v.value for k, v in zip(entry.keys, entry.values)
                  if isinstance(k, ast.Constant) and isinstance(v, ast.Constant)}
        if consts.get("id") == "chat.attach":
            out.append((n.lineno, "seq" in keys))
    return sorted(out)


def step13_attach_wiring():
    """跑前自检：配置读数的两个生产者（cmd_chat / cmd_m1 的 attach 之后各一处）。

    六个臂里 DELETE 只走 cmd_chat，site-4 才走 cmd_m1 —— 所以「两处都在」只能在这里（跑前）判。
    先验已知正确对象不误报，再用人为构造的「只有一处」证明这个计数判据能红（纯函数，不改源文件）。
    """
    src = open(os.path.join(os.path.dirname(HERE), "..", "tools", "chat.py"),
               encoding="utf-8").read()
    got = attach_event_sites(src)
    drill_src = ('def f():\n    for i in p:\n'
                 '        leases.attach(i, 0, 1, 2, site="m1.attach")\n'
                 '        _event({"id": "chat.attach", "seq": int(i)})\n')
    drill_n = len(attach_event_sites(drill_src))   # 构造上只有一处 ⇒ expect==2 的判据必须红
    ok = len(got) == 2 and all(has_seq for _ln, has_seq in got) and drill_n == 1
    print("  attach_event_sites=%r expect=2 | drill(1 site)=%d(⇒计数判据能红) %s"
          % (got, drill_n, "OK" if ok else "FAIL"))
    return 0 if ok else 1


def step7_prev_selfcheck():
    """核上一份 SELFCHECK 的 products_cited：每份存在且 file_sha16 相符（链条闭合）。"""
    files = sorted(glob.glob(os.path.join(HERE, "out", "SELFCHECK-*.json")),
                   key=lambda p: os.path.getmtime(p))
    if not files:
        print("  no previous SELFCHECK"); return 1
    prev = json.load(open(files[-1], encoding="utf-8"))
    bad = 0
    for c in prev.get("products_cited") or []:
        p = os.path.join(HERE, "out", c["file"])
        if not os.path.exists(p):
            print("  cited but missing:", c["file"]); bad += 1
        elif V.sha16(p) != c["file_sha16"]:
            print("  cited but changed:", c["file"]); bad += 1
    print("  prev=%s cited=%d bad=%d" % (os.path.basename(files[-1]),
                                         len(prev.get("products_cited") or []), bad))
    return 0 if bad == 0 else 1


def write_self_product(gates, retired, feeds, drill, cited):
    """快闸自产物：检查者不过同一套检查，它就是回声最后的藏身处。"""
    import uuid
    rid = uuid.uuid4().hex[:8]
    p = os.path.join(HERE, "out", "SELFCHECK-%s.json" % rid)
    json.dump({"run_id": rid, "self_sha16": V.sha16(os.path.abspath(__file__)),
               "verdict_sha16": V.sha16(V.ME),
               "gates_passed": gates, "gates_retired": retired, "feeds": feeds,
               "check_order_drill": drill, "products_cited": cited,
               "sampled_at": __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime())},
              open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("[self] 快闸自产物:", os.path.basename(p))
    return p


def main():
    gates, cited, retired = [], [], []
    print("[step1] 归因表（%d 行）" % len(ROWS)); b1 = step1_table(); gates.append("step1_table")
    print("[step2a] 守卫喂法（三组，落盘）"); b2a = step2_guards(); gates.append("step2a_guards")
    print("[step2b] 层序蕴含可红（对调演练，不改源文件）"); b2 = step2_order(); gates.append("step2b_order")
    print("[step3] 定义指纹"); b3 = step3_defs(); gates.append("step3_defs")
    print("[step4] 归因层单点"); b4 = step4_files(); gates.append("step4_single_author")
    print("[step5] 逐类复核最新慢闸产物"); b5, cited = step5_latest()
    print("[step6] 字段两类双向核"); b6 = step6_fields(); gates.append("step6_fields")
    print("[step7] 核上一份 SELFCHECK 的 products_cited"); b7 = step7_prev_selfcheck(); gates.append("step7_chain")
    print("[step9] 底层写入只有专用入口能碰"); b9 = step9_bypass_writer(); gates.append("step9_bypass_writer")
    print("[step10] 三种死法的第 1 种：return 之后"); b10 = step10_dead_after_return(); gates.append("step10_dead_after_return")
    print("[step12] 私有函数零调用点"); b12 = step12_uncalled_private_fn(); gates.append("step12_uncalled_private_fn")
    print("[step11] 只有 docstring 的函数"); r11 = step11_docstring_only()
    (retired.append("step11_docstring_only") if r11 == "retired" else gates.append("step11_docstring_only"))
    b11 = 0 if r11 in ("retired",) or r11 == "ok" else 1
    print("[step13] 配置读数的两个生产者（跑前自检）"); b13 = step13_attach_wiring(); gates.append("step13_attach_wiring")
    print("[step8] try 内可达 assert 谓词集合"); r8 = step8_assert_in_try()
    (retired.append("step8_assert_in_try") if r8 == "retired" else gates.append("step8_assert_in_try"))
    b8 = 0 if r8 in ("ok", "retired") else 1
    write_self_product(gates, retired, json.load(open(os.path.join(HERE, "out", "HARNESS-GUARDS.json"), encoding="utf-8"))["feeds"],
                       V.check_order(("finalize_error", "not_finalized") + tuple(
                           n for n in V.LAYERS if n not in ("finalize_error", "not_finalized")), V.ORDER_IMPLIES),
                       cited)
    total = sum(int(x) for x in (b1, b2a, b2, b3, b4, b5, b6, b7, b8, b9, b10, b11, b12, b13))
    print("SELFCHECK", "PASS" if total == 0 else "FAIL(%d)" % total)
    sys.exit(0 if total == 0 else 5)


if __name__ == "__main__":
    main()
