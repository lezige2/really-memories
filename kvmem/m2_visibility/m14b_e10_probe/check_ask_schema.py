"""ask 产物 schema 校验：缺必填字段即判不合格（不靠自觉）。"""
import json, os, sys

REQUIRED = ['ask_pos', 'ask_pos_source', 'raw_len', 'stripped_len',
            'n_tokens_before_ask', 'n_tokens_after_ask']


def check_ask(obj, where):
    miss = [k for k in REQUIRED if k not in obj]
    return {'where': where, 'ok': not miss, 'missing': miss}


def walk(node, where, out):
    if isinstance(node, dict):
        if 'answer' in node or 'ask_pos' in node:
            out.append(check_ask(node, where))
        for k, v in node.items():
            walk(v, where + '.' + k, out)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk(v, where + '[%d]' % i, out)


def main(paths):
    bad = 0
    for p in paths:
        out = []
        walk(json.load(open(p, encoding='utf-8')), os.path.basename(p), out)
        for r in out:
            if not r['ok']:
                bad += 1
                print('FAIL %-28s %s 缺 %s' % (r['where'][:28], '', ','.join(r['missing'])))
        print('%-32s asks=%d %s' % (os.path.basename(p), len(out),
                                    'OK' if all(x['ok'] for x in out) else 'HAS FAILURES'))
    return 0 if bad == 0 else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))