"""Assert the discipline numbering in SRC-CRITERIA.md agrees with DISCIPLINES.md.

Authority: mine/lead/DISCIPLINES.md. My criteria only ever cite it as #N.

Checks (each failure prints WHICH item and WHERE, never just False):
  1. every #N in my mapping table exists as a DISCIPLINES row;
  2. every DISCIPLINES row is cited by my table, or declared exempt WITH a reason;
  3. every discipline label used in prose has a table row;
  4. no label maps to two different numbers;
  5. exempt entries carry a non-empty reason and are not also mapped;
  6. source numbering is 1..N strictly increasing: gap / duplicate / misorder are
     reported SEPARATELY (different causes: missing row / colliding number / wrong slot);
  7. no two disciplines carry the same normalized topic text;
  8. set equality cited|LEAD_ONLY == source numbers, printing both difference sides;
  9. a label that LOOKS like a number but cannot be read is reported, never dropped.

UNCOVERED (printed on every run, for whoever reads the verdict rather than the code):
  1. duplicate topics are compared only after normalization; a paraphrase is not caught;
  2. only the section 12.30 mapping table is compared; #N cited elsewhere is out of scope;
  3. says nothing about whether each DISCIPLINES topic is correct or matches the code.
"""
import argparse, re, sys

DEFAULT_CRIT = "D:/llama-mem/kvmem/m2_visibility/mine/inspector/SRC-CRITERIA.md"
DEFAULT_DISC = "D:/llama-mem/kvmem/m2_visibility/mine/lead/DISCIPLINES.md"

LEAD_ONLY = {
    4: ("ledger item-to-criterion traceability; the M4/M5 acceptance ledgers live on the "
        "registry side and my criteria cite their resulting booleans, not this rule"),
}

DIGITS = "\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d"      # 一..九
TEN = "\u5341"
CN = DIGITS + TEN
NUMERAL = "(?:" + TEN + "[" + DIGITS + "]?|[" + DIGITS + "]" + TEN + "[" + DIGITS + "]?|[" + DIGITS + "])"
NUMERAL_ANY = "[" + CN + "\u5eff\u5345\u767e\u96f6\u3007\u58f9\u8d30\u53c1\u8086\u4f0d\u9646\u67d2\u634c\u7396\u4e24 0-9]{1,4}"
LABEL = re.compile("\u7eaa\u5f8b(" + NUMERAL + ")")
LABEL_ANY = re.compile("\u7eaa\u5f8b(" + NUMERAL_ANY + ")")


def cn2int(s):
    if s == TEN:
        return 10
    if s.startswith(TEN):
        return 10 + DIGITS.index(s[1]) + 1
    if s.endswith(TEN):
        return (DIGITS.index(s[0]) + 1) * 10
    if TEN in s:
        a, b = s.split(TEN)
        return (DIGITS.index(a) + 1) * 10 + DIGITS.index(b) + 1
    return DIGITS.index(s) + 1


def topic_norm(s):
    s = s.replace("**", "").replace(chr(96), "")
    s = re.sub(r"\s+", "", s)
    return s.strip("|\u3002.\uff1b;\uff0c,")


def parse_disc(path):
    rows = []
    for i, line in enumerate(open(path, encoding="utf-8").read().splitlines(), 1):
        m = re.match(r"^\| (\d+) \|", line)
        if not m:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        rows.append((i, int(m.group(1)), cells[1] if len(cells) > 1 else ""))
    return rows


