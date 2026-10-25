# -*- coding: utf-8 -*-
"""M4-C 归因层：零引擎依赖。身份、指纹、命中闭集、判定与退出码。

退出码表：0 通过 / 1 被测对象坏了 / 2 用法 / 3 环境 / 4 几何 / 5 仪器坏了。
本文件不许 import chat / kvslots / 任何引擎模块 —— 否则快闸(毫秒级)立刻变成慢闸(分钟级)。
"""
import ast, hashlib, inspect, os

ME = os.path.abspath(__file__)
SELFEVIDENCE_KEYS = ("fixture_file_used", "harness_sha16", "instrument")
LAYERS = ("mode_unknown", "def_mismatch", "stale", "finalize_error", "not_finalized",
          "attach_config_not_met", "coverage_shape", "asserts_short", "coverage_not_met",
          "no_discrimination", "self_contradiction")

# 层序按蕴含拓扑排序，强者在前：若 A 恒蕴含 B，B 排在 A 前会把 A 的全部命中吃掉。
ORDER_IMPLIES = (("finalize_error", "not_finalized"),
                 ("not_finalized", "coverage_shape"),
                 ("not_finalized", "asserts_short"),
                 ("not_finalized", "coverage_not_met"),
                 ("coverage_shape", "coverage_not_met"))


def bool_guard(rec):
    """全函数：零硬下标。缺失时给结论，不抛。"""
    return isinstance(rec.get("is_red"), bool)


def red_guard(rec):
    """红必须伴随 exit==1（die 路径）。exit 是另一个生产者（夹具捕获 SystemExit.code）。"""
    return (rec.get("is_red") is not True) or rec.get("exit") == 1


def check_order(layers=LAYERS, implies=ORDER_IMPLIES):
    """纯函数：返回违规对列表（不抛）。说不出哪一对的检查，与死值等价。"""
    idx = {n: i for i, n in enumerate(layers)}
    return ["%s>%s" % (a, b) for a, b in implies
            if idx.get(a, -1) >= idx.get(b, -1)]


def sha16(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


def def_fp(fn):
    """三元组指纹：文件名 / 行号 / code 名。文件名回答「活的是哪份」，行号回答「第几次定义」。"""
    c = fn.__code__
    return [os.path.basename(c.co_filename), c.co_firstlineno, c.co_name]


def def_inventory(module_globals, module_file):
    """两通道：ast 数顶层 def（抓重复定义），globals 看绑定（抓装饰器/变体文件）。

    嵌套 def 只数进 nested_def_names，绝不混进同一判据：判据混入两类对象后，它的"不等"说不清是哪一类。
    """
    tree = ast.parse(open(module_file, encoding="utf-8").read())
    top = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    nested = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    nested = [n for n in nested if n not in top]
    fns = {n: def_fp(o) for n, o in module_globals.items()
           if inspect.isfunction(o) and getattr(o, "__module__", None) == module_globals.get("__name__")}
    return {"top": {n: top.count(n) for n in sorted(set(top))},
            "nested": sorted(set(nested)), "fps": fns,
            "module_file": os.path.basename(module_file)}


def def_mismatch_detail(inv, own_file):
    """三谓词各自的证据；空列表 = 没问题。命中却说不出内容 ⇒ 由调用方判 self_contradiction。"""
    detail = []
    for n, c in inv["top"].items():
        if c > 1:
            detail.append("%s:source_count=%d" % (n, c))
    return detail


def site_of(entry):
    """站点由 id 前缀派生（id 是唯一作者）：'site3.unmount.flow' -> 3；'die' -> None。"""
    import re
    m = re.match(r"site(\d+)\.", entry.get("id", ""))
    return int(m.group(1)) if m else None


def instrument_hits(rec):
    """闭集，每值一谓词，直线代码、不抛。不变式也写成 hit，不 assert。"""
    hits = []
    if rec.get("contract_violation") or rec.get("contract_ok") is False:
        hits.append("self_contradiction")      # chat.py 与 harness 的契约破裂（kind 与 status 不再等价）
    if rec.get("order_violations"):
        hits.append("self_contradiction")      # 层序违反蕴含 ⇒ 归因自相矛盾，仪器坏了
    if rec.get("mode_unknown"):
        hits.append("mode_unknown")
    if rec.get("def_mismatch"):
        hits.append("def_mismatch")
    if rec.get("harness_sha16") != rec.get("harness_sha16_now"):
        hits.append("stale")
    if not rec.get("finalized"):
        hits.append("not_finalized")
    if rec.get("finalize_error"):
        hits.append("finalize_error")
    # 配置读数（§6.22 第四样）：执行过的次数没到期望，或条目不是 _event 的形状 ⇒ 这条读数不成立。
    # 三态：期望缺省（None）= 本臂不声明这条读数 ⇒ 不判（其余四臂形态）；读数缺失（None）≠ 通过（§6.3）。
    _exp, _done = rec.get("attaches_expected_min"), rec.get("attaches_done")
    if _exp is not None and not (isinstance(_exp, int) and isinstance(_done, int) and _done >= _exp):
        hits.append("attach_config_not_met")
    if rec.get("attach_events_ok") is False:
        hits.append("attach_config_not_met")
    cov = rec.get("coverage_ok")
    if cov not in (True, False):
        hits.append("coverage_shape")
    elif cov is False:
        hits.append("coverage_not_met")
    decl = rec.get("asserts_declared")
    if not decl or rec.get("asserts_ran") != decl:      # 0/None 都是 falsy：删光 assert 也命中
        hits.append("asserts_short")
    if rec.get("expected_red") is True and rec.get("is_red") is not True:
        hits.append("no_discrimination")
    if rec.get("is_red") is None and not hits:
        hits.append("self_contradiction")
    if "def_mismatch" in hits and not rec.get("def_mismatch_detail"):
        hits.append("self_contradiction")
    return [h for h in LAYERS if h in hits]


def verdict(rec):
    """层序 = 依赖序：仪器有效性先于读数比较。只报第一层，记录全部 hits。

    harness_id 由调用方给（本文件 sha16 或 夹具 + 本文件 的组合），不放进 rec 让调用点传错期望。
    """
    hits = instrument_hits(rec)
    rec["instrument_hits"] = hits
    rec["instrument"] = hits[0] if hits else None
    if hits:
        print("INSTRUMENT %s (hits=%s): finalized=%r asserts_ran=%r coverage_ok=%r is_red=%r"
              % (hits[0], hits, rec.get("finalized"), rec.get("asserts_ran"),
                 rec.get("coverage_ok"), rec.get("is_red")))
        return 5
    if rec.get("is_red") is True and rec.get("expected_red") is not True:
        print("VERDICT MISMATCH: 行还在、断言响了 ⇒ 被测对象坏了")
        return 1
    return 0
