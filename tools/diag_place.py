# -*- coding: utf-8 -*-
"""Isolate why a placed block is not readable.

modes:
  native   encode the block directly at its target position (no move at all)
  shifted  encode at 0, then seq_repos_local() it to the target position
  native2  two blocks, both encoded at their final targets
  shifted2 two blocks, both encoded at 0 and moved with seq_repos_local()

A correct block answers the profile question with A-4417 (and the project one
with 蓝鲸). If native works and shifted does not, the per-cell rotation is wrong.
If both fail, the placement / mask side is wrong.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kvslots import KVEngine

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

MODEL = r"D:\models\DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf"

PROFILE = ("我叫林知远，在供应链分析组工作，我的工号是 A-4417。"
           "我养的猫叫年糕，是一只橘猫。"
           "每周例会订在 B栋3层302会议室。")
PROJECT = ("我在做蓝鲸项目。蓝鲸项目定在 3月14日 上线。"
           "蓝鲸项目的负责人是周敏。")

CHAT = 4096
Q1 = "我的工号是多少？"
Q2 = "项目代号是什么？"


def run(mode):
    eng = KVEngine(MODEL, n_ctx=8192, n_seq=8, gpu=99, kv="q8_0")
    try:
        if mode in ("disk0", "disk1", "disk2", "disk1s", "disk1c", "disk1f"):
            BLK = r"D:\llama-mem\kvmem\blocks"
            if mode == "disk1f":
                # same as disk1 but with a flush decode after repos_local, to see
                # whether a pending K-shift left over from the load is the culprit
                eng.reset(1)
                eng.load(1, os.path.join(BLK, "profile.kvmem"))
                t1 = CHAT - eng.n_tokens(1)
                m = eng.repos_local(1, t1)
                eng.reset(7)
                eng.write(7, "。")
                eng.share(1, 0)
                print("      moved %d cells, block1 at %d, can_shift=%d"
                      % (m, t1, eng.can_shift()))
                a1 = eng.ask(0, Q1, n_predict=24, pos=CHAT)
                print("      q1 -> %s" % a1.strip().replace("\n", " "))
                return

            if mode == "disk1c":
                # round trip: +4046 then -4046, back to 0..49, ask at 50.
                # if this answers correctly the rotation is self-consistent on a
                # loaded block, i.e. the write lands in the cells it reads.
                eng.reset(1)
                eng.load(1, os.path.join(BLK, "profile.kvmem"))
                n1 = eng.n_tokens(1)
                t1 = CHAT - n1
                m1 = eng.repos_local(1, +t1)
                m2 = eng.repos_local(1, -t1)
                eng.share(1, 0)
                print("      moved %d/%d cells, back at %d..%d"
                      % (m1, m2, eng.pos_max(1) - n1 + 1, eng.pos_max(1)))
                a1 = eng.ask(0, Q1, n_predict=24, pos=n1)
                print("      q1 -> %s" % a1.strip().replace("\n", " "))
                return

            if mode == "disk1s":
                # same as disk1 but using the engine's own seq_add (whole-tensor shift)
                eng.reset(1)
                eng.load(1, os.path.join(BLK, "profile.kvmem"))
                t1 = CHAT - eng.n_tokens(1)
                eng.repos(1, t1)
                eng.reset(7)
                eng.write(7, "。")          # flush decode applies the pending shift
                eng.share(1, 0)
                print("      seq_add %+d, block1 at %d, pos_max %d"
                      % (t1, t1, eng.pos_max(1)))
                a1 = eng.ask(0, Q1, n_predict=24, pos=CHAT)
                a2 = eng.ask(0, Q2, n_predict=24)
                print("      q1 -> %s" % a1.strip().replace("\n", " "))
                print("      q2 -> %s" % a2.strip().replace("\n", " "))
                return

            if mode == "disk0":
                # no move at all: ask right after the block, wherever it loaded
                eng.reset(1)
                eng.load(1, os.path.join(BLK, "profile.kvmem"))
                n1 = eng.n_tokens(1)
                eng.share(1, 0)
                print("      loaded at 0..%d, NO move" % (n1 - 1))
                a1 = eng.ask(0, Q1, n_predict=24, pos=n1)
                a2 = eng.ask(0, Q2, n_predict=24)
                print("      q1 -> %s" % a1.strip().replace("\n", " "))
                print("      q2 -> %s" % a2.strip().replace("\n", " "))
                return

            if mode == "disk1":
                eng.reset(1)
                eng.load(1, os.path.join(BLK, "profile.kvmem"))
                t1 = CHAT - eng.n_tokens(1)
                moved = eng.repos_local(1, t1)
                eng.share(1, 0)
                print("      moved %d cells, block1 at %d" % (moved, t1))
                lo, hi = t1, CHAT
            else:
                eng.reset(1)
                eng.load(1, os.path.join(BLK, "profile.kvmem"))
                n1 = eng.n_tokens(1)
                t1 = CHAT - 29 - n1
                m1 = eng.repos_local(1, t1)

                eng.reset(2)
                eng.load(2, os.path.join(BLK, "project.kvmem"))
                n2 = eng.n_tokens(2)
                t2 = CHAT - n2
                m2 = eng.repos_local(2, t2)

                eng.share(1, 0)
                eng.share(2, 0)
                print("      moved %d + %d cells, block1 at %d, block2 at %d"
                      % (m1, m2, t1, t2))
                lo, hi = t1, CHAT

            a1 = eng.ask(0, Q1, n_predict=24, pos=CHAT)
            a2 = eng.ask(0, Q2, n_predict=24)
            print("      visible [%d, %d)  q1 -> %s" % (lo, hi, a1.strip().replace("\n", " ")))
            print("                        q2 -> %s" % a2.strip().replace("\n", " "))
            return

        if mode in ("native", "shifted"):
            n = None
            if mode == "native":
                eng.reset(1)
                eng.write_at(1, PROFILE, CHAT - 50)
            else:
                eng.reset(1)
                eng.write_at(1, PROFILE, 0)
                n = eng.n_tokens(1)
                moved = eng.repos_local(1, (CHAT - 50) - 0)
                print("      repos_local moved %d cells" % moved)
            eng.share(1, 0)
            lo, hi = eng.pos_max(0) - eng.n_tokens(1) + 1, eng.pos_max(0)
        else:
            # two blocks packed head to tail below CHAT
            eng.reset(1)
            eng.write_at(1, PROFILE, 0)
            n1 = eng.n_tokens(1)
            eng.reset(2)
            eng.write_at(2, PROJECT, 0)
            n2 = eng.n_tokens(2)

            t1 = CHAT - n2 - n1
            t2 = CHAT - n2

            moved1 = moved2 = 0
            if mode == "shifted2":
                moved1 = eng.repos_local(1, t1)
                moved2 = eng.repos_local(2, t2)
            else:
                eng.reset(1)
                eng.write_at(1, PROFILE, t1)
                eng.reset(2)
                eng.write_at(2, PROJECT, t2)
            print("      moved %d + %d cells, block1 at %d, block2 at %d"
                  % (moved1, moved2, t1, t2))

            eng.share(1, 0)
            eng.share(2, 0)
            lo, hi = t1, CHAT - 1

        a1 = eng.ask(0, Q1, n_predict=24, pos=CHAT)
        a2 = eng.ask(0, Q2, n_predict=24)
        print("      visible [%d, %d)  q1 -> %s" % (lo, hi, a1.strip().replace("\n", " ")))
        print("                        q2 -> %s" % a2.strip().replace("\n", " "))
    finally:
        eng.close()


modes = sys.argv[1:] or ["native", "shifted", "native2", "shifted2"]
for mode in modes:
    print("== %s" % mode)
    run(mode)
    print()