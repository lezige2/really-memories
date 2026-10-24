# -*- coding: utf-8 -*-
"""T-033 machine judge: norm / fact_ok / failure_form exactly as the task brief specifies.

Order is fixed and must not be swapped:
  0 fact_ok -> none
  1 empty after norm -> 空串
  2 norm(question) inside norm(answer) -> 复述提问
  3 ___ / ____ / 填空 / 选项 / ^[A-D][.、] -> 改写成模板
  4 不知道 / 无法 / 不能确定 / 没有相关信息 -> 拒答
  5 digits or address-like string while fact_ok == False -> 编造具体值
  6 otherwise -> 其他 (raw answer must be stored)
"""
import hashlib, json, os, re, sys

FACT = "广陵路12号2单元602"
WS = re.compile(r"[\s\u3000\u00a0\u200b\u200c\u200d\ufeff]+")
DIGIT = re.compile(r"[0-9０-９]")
ADDR = re.compile(r"(路|街|道|号|单元|室|楼|巷|村|区)")


def norm(s):
    return WS.sub("", s or "")


def fact_ok(ans):
    return FACT in norm(ans)


def failure_form(q, ans):
    n = norm(ans)
    if fact_ok(ans):
        return "none"
    if n == "":
        return "空串"
    if norm(q) and norm(q) in n:
        return "复述提问"
    if ("___" in n or "____" in n or "填空" in n or "选项" in n
            or re.search(r"(?m)^[A-D][.、]", ans or "")):
        return "改写成模板"
    if any(k in n for k in ("不知道", "无法", "不能确定", "没有相关信息")):
        return "拒答"
    if DIGIT.search(n) or ADDR.search(n):
        return "编造具体值"
    return "其他"


def judge(question, ans):
    return {"answer": ans, "answer_sha256": hashlib.sha256((ans or "").encode("utf-8")).hexdigest(),
            "norm_answer": norm(ans), "fact_ok": fact_ok(ans),
            "failure_form": failure_form(question, ans)}


def dig(obj, path):
    for k in path.split("/"):
        obj = obj[int(k)] if k.isdigit() else obj[k]
    return obj


if __name__ == "__main__":
    # self-check first: the procedure must reproduce E (True/none) and F (False/改写成模板)
    E = "kvmem/m2_visibility/evidence/t030/curve_E_r1.json"
    F = "kvmem/m2_visibility/runs_t032/t032_f_r1.json"
    q = "我住在哪？"
    e_ans = json.load(open(E, encoding="utf-8"))["answer"]
    f_ans = json.load(open(F, encoding="utf-8"))["answers"][0]["answer"]
    e, f = judge(q, e_ans), judge(q, f_ans)
    ok = (e["fact_ok"] is True and e["failure_form"] == "none"
          and f["fact_ok"] is False and f["failure_form"] == "改写成模板")
    print("SELFCHECK %s  E: fact_ok=%s form=%s | F: fact_ok=%s form=%s"
          % ("PASS" if ok else "FAIL", e["fact_ok"], e["failure_form"],
             f["fact_ok"], f["failure_form"]))
    if not ok:
        sys.exit("judge procedure does not reproduce E/F -- do not interpret any arm")
    for p in sys.argv[1:]:
        d = json.load(open(p, encoding="utf-8"))
        a = d["answers"][0]
        print("%-16s %s" % (os.path.basename(p), json.dumps(judge(a["question"], a["answer"]),
                                                            ensure_ascii=False)))
