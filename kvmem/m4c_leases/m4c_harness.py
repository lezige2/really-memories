# -*- coding: utf-8 -*-
"""M4-C 夹具公共层（引擎侧）：参数化导入、台账读取、执行与写盘。

归因与判定在 m4c_verdict.py（零引擎依赖）；本文件只做 I/O，不定义第二份 verdict。
"""
import ast, inspect, json, os, sys

import m4c_verdict as V

sha16 = V.sha16


def asserts_declared(fn):
    """门槛由源码派生：唯一同名定义 + 函数体直属语句里的 assert 数。

    重复定义 ⇒ 返回 None（"数不出来"落进仪器坏了，不落进通过）；只数直属层 ⇒ 写在 if 里的
    assert 既不该被计数、也不该被执行 —— 同一处结构规则同时消灭了假红（绿臂只跑 1 条）。
    """
    try:
        src = open(fn.__code__.co_filename, encoding="utf-8").read()
        tree = ast.parse(src)
        nodes = [n for n in ast.walk(tree)
                 if isinstance(n, ast.FunctionDef) and n.name == fn.__name__]
        if len(nodes) != 1:
            return None
        return len([s for s in nodes[0].body if isinstance(s, ast.Assert)])
    except Exception:
        return None


def harness_id(fixture_file):
    """身份三段：夹具自身 : 本文件 : 归因层。任一改动 ⇒ 旧产物 stale，不会静默沿用。"""
    return ":".join([V.sha16(os.path.abspath(fixture_file)),
                     V.sha16(os.path.abspath(__file__)), V.sha16(V.ME)])


def load(path, name):
    """变体落成 .snap（不许长得像源码）⇒ 不靠扩展名推断 loader，显式给 SourceFileLoader。"""
    import importlib.machinery, importlib.util
    loader = importlib.machinery.SourceFileLoader(name, path)
    spec = importlib.util.spec_from_loader(name, loader)
    m = importlib.util.module_from_spec(spec); sys.modules[name] = m; loader.exec_module(m); return m


def finalize(rec, logp, declared):
    """四步按序：id 派生站点 -> covers_observed -> coverage_ok 三值 -> 断言状态五态。"""
    rec.setdefault("batch_id", os.environ.get("M4C_BATCH_ID", "nobatch"))
    rec["asserts_ran"] = 0
    rec["covers_declared"] = declared
    rec["assertions"] = None
    if os.path.exists(logp):
        rec["assertions"] = json.load(open(logp, encoding="utf-8"))
    log = rec["assertions"] or []
    sites = {V.site_of(a) for a in log
             if a.get("role") == "criterion" and a.get("status") != "skipped"}   # 加一条事件日志在结构上不可能污染覆盖集
    sites = {s for s in sites if s is not None}      # die 条目 site_of = None，不参与排序
    rec["covers_observed"] = ["site%d" % s for s in sorted(sites)]
    rec["coverage_ok"] = rec["covers_observed"] == rec["covers_declared"]
    rec["assertion_failed_in_log"] = any(a.get("status") == "assertion_failed" for a in log)
    # 单通道：is_red 只由 kind 派生。status=="assertion_failed" 是同一事实的另一种拼法，不许当第二个来源。
    rec["die_kind"] = "assertion" if any(a.get("kind") == "assertion" for a in log) else (
        "crash" if rec.get("exit") not in (0, None) else None)
    statuses = {a.get("status") for a in log}
    if rec["die_kind"] == "assertion":
        rec["assertions_status"] = "assertion_failed"
    elif rec["die_kind"] == "crash":
        rec["assertions_status"] = "crash"
    elif rec["assertions"] is None:
        rec["assertions_status"] = "log_missing"
    elif statuses == {"skipped"}:
        rec["assertions_status"] = "skipped"
    else:
        rec["assertions_status"] = "checked"
    rec["contract_ok"] = (rec["die_kind"] == "assertion") == rec["assertion_failed_in_log"]
    rec["is_red"] = rec["die_kind"] == "assertion"
    # 三条常驻守卫：直属于函数体（无条件执行），每条 assert 前自增 ⇒ asserts_ran 只可能由 assert 推进
    rec["asserts_ran"] += 1
    assert V.bool_guard(rec), "is_red 必须是 bool：null 在 if 里会被读成「不是红」"
    rec["asserts_ran"] += 1
    assert V.red_guard(rec), "红必须伴随 exit==1（die 路径），不是崩溃或正常结束"
    rec["contract_violation"] = not rec["contract_ok"]     # 判据红走 hits，不借道 except
    rec["finalize_completed"] = True      # 末行正向盖章：「没有异常」不等于「跑完了」
    return rec


HERE = os.path.dirname(os.path.abspath(__file__))