def scan_labels(crit):
    """(used_numbers, unreadable_tokens). A numeral-looking token never disappears."""
    used, unparsed, covered = set(), [], set()
    for m in LABEL.finditer(crit):
        covered.add(m.start(1))
        used.add(cn2int(m.group(1)))
    for m in LABEL_ANY.finditer(crit):
        if m.start(1) in covered:
            continue
        tok = m.group(1).strip()
        line_no = crit.count(chr(10), 0, m.start()) + 1
        if tok.isdigit():
            used.add(int(tok))
        elif re.fullmatch(NUMERAL, tok):
            used.add(cn2int(tok))
        else:
            unparsed.append("%s@line%d" % (tok, line_no))
    return used, unparsed


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--crit", default=DEFAULT_CRIT)
    ap.add_argument("--disc", default=DEFAULT_DISC)
    a = ap.parse_args(argv)

    crit = open(a.crit, encoding="utf-8").read()
    drows = parse_disc(a.disc)
    nums = {n for _, n, _ in drows}

    sec = re.search(r"### 12\.30.*?(?=\n### |\Z)", crit, re.S)
    if not sec:
        print("FAIL: section 12.30 mapping table not found")
        return 1

    pairs = []
    for line in sec.group(0).split(chr(10)):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2 or not cells[1].startswith("#"):
            continue
        try:
            pairs.append((cells[0], int(re.match(r"#(\d+)", cells[1]).group(1))))
        except AttributeError:
            continue

    cited = {n for _, n in pairs}
    label_nums = {}
    for lbl, n in pairs:
        label_nums.setdefault(lbl, set()).add(n)
    dup_labels = sorted(l for l, v in label_nums.items() if len(v) > 1)

    used, unparsed = scan_labels(crit)
    labeled = {cn2int(l[2:]) for l in label_nums
               if l.startswith("\u7eaa\u5f8b") and re.fullmatch("\u7eaa\u5f8b" + NUMERAL, l)}

    missing_in_disc = sorted(n for n in cited if n not in nums)
    unhandled_new = sorted(nums - cited - set(LEAD_ONLY))
    no_reason = sorted(k for k, v in LEAD_ONLY.items() if not str(v).strip())
    # a prose label counts as mapped when its NUMBER is cited in the table (any label form),
    # or declared exempt; requiring the label text itself to be 纪律N would duplicate rule 4
    unmapped_labels = sorted(n for n in used if n not in cited and n not in LEAD_ONLY)
    exempt_mapped = sorted(set(LEAD_ONLY) & cited)

    seq = [(ln, n) for ln, n, _ in drows]
    order_offenders = [(ln, n, prev) for (ln, n), (_, prev) in zip(seq[1:], seq[:-1]) if n != prev + 1]
    top = max(nums) if nums else 0
    gaps = [n for n in range(1, top + 1) if n not in nums]
    all_nums = [n for _, n, _ in drows]
    dups_num = sorted({n for n in all_nums if all_nums.count(n) > 1})

    by_topic = {}
    for ln, n, topic in drows:
        t = topic_norm(topic)
        if t:
            by_topic.setdefault(t, []).append("%d@line%d" % (n, ln))
    dup_topics = {t[:30]: v for t, v in by_topic.items() if len(v) > 1}

    diff_left = sorted((cited | set(LEAD_ONLY)) - nums)
    diff_right = sorted(nums - cited - set(LEAD_ONLY))
    set_equal = not diff_left and not diff_right

    print("DISCIPLINES rows (%d) at %s" % (len(drows), a.disc))
    print("table rows (%d) citing (%d)" % (len(pairs), len(cited)))
    for k in sorted(LEAD_ONLY):
        print("exempt #%-2d reason: %s" % (k, LEAD_ONLY[k]))
    print()
    print("cited but absent in DISCIPLINES :", missing_in_disc or "none")
    print("DISCIPLINES rows unhandled      :", unhandled_new or "none")
    print("exempt without a reason         :", no_reason or "none")
    print("labels used but not in table    :", unmapped_labels or "none")
    print("labels mapped to 2+ numbers     :", dup_labels or "none")
    print("exempt numbers also mapped      :", exempt_mapped or "none")
    print("labels that failed to parse     :", unparsed or "none")
    print()
    print("source numbering 1..N strictly increasing :", "yes" if not (order_offenders or gaps or dups_num) else "NO")
    print("  out of order (line:number,previous)     :", order_offenders or "none")
    print("  missing numbers (gaps)                  :", gaps or "none")
    print("  duplicated numbers                      :", dups_num or "none")
    print("duplicate topic text (number@line)        :", dup_topics or "none")
    print("set equality cited|LEAD_ONLY == source    :", "yes" if set_equal else "NO")
    print("  only in my table (not in source)        :", diff_left or "none")
    print("  only in source (not in my table)        :", diff_right or "none")
    print()

    ok = not (missing_in_disc or unhandled_new or no_reason or unmapped_labels or dup_labels
              or exempt_mapped or unparsed or order_offenders or gaps or dups_num
              or dup_topics or not set_equal)
    print("UNCOVERED (by design -- read this, not the code):")
    print("  1. duplicate topics are compared only after normalization; a paraphrase is NOT caught")
    print("  2. only the section 12.30 mapping table is compared; #N cited elsewhere is out of scope")
    print("  3. says nothing about whether each DISCIPLINES topic is correct or matches the code")
    print()
    print("mapping_consistent =", ok)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
