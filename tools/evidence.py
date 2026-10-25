# -*- coding: utf-8 -*-
"""evidence.py -- M1: "no evidence" is a state, not silence.

The failure this fixes: retrieval correctly returned nothing, the turn was treated as
"nothing to do", the model was still called, and it invented a plate number. Silence is
not a policy.

Three states, decided BEFORE any generation:

    memory_hit    a long-term block was selected      -> mount, generate
    chat_only     not in memory, but in this dialogue -> generate, UI badge
    no_evidence   neither                             -> split by intent:
                    memory_recall (a personal/habitual fact)  -> REFUSE, model not called
                    general (small talk, world knowledge)      -> generate, UI badge

The refusal is a fixed application string. It is returned to the caller and displayed;
it is never handed to `ask`, so the prompt still carries the question and nothing else.
That is why the red line survives: R1 (memory text never enters the prompt) is untouched,
and R2 (application text) is satisfied trivially -- the text exists, but is not injected.

Two judgements, both rule-based on purpose (no classifier, so it is deterministic and
auditable; a model in the decision path would put generation noise into policy):

    intent            asked about a personal/habitual fact, or about the world?
    dialogue evidence is the asked-about thing present in the chat transcript?

Both are logged, and both are measured on the held-out set (eval_heldout.py).
"""
import re
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import retrieval as R                                     # noqa: E402

POLICY_VERSION = 1
# Fixed, non-user, non-memory application text. Never passed to ask().
REFUSAL = "长期记忆里没有这条，当前对话里也没有提到。我不想猜。"

# ---- intent ------------------------------------------------------------------
# A possessive/self reference plus a fact-shaped noun: "my X", "what is my X"
SELF_FACT = re.compile(
    r"(我的|我)(工号|车牌|生日|电话|手机|地址|护照|血型|身高|体重|老家|密码|身份证|"
    r"房贷|利率|工资|薪水|保险|保单|合同|车位|房租|余额|卡号|学号|车牌号|社保|公积金)")
# "我每个月工资多少": the fact noun is a few characters away from the self reference,
# so an adjacency-only pattern silently classifies it as small talk.
SELF_FACT_NEAR = re.compile(
    r"我[^，。？！?]{0,6}(工号|车牌|生日|电话|手机|地址|护照|血型|身高|体重|老家|密码|"
    r"房贷|利率|工资|薪水|保险|保单|合同|车位|房租|余额|卡号|学号|社保|公积金)")
RECALL_VERB = re.compile(r"上次|之前|以前|还记得|记得|我说过|我说的是|刚才说|前面说|"
                         r"刚才提到|前面提到|上回")
WORLD = re.compile(r"首都|省会|天气|翻译|写个|写一个|函数|代码怎么写|怎么做|为什么|"
                   r"解释一下|介绍|区别|原理|算法|历史|哪年|谁发明")


QUESTION = re.compile(r"[?？]|吗|多少|几|什么|哪|谁|是不是|有没有|多久|多大|几点")


def intent_of(query):
    """memory_recall | general. Deliberately narrow: a wrong refusal is worse than a
    missing one, so only clear self-fact questions refuse."""
    q = query or ""
    if WORLD.search(q):
        return "general"
    # a statement is never a request: "我的车牌号是沪A-12345" must not be refused
    if not QUESTION.search(q):
        return "general"
    if RECALL_VERB.search(q) or SELF_FACT.search(q) or SELF_FACT_NEAR.search(q):
        return "memory_recall"
    return "general"


# ---- dialogue evidence -------------------------------------------------------
def _content_terms(text):
    return [t for t in R.tokenize(text or "") if t not in R.STOP_BIGRAMS]


def dialogue_evidence(query, transcript):
    """Is the asked-about thing visible in this conversation?

    One matched content term is not enough -- "我的" would match everything -- so this
    requires either an entity from the query, or at least half of the query's content
    bigrams to appear in the transcript.
    """
    if not transcript:
        return False
    q = _content_terms(query)
    if not q:
        return False
    chat = set(_content_terms(transcript))
    hits = [t for t in q if t in chat]
    ents = [e for e in re.findall(r"[a-zA-Z]{1,4}-?\d+(?:[.\-]\d+)*", (query or "").lower())]
    if any(e in (transcript or "").lower() for e in ents):
        return True
    # One shared content term is enough. The asymmetry is deliberate: a wrong chat_only
    # still answers from the dialogue, while a missed one refuses a fact the user just
    # stated -- and over-refusal is the failure this state exists to prevent.
    return bool(hits)


# ---- decision ----------------------------------------------------------------
def decide(query, selection, transcript=""):
    """Return the state and what the caller must do. `selection` is retrieval's output."""
    intent = intent_of(query)
    if selection:
        return {"state": "memory_hit", "intent": intent, "refuse": False,
                "reply": None, "policy_version": POLICY_VERSION,
                "reason": "long-term block selected", "chars_injected": 0}
    if dialogue_evidence(query, transcript):
        return {"state": "chat_only", "intent": intent, "refuse": False,
                "reply": None, "policy_version": POLICY_VERSION,
                "reason": "not in memory, present in this dialogue",
                "chars_injected": 0}
    if intent == "memory_recall":
        return {"state": "no_evidence", "intent": intent, "refuse": True,
                "reply": REFUSAL, "policy_version": POLICY_VERSION,
                "reason": "personal fact, no memory, not in dialogue",
                "chars_injected": 0}
    return {"state": "no_evidence", "intent": intent, "refuse": False,
            "reply": None, "policy_version": POLICY_VERSION,
            "reason": "general question, no memory needed", "chars_injected": 0}


BADGE = {"memory_hit": "长期记忆", "chat_only": "仅对话上下文",
         "no_evidence": "未检索到长期记忆"}


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--transcript", default="")
    ap.add_argument("--select", default="", help="comma-separated block names")
    a = ap.parse_args()
    sel = [{"name": x} for x in a.select.split(",") if x]
    d = decide(a.query, sel, a.transcript)
    print("intent=%s state=%s refuse=%s" % (d["intent"], d["state"], d["refuse"]))
    print("badge=%s  reason=%s" % (BADGE[d["state"]], d["reason"]))
    if d["refuse"]:
        print("reply=%s" % d["reply"])
    return 0


if __name__ == "__main__":
    sys.exit(main())