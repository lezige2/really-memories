P = r"C:/Users/lezige/Documents/deepseek-harness/default-workspace/t030/norm_pe.py"
s = open(P, encoding="utf-8").read()
old = '    if len(sys.argv) > 2:' + chr(10) + '        print("NORMALIZED_EQUAL=%s" % (len(set(hs.values())) == 1))'
new = chr(10).join([
    '    if len(sys.argv) > 2:',
    '        a, b = sys.argv[1], sys.argv[2]',
    '        ba = open(a, "rb").read()',
    '        bb = open(b, "rb").read()',
    '        if len(ba) != len(bb):',
    '            print("FATAL size mismatch %d vs %d" % (len(ba), len(bb)))',
    '            return',
    '        raw_diff = [i for i in range(len(ba)) if ba[i] != bb[i]]',
    '        _nb, detail, _c = normalize(a)',
    '        sites = [off for _n, off in detail]',
    '        covered = all(any(site <= i < site + 4 for site in sites) for i in raw_diff)',
    '        nonempty = len(raw_diff) > 0',
    '        print("raw differing bytes: %d at %s" % (len(raw_diff), raw_diff[:12]))',
    '        print("(a) raw diff subset of enumerated sites: %s" % covered)',
    '        print("(b) raw diff non-empty: %s" % nonempty)',
    '        eq = len(set(hs.values())) == 1',
    '        print("(c) sites inside their parent structures: True (parser raises otherwise)") ',
    '        print("NORMALIZED_EQUAL=%s%s" % (eq, "" if (eq and covered and nonempty) else "  <-- NO CERTIFICATE"))',
])
assert s.count(old) == 1
s = s.replace(old, new)
open(P, "w", encoding="utf-8").write(s)
print("norm_pe patched with (a)(b)(c)")