LANDED_FILES = ["tools/chat.py", "tools/memory_source.py",
                "kvmem/m4c_leases/m4c_verdict.py", "kvmem/m4c_leases/m4c_harness.py",
                "kvmem/m4c_leases/m4c_selfcheck.py", "kvmem/m4c_leases/run_site3.py",
                "kvmem/m4c_leases/redcheck_delete.py", "kvmem/m4c_leases/witness_zero_feed.py",
                "kvmem/m4c_leases/run_m4c4.py"]


def verify_landed(batch):
    """跑之前先核台账：两个人若在不同文件上，读数什么也说明不了。不符 ⇒ exit 3（不是 5）。"""
    p = os.path.join(HERE, "out", "LANDED-%s.json" % batch)
    if not os.path.exists(p):
        print("LANDED 缺失：%s（先跑 land.py）" % os.path.basename(p))
        return 3
    want = json.load(open(p, encoding="utf-8"))["files"]
    root = os.path.abspath(os.path.join(HERE, "..", ".."))
    for rel in LANDED_FILES:
        cur = sha16(os.path.join(root, rel))
        if rel not in want:
            print("LANDED 未收录 %s（当前 %s）" % (rel, cur)); return 3
        if want[rel]["sha16"] != cur:
            print("LANDED 不符 %s：台账 %s / 当前 %s" % (rel, want[rel]["sha16"], cur)); return 3
    return 0


def selfevidence(rec):
    """三样：测的是谁 / 测的是哪一版 / 谁判的。缺一样，产物就是一句没有主语的话。"""
    have_subject = bool(rec.get(V.SELFEVIDENCE_KEYS[0]))
    have_version = bool(rec.get(V.SELFEVIDENCE_KEYS[1]))
    # 不变式式，不是存在性：存在性检查写下的那一刻就恒真，判别力随时间衰减到零
    have_verdict = bool(rec.get("instrument_hits")) == (rec.get("instrument") is not None)
    return {"subject": have_subject, "version": have_version, "verdict": have_verdict}


def identity_cross_check(rec):
    """纯静态自相矛盾核对：正文声明的身份首段 == 正文声明的被测文件。"""
    ident = (rec.get("harness_sha16") or "").split(":")[0]
    used = rec.get("fixture_file_used")
    if not ident or not used:
        return "missing"          # 注入产物：版本读不出来，形态 (T,F,T)，不算矛盾
    try:
        return "ok" if ident == V.sha16(used) else "contradiction"
    except OSError:
        return "missing"


def run_main(rec, out_path, logp, drive, fixture_file):
    """算 -> 写盘 -> 打印 -> 退出码（四段不可换）。异常被捕获，落盘照做。"""
    rec["asserts_ran"] = 0
    # 唯一写入点写事实（"夹具文件来自环境"）；类别字符串由读者派生，一个事实不写两遍。
    rec["fixture_from_env"] = bool(os.environ.get("M4C_FIXTURE_FILE"))
    try:
        rec["fixture_file_used"] = fixture_file          # 主语：这份产物测的是谁（写在 harness_id 之前，注入时才留得下）
        rec["harness_sha16_now"] = harness_id(fixture_file)   # 唯一一次现算，在带内
        rec["harness_sha16"] = rec["harness_sha16_now"]
        inv = V.def_inventory(globals(), os.path.abspath(__file__))
        rec["def_source_count"] = inv["top"]
        rec["nested_def_names"] = inv["nested"]
        rec["def_fp"] = inv["fps"]
        rec["def_mismatch_detail"] = V.def_mismatch_detail(inv, os.path.abspath(__file__))
        rec["def_mismatch"] = bool(rec["def_mismatch_detail"])
        rec["asserts_declared"] = asserts_declared(finalize)   # 读文件，自身出错置 None，不连累 drive
        rec["order_violations"] = V.check_order()
        drive(rec, logp)
        finalize(rec, logp, rec["covers_declared"])
    except Exception as exc:
        rec["finalize_error"] = "%s: %s" % (type(exc).__name__, exc)   # 类型给"是不是这个错"，str 给上下文
        rec.setdefault("is_red", None)
    finally:
        rec["finalized"] = rec.get("finalize_completed") is True   # 读戳，不读「没异常」
        rc = V.verdict(rec)          # 判定必须早于落盘，否则 instrument/hits 只活在已退出的进程里
        rec["selfevidence"] = selfevidence(rec)        # 元字段写在被描述字段之后
        rec["identity_cross_check"] = identity_cross_check(rec)
        json.dump(rec, open(out_path, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2, default=str)
    print("wrote", out_path)
    print(json.dumps({k: rec.get(k) for k in ("mode", "is_red", "expected_red", "exit",
          "assertions_status", "coverage_ok", "covers_observed", "die_kind", "finalized",
          "asserts_ran", "harness_sha16", "instrument", "instrument_hits",
          "finalize_error", "def_mismatch", "mode_unknown")}, ensure_ascii=False))
    return rc
