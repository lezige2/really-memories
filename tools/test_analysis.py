# -*- coding: utf-8 -*-
"""test_analysis.py -- table-driven tests for the value table, before it is frozen.

Every row here is a claim the table makes. The negative rows matter more than the positive
ones: a value table that over-claims is not a small bug, it is a gate that rejects the
right block or admits a wrong one, and both look like "retrieval is flaky".

    python tools/test_analysis.py [-v]
"""
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import analysis as A                                      # noqa: E402

# (query, expected answer_type or None)
ASKS_CASES = [
    # the four defects found in review, each as a pair so the pair cannot drift apart
    ("我什么时候上班", "time_of_day"),
    ("几点上班", "time_of_day"),
    ("什么时候下班", "time_of_day"),
    ("项目上线了吗", None),              # status question, not a date question
    ("什么时候上线", "date"),
    ("Q4 的交付日期是什么", "date"),
    ("我的生日是什么时候", "date"),      # regression from the previous table
    ("生日是哪天", "date"),
    ("生日几号", "date"),
    # money -- the noun+多少 form is the one that used to slip through
    ("我工资是多少", "money"),
    ("我的月薪是多少", "money"),
    ("房租多少", "money"),
    ("房贷每月还多少", "money"),
    ("报销花了多少", "money"),
    ("这个多少钱", "money"),
    ("奖金多少", "money"),
    # not money
    ("我的车牌号是多少", None),          # an identifier, not an amount
    ("我工资卡是哪家银行", None),        # asks a bank, not an amount
    # time_of_day
    ("我几点睡觉", "time_of_day"),
    ("几点开会", "time_of_day"),
    # duration
    ("通勤多久", "duration"),
    ("要几个小时", "duration"),
    # date
    ("什么时候上线", "date"),
    ("我几号发工资", "date"),
    ("合同哪天到期", "date"),
    # count
    ("组里有几个人", "count"),
    ("一本书几页", "count"),
    # location / name (ranking only, never gated)
    ("我下周去哪出差", "location"),
    ("我住哪", "location"),
    ("项目负责人是谁", "name"),
]

# (text, kinds that MUST be present)
VALUES_POSITIVE = [
    ("每月 15号 发工资", {"date", "count"}),
    ("3月14日 上线", {"date"}),
    ("3月14 上线", {"date"}),                    # no 日
    ("下个月 去西安", {"date"}),
    ("月底 之前交", {"date"}),
    ("坐 2号线 到公司", {"count"}),                # a metro line is NOT a date
    ("房租 4800元", {"money"}),
    ("工资 五千元", {"money"}),                   # Chinese numeral WITH a unit
    ("年终奖 一万二元", {"money"}),
    ("12点半 睡", {"time_of_day"}),
    ("早上 7点 起床", {"time_of_day"}),
    ("全程 55分钟", {"duration"}),
    ("组里 9个人", {"count"}),
    ("例会订在 B栋3层302会议室", {"count", "location"}),
    ("我住西郊的梅园新村", {"location"}),
    ("去 上海 出差", {"location"}),
    ("猫叫 团子", {"name"}),
    # month alone, and a Chinese date with no 日/号
    ("三月十四 上线", {"date"}),
    ("3月14 上线", {"date"}),
    ("3月 上线", {"date"}),
    ("工资 1万。", {"money"}),
    ("早上9点上班", {"time_of_day"}),
]

# (text, kinds that must NOT be present) -- the false positives that would poison a gate
VALUES_NEGATIVE = [
    ("我在做蓝鲸项目", {"location"}),                  # a project is not a place
    ("我在供应链分析组工作", {"location"}),            # an org is not a place
    ("每月 15号 发工资", {"money"}),                   # a payday is not an amount
    ("工资卡是 招商银行", {"money"}),                  # a card is not an amount
    ("发工资", {"money"}),
    ("每天 一万步", {"money"}),                        # Chinese numeral without a unit
    ("每月 15号 发工资，共 5000元", set()),            # sanity: this one IS money (checked below)
    ("坐 2号线 到公司", {"date"}),                     # a metro line is not a date
    # the arabic 万 trap: my own "一万步" test passed while "1万步" was still money
    ("每天走1万步", {"money"}),
    ("1万公里", {"money"}),
    ("1万人", {"money"}),
    ("1万次", {"money"}),
    ("3个月 之后上线", {"date"}),                      # 个月 is a duration, not a date
    ("我有一点累", {"time_of_day"}),                   # "一点" is not 1 o'clock
]

# near-miss pairs: (query, block, does the gate admit the block?)
NEAR_MISS = [
    ("我工资是多少", "工资卡是 招商银行", False),       # asks amount, block has a card
    ("我工资是多少", "每月 15号 发工资", False),        # asks amount, block has a payday
    ("我几号发工资", "每月 15号 发工资", True),         # asks date, block HAS it
    ("我工资是多少", "每月 15号 发工资，共 5000元", True),
    # no answer type means no gate at all: this one is left to bm25 + coverage
    ("我的车牌号是多少", "车停在 B2层 217号", True),
]

FAIL = []


def check(cond, label):
    if not cond:
        FAIL.append(label)


def main(argv):
    verbose = "-v" in argv
    n = 0

    for q, want in ASKS_CASES:
        got = A.answer_type(q)
        n += 1
        check(got == want, "answer_type(%r) = %r, want %r" % (q, got, want))

    for text, must in VALUES_POSITIVE:
        kinds = A.value_kinds(text)
        n += 1
        missing = must - kinds
        check(not missing, "value_kinds(%r) = %s, missing %s" % (text, sorted(kinds),
                                                                sorted(missing)))
        if verbose:
            print("  + %-28s %s" % (text, sorted(kinds)))

    for text, must_not in VALUES_NEGATIVE:
        kinds = A.value_kinds(text)
        n += 1
        bad = must_not & kinds
        check(not bad, "value_kinds(%r) = %s, must NOT contain %s" % (text, sorted(kinds),
                                                                     sorted(bad)))

    # the multi-value sanity row: a block with an amount must be money
    n += 1
    check("money" in A.value_kinds("每月 15号 发工资，共 5000元"),
          "a block with 5000元 must supply money")

    for q, block, expect in NEAR_MISS:
        want = A.answer_type(q)
        kinds = A.value_kinds(block)
        n += 1
        if want in A.GATED:
            passes = want in kinds
        else:
            passes = True          # no gate applies; location/name only reorder
        check(passes == expect, "near-miss %r vs %r: gate %s, expected %s (kind=%s)"
              % (q, block, "passes" if passes else "rejects",
                 "passes" if expect else "rejects", want))

    # normalization spot checks
    for raw, want in [("十二点半", "12点半"), ("１２点", "12点"), ("3月14日", "3月14日")]:
        n += 1
        check(A.normalize(raw) == want, "normalize(%r) = %r, want %r"
              % (raw, A.normalize(raw), want))

    # the documented limitation, asserted so a future change cannot pass silently
    multi = A.answer_type("什么时候发工资，多少钱")
    n += 1
    check(multi in ("money", "date"), "multi-intent returns one kind (%r)" % multi)
    print("\nknown limitation: 什么时候发工资，多少钱 -> %r (first match wins)" % multi)
    # recorded, not fixed: colloquial amounts. "1.5万" is money, "1万5" is not; same family
    # as the already-recorded "一万二". A miss here is a real measurement, not a tuning hint.
    for t in ("1万5", "一万二"):
        print("known limitation: value_kinds(%r) = %s" % (t, sorted(A.value_kinds(t))))
    # recorded, not fixed: location is a substring lookup, so names that contain a city are
    # tagged. Harmless while location is not gated; must become word-boundary aware if it
    # ever is.
    for t in ("大理石 台面", "孙中山 是 谁"):
        print("known limitation: value_kinds(%r) = %s" % (t, sorted(A.value_kinds(t))))

    print("%d/%d checks passed" % (n - len(FAIL), n))
    for f in FAIL:
        print("  FAIL %s" % f)
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))