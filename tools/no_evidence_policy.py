# -*- coding: utf-8 -*-
"""无证据策略校验器（离线判定，不改产品路径）。

规则：question 含“微信”且 answer 含 11 位手机号（可带分隔符），而记忆里没有任何
“微信”事实 -> fail（不得把手机号当微信号；追问应是模型澄清，不是系统映射）。

KNOWN：无别名表、无向量检索；当前检索为 BM25/词法匹配。
"""

import re

_PHONE = re.compile(r"1[3-9]\d(?:[-\s]?\d){8}")


def _norm(s):
    return re.sub(r"[\s\-]", "", str(s or ""))


def has_wechat_fact(memories):
    for m in memories or []:
        text = m.get("text") if isinstance(m, dict) else str(m)
        if "微信" in str(text or ""):
            return True
    return False


def phone_in(text):
    return bool(_PHONE.search(str(text or "")))


_CLAIM_WECHAT = re.compile(r"你的微信号是|微信号是|微信号为")
_WECHAT_THEN_PHONE = re.compile(r"微信号[^。；;\n]{0,8}1[3-9]\d")
_QUALIFIER = re.compile(r"这是手机号|不是微信号|微信没说过|"
                        r"没告诉我微信号|只告诉过我手机号")
_PHONE_ANY = re.compile(r"1[3-9]\d(?:[-\s]?\d){8}")


def check(question, answer, memories):
    """-> {ok, reason}；允许“说明这是手机号”，禁止把手机号冒充微信号。"""
    q = str(question or "")
    a = str(answer or "")
    if "微信" not in q:
        return {"ok": True, "reason": "not_wechat_question"}
    if not phone_in(a):
        return {"ok": True, "reason": "no_phone_in_answer"}
    mem_phone = any(_PHONE_ANY.search(str(
        (m.get("text") if isinstance(m, dict) else m) or ""))
        for m in (memories or []))
    if not mem_phone:
        return {"ok": False, "reason": "phone_without_memory_evidence"}
    if _CLAIM_WECHAT.search(a) or _WECHAT_THEN_PHONE.search(a):
        return {"ok": False, "reason": "phone_claimed_as_wechat"}
    if _QUALIFIER.search(a):
        return {"ok": True, "reason": "phone_explained_not_wechat"}
    return {"ok": False, "reason": "phone_unexplained_for_wechat"}