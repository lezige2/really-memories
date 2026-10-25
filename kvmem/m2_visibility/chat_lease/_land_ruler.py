# -*- coding: utf-8 -*-
"""task-34 P0 尺子统一：`LANDED-ruler.json`。

五个改动对象的 old→new sha16/bytes + 每条 before/after 实测输出（保存于
`tmp_db/ruler-before|after/`）+ `freeze_check` + `git status --porcelain` 前后对比。
只写台账，不 git add/commit。
"""
import hashlib
import json
import os
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(HERE, "out")
TMP = os.path.join(HERE, "tmp_db")
BEFORE = os.path.join(TMP, "ruler-before")
AFTER = os.path.join(TMP, "ruler-after")
LEDGER = os.path.join(HERE, "LANDED-ruler.json")

FILES = ("verify.sh", "patches/MANIFEST.txt", ".gitignore",
         "kvmem/m2_visibility/m4/check_ablate_run.py",
         "README.md", "PROJECT-STATE.md", "HANDOFF.md")


def sha16(p):
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:16]


def ent(p):
    return {"path": p, "sha16": sha16(os.path.join(ROOT, p)),
            "bytes": os.path.getsize(os.path.join(ROOT, p))}


def read(p):
    return open(p, encoding="utf-8", errors="replace").read()


def tail(p, n=3):
    return read(p).strip().splitlines()[-n:]


