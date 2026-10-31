# -*- coding: utf-8 -*-
"""P3：从助手最终答案里抽“显式承诺/计划”（确定性正则，不含模型）。

只认第一人称 + 未来动作 + 交付对象/时间锚点；否定、敏感、用户事实一律不写。
"""

import re
import unicodedata

# 未来时间/承诺锚点
_TIME_ANCHOR = re.compile(
    r"明天|后天|大后天|下周|下下周|周[一二三四五六日天]|星期[一二三四五六日天]|"
    r"稍后|晚点|回头|到时候|一会儿|今晚|今天晚些|月底|下个月|\d{1,2}\s*点")
# 助手动作（承诺交付）
_ACTION = re.compile(
    r"提醒你|提醒您|提醒一下|告诉你|通知你|发给你|给你发|发你|帮你|替你|"
    r"给你准备|帮你查|帮你整理|帮你安排|给你带|给你留|和你确认|跟你确认|"
    r"再跟你说|来提醒")
# 第一人称主语（助手视角）
_SELF = re.compile(r"我")
_NEG = re.compile(r"不会|不用|不需要|不必|别|不要|没法|无法|不能|不提醒|不写|不做")
_SENSITIVE = re.compile(
    r"密码|口令|验证码|身份证|银行卡|卡号|secret|api[\s_-]?key|token\s*=|"
    r"(?<!\d)\d{16,19}(?!\d)|1[3-9]\d{9}")
_SENT_SPLIT = re.compile(r"(?<=[。！？!?；;])\s*|\n+")

MAX_COMMITMENTS = 2
MAX_CHARS = 120


def _clean(text):
    s = unicodedata.normalize("NFKC", str(text or ""))
    return re.sub(r"\s+", " ", s).strip()


def is_commitment(sentence):
    s = _clean(sentence)
    if not s or len(s) > 240:
        return False
    if _NEG.search(s) or _SENSITIVE.search(s):
        return False
    if not _SELF.search(s):
        return False
    if not _TIME_ANCHOR.search(s):
        return False
    return bool(_ACTION.search(s))


def extract_commitments(answer):
    """-> [{sentence, text}]；text 为“助手承诺：…”；最多 MAX_COMMITMENTS 条。"""
    out, seen = [], set()
    for raw in _SENT_SPLIT.split(_clean(answer)):
        s = raw.strip(" ，,；;。")
        if not s or not is_commitment(s):
            continue
        if len(s) > MAX_CHARS:
            s = s[:MAX_CHARS] + "…"
        key = re.sub(r"[\s，,。．.、:：;；!！?？]+", "", s)
        if key in seen:
            continue
        seen.add(key)
        out.append({"sentence": s, "text": "助手承诺：" + s})
        if len(out) >= MAX_COMMITMENTS:
            break
    return out


def is_sensitive(text):
    return bool(_SENSITIVE.search(str(text or "")))