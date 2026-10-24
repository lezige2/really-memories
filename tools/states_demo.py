# -*- coding: utf-8 -*-
"""states_demo.py -- the four evidence states, end to end, on one engine.

    1  general        -> no_evidence, generate, badge "no long-term memory"
    2  absent fact    -> no_evidence + memory_recall -> REFUSE, the model is not called
    3  in dialogue    -> chat_only, generate (refusing here would be wrong)
    4  in a block     -> memory_hit, mount and generate

Turn 3 needs the fact to be in the transcript, so the transcript is seeded with the user's
statement (as the app would: a statement is stored, not answered).
"""
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import chat as C                                          # noqa: E402
import evidence as E                                      # noqa: E402
import memory_source as ms                                # noqa: E402
import retrieval as R                                     # noqa: E402
from kvslots import KVEngine                              # noqa: E402

con = ms.connect(C.DB)
eng = KVEngine(C.MODEL, n_ctx=C.N_CTX, n_seq=8, gpu=99, kv="q8_0")
turns = [
    ("法国的首都是哪里？", None),
    ("我的车牌号是多少？", None),
    ("用户：我的车牌号是沪A-12345，记一下。", None),
    ("我的车牌号是多少？", None),
    ("我的工号是多少？", None),
]
mounted, order, history, first = {}, [], [], True
try:
    rows = {r[1]: r for r in ms.block_rows(con) if r[5] is not None}
    R.build_index(con, verbose=False)
    for q, _ in turns:
        statement = q.startswith("用户：")
        text = q[3:] if statement else q
        sel = [] if statement else C._selection(con, text)
        want = [s["name"] for s in sel]
        d = E.decide(text, sel, "\n".join(history))

        print("\n" + "=" * 74)
        print(("用户陈述：%s" if statement else "问：%s") % text)
        print("  状态：%s  [%s]  意图=%s" % (d["state"], E.BADGE[d["state"]], d["intent"]))
        print("  依据：%s" % d["reason"])

        if want != order:
            for name, (seq, lo, hi) in mounted.items():
                eng.drop(0, lo, hi)
                eng.reset(seq)
            mounted, order = {}, want
            for i, name in enumerate(order):
                seq = i + 1
                eng.reset(seq)
                nn = ms.load_into(eng, rows[name], seq)
                end = C.CHAT_START - i * C.SLOT
                lo = end - nn
                base = eng.pos_max(seq) + 1 - nn
                if base != lo and eng.repos_local(seq, lo - base) != nn:
                    raise SystemExit("%s: repos_local refused" % name)
                eng.share(seq, 0, lo, end)
                mounted[name] = (seq, lo, end)
        print("  挂载：%s" % (", ".join("%s[%d,%d)" % (k, v[1], v[2])
                                      for k, v in mounted.items()) or "（无）"))

        if statement:
            # A statement must land in the chat KV, otherwise "the fact is in this
            # dialogue" is only true in the app's transcript -- the model would be
            # answering from nothing. write_at decodes without generating.
            pos = C.CHAT_START if first else eng.pos_max(0) + 1
            eng.write_at(0, text, pos, add_bos=False)
            first = False
            history.append(q)
            continue
        if d["refuse"]:
            print("答：%s" % d["reply"])
            print("   （模型未调用；注入字符 %d；policy v%d）"
                  % (d["chars_injected"], d["policy_version"]))
            history.append("用户：%s\n助手：%s" % (text, d["reply"]))
            continue
        ans = eng.ask(0, text, n_predict=40, pos=C.CHAT_START if first else None)
        first = False
        print("答：%s" % C.clean(ans))
        history.append("用户：%s\n助手：%s" % (text, ans))
finally:
    eng.close()
    con.close()