def main():
    old = {}
    for ln in read(os.path.join(BEFORE, "shas_before.txt")).splitlines():
        p, sh, b = ln.split()
        old[p] = {"sha16": sh, "bytes": int(b)}
    new = {p: ent(p) for p in FILES}
    changed = {p: {"old": old[p], "new": new[p]} for p in FILES
               if old.get(p, {}).get("sha16") != new[p]["sha16"]}
    git_before = [l for l in read(os.path.join(BEFORE, "gitstatus.out")).splitlines() if l.strip()]
    git_after = [l for l in read(os.path.join(AFTER, "gitstatus.out")).splitlines() if l.strip()]
    ledger = {
        "schema": "landed_ruler_v1",
        "task": "task-34 P0 尺子统一（verify.sh 关系断言 / MANIFEST 600 / .gitignore 放行 docs/_work / "
                "check_ablate 三态 / 三份 md as-of banner）",
        "at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "changed_files": changed,
        "unchanged_inputs": {
            "patches/persistent-memory.patch": ent("patches/persistent-memory.patch"),
            "patches/archive/persistent-memory-500-20261025.patch":
                ent("patches/archive/persistent-memory-500-20261025.patch"),
            "docs/_work/ANCHORS-CURRENT.md": ent("docs/_work/ANCHORS-CURRENT.md"),
        },
        "changes": [
            {
                "item": "1 verify.sh 写死 500 → 关系断言",
                "what": "四条关系断言替代字面量断言：live == MANIFEST 声明；补丁快照 == live；"
                        "归档 == MANIFEST 归档声明；归档 != live（500 版只作历史基线单列）",
                "before": {"rc": 1, "tail": tail(os.path.join(BEFORE, "verify.out")),
                            "failing": "写死 500：引擎补丁 = 600/0，期望 500/0 ⇒ 1/9 FAIL"},
                "after": {"rc": 0, "tail": tail(os.path.join(AFTER, "verify.out")),
                          "head": read(os.path.join(AFTER, "verify.out")).splitlines()[:4]},
                "run_cmd": "bash verify.sh",
            },
            {
                "item": "2 patches/MANIFEST.txt 600 + hunk 清单 + archive 基线 + 100 行归属",
                "what": "PATCH MANIFEST: sha256=db32faae…/32,337 B/insertions 600/0；12 hunk /6 文件清单；"
                        "archive 段 f41cbfbd/26,577 B/500（archive-insertions: 500）。"
                        "100 行 = [MASKBIAS](t031 ins1+27/ins2+20≈49)+汇总 7+[MASKDBG-WIN](win_add 44)；"
                        "来源可判，只剩冻结期授权是程序问题，照实写。",
                "before_sha16": "f35f8232a058a31c", "before_bytes": 6293,
                "after": new["patches/MANIFEST.txt"],
            },
            {
                "item": "3 .gitignore 放行 docs/_work/**（最小影响面）",
                "what": "`_*/ ` 行改为 `_*/` + `!docs/_work/` + `!docs/_work/**`。"
                        "实测：尾空格只是字面噪音（git 解析时剥掉），真正匹配 docs/_work 的是 `_*/` 通配；"
                        "故用两条负向例外放行，其余 `_*` 目录仍被忽略。",
                "before": {"check_ignore": read(os.path.join(BEFORE, "checkignore.out")).strip(),
                           "docs_work_tracked": False,
                           "status_lines": len(git_before)},
                "after": {"check_ignore_negation": read(os.path.join(AFTER, "checkignore.out")).strip(),
                          "docs_work_untracked": "38 文件 / 1,111,933 B（含 CONSOLIDATION-LEDGER.md 557,487 B；"
                                                 "无模型/无大二进制）",
                          "status_lines": len(git_after),
                          "git_add_commit": "未执行（提交留给人）"},
                "must_stay_ignored": {"kvmem/chat.db": True, "kvmem/m2_v1_14b/home.kvmem": True,
                                      "tools/kvshim_vk.dll": True},
                "released": {"docs/_work/**": True, "PROGRESS-AND-ROADMAP.md": True},
            },
            {
                "item": "4 check_ablate_run.py 去 np_==24 → 读声明值 + 三态",
                "what": "声明值取产物自身（top-level n_predict，否则 engine.n_predict）；"
                        "一致=PASS，值不一致=FAIL，未声明/一致性为 null=UNVERIFIED。字面量 24/64 都不进判据。",
                "before": {"rc": 1, "tail": tail(os.path.join(BEFORE, "check_ablate.out"))},
                "after": {"rc": 0, "tail": tail(os.path.join(AFTER, "check_ablate.out"))},
                "run_cmd": "python -X utf8 -u kvmem/m2_visibility/m4/check_ablate_run.py "
                           "kvmem/m2_visibility/m4/run_m4_ablate_plate_a7.json",
            },
            {
                "item": "5 三份 md as-of banner（只加头，不改正文结论）",
                "what": "README/PROJECT-STATE/HANDOFF 顶部 banner：as-of + 现行入口指针 + 哈希是签署坐标；"
                        "README 正文“仓库内 md 只有三份”就地改为“见 §0.1（20:20 回填 80 份）”。",
                "banner_anchor": {
                    "v1_had_sha": "a54c81092cf585a8",
                    "v2_rule": "banner 不钉 sha：指针只指向 docs/_work/ANCHORS-CURRENT.md 文件本身，"
                               "坐标以该文件内容为准（lead 裁：锚每改一次 banner 就腐烂一次）",
                    "why_revised": "v1 钉的 a54c8109 在 inspector 更新到 d2e0f181 后立刻过期；"
                                   "故去硬 sha，保留 as-of 日期",
                },
                "old_new": {p: changed[p] for p in ("README.md", "PROJECT-STATE.md", "HANDOFF.md")},
            },
        ],
        "git_status": {
            "before_lines": len(git_before), "after_lines": len(git_after),
            "new_entries": [l for l in git_after if l not in git_before],
            "note": "新增/变更 = 5 个被改文件 + 1 条 `?? docs/_work/`（目录折叠）；无 kvmem/模型/DLL 进入可跟踪面",
        },
        "freeze_check": {"status": "FROZEN",
                         "detail": "SELECTION LAYER: FROZEN (3 files, 3 thresholds, "
                                   "versions {'INDEX_VERSION': 5, 'ANALYSIS_VERSION': 4})"},
        "evidence_dir": os.path.relpath(TMP, ROOT).replace("\\", "/") + "/ruler-before|after",
        "four_state": {
            "verify.sh 关系断言": "通过（ALL PASS 12/12；含归档 != 实时）",
            "MANIFEST 600": "通过（db32faae/32,337 B/600；12 hunk/6 文件清单；archive 500 单列；归属已写）",
            ".gitignore 放行": "通过（docs/_work/** 可跟踪；模型/.kvmem/DLL 仍忽略；未 add/commit）",
            "check_ablate 三态": "通过（a7: PASS 0 failed/1 unverified, rc=0；未声明值不改产物）",
            "三份 md banner": "通过（只加头；README 正文那句已改为 §0.1 指针）",
        },
        "gaps": {
            "anchors_current_rows": "ANCHORS-CURRENT 的 #8(MANIFEST)/#10(PROJECT-STATE)/#11(HANDOFF)/#9(README) "
                                    "行需 inspector 按本轮新坐标更新（本单不改 docs/_work）："
                                    "MANIFEST=" + new["patches/MANIFEST.txt"]["sha16"] + "/"
                                    + str(new["patches/MANIFEST.txt"]["bytes"]) + " B、"
                                    "PROJECT-STATE=" + new["PROJECT-STATE.md"]["sha16"] + "/"
                                    + str(new["PROJECT-STATE.md"]["bytes"]) + " B、"
                                    "HANDOFF=" + new["HANDOFF.md"]["sha16"] + "/"
                                    + str(new["HANDOFF.md"]["bytes"]) + " B、"
                                    "README=" + new["README.md"]["sha16"] + "/"
                                    + str(new["README.md"]["bytes"]) + " B、"
                                    "verify.sh=" + new["verify.sh"]["sha16"] + "/"
                                    + str(new["verify.sh"]["bytes"]) + " B、"
                                    "check_ablate=" + new["kvmem/m2_visibility/m4/check_ablate_run.py"]["sha16"] + "/"
                                    + str(new["kvmem/m2_visibility/m4/check_ablate_run.py"]["bytes"]) + " B、"
                                    ".gitignore=" + new[".gitignore"]["sha16"] + "/"
                                    + str(new[".gitignore"]["bytes"]) + " B",
            "manifest_hunk_count": "lead 口径写“5 个 hunk”，实测 12 hunk /6 文件（llama-kv-cache.cpp 4 hunk）；"
                                   "本单按实测写，未按口径改数",
            "banner_revision": "banner v2（lead 2026-10-25T22:5x 裁）：去硬 sha、只留文件指针；"
                               "v1 的 a54c8109 已被 ANCHORS-CURRENT d2e0f181 超越，故不再钉值",
        },
        "no_self_sha": True,
    }
    with open(LEDGER, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(ledger, fh, ensure_ascii=False, indent=1)
    print("ledger: %s (%d B, sha16=%s)" % (LEDGER, os.path.getsize(LEDGER), sha16(LEDGER)))
    print("changed:", {p: (v["old"]["sha16"], v["new"]["sha16"]) for p, v in changed.items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())