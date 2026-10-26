#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Structure validator for the M5-B2 out-of-sample fixture.

This is preparation only: zero GPU, zero model, zero judging.  It validates the
fixture shape requested by the Lead.  It deliberately does NOT decide whether a
scenario is semantically valid, whether q text is good, or what the expected
label should be; those are frozen in docs/_work/PREREG-M5-B.md by m6b-analyst.

Skeleton mode (default):
    expected = "TBD" is accepted, and empty source_text/text are accepted, so the
    shape can be checked before the prereg lands.

Strict mode:
    python -X utf8 validate_m5b_fixture.py --strict
    requires non-empty source_text/text and expected in {"support","abstain"}.

Exit code: 0 = valid, 1 = invalid.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT = os.path.join(HERE, "out", "M5B2-fixture.json")
KINDS = ("detail", "lure")
EXPECTED = ("support", "abstain")
PLACEHOLDER = "TBD"


def validate_fixture(path, allow_placeholder=True, require_each_scenario_two=True):
    errors = []
    warnings = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "path": path, "errors": ["cannot read JSON: %s: %s" % (type(e).__name__, e)],
                "warnings": [], "counts": {}}

    if not isinstance(data, dict):
        return {"ok": False, "path": path, "errors": ["top level must be an object"],
                "warnings": [], "counts": {}}
    if not isinstance(data.get("scenarios"), list):
        return {"ok": False, "path": path, "errors": ["scenarios must be a list"],
                "warnings": [], "counts": {}}

    scenarios = data["scenarios"]
    if len(scenarios) != 8:
        errors.append("scenarios must be exactly 8, got %d" % len(scenarios))

    scenario_ids = []
    qids = []
    kind_counts = {"detail": 0, "lure": 0}
    q_total = 0
    for si, s in enumerate(scenarios):
        where = "scenarios[%d]" % si
        if not isinstance(s, dict):
            errors.append(where + " must be an object")
            continue
        sid = s.get("id")
        if not isinstance(sid, str) or not sid.strip():
            errors.append(where + ".id must be a non-empty string")
        else:
            if sid in scenario_ids:
                errors.append("duplicate scenario id: " + sid)
            scenario_ids.append(sid)
        st = s.get("source_text")
        if not isinstance(st, str):
            errors.append(where + ".source_text must be a string")
        elif not st.strip() and not allow_placeholder:
            errors.append(where + ".source_text must be non-empty in strict mode")
        facts = s.get("facts")
        if not isinstance(facts, list):
            errors.append(where + ".facts must be a list")
        else:
            for fi, fact in enumerate(facts):
                if not isinstance(fact, str):
                    errors.append("%s.facts[%d] must be a string" % (where, fi))
        qs = s.get("questions")
        if not isinstance(qs, list):
            errors.append(where + ".questions must be a list")
            continue
        if len(qs) != 5:
            errors.append(where + " must have exactly 5 questions, got %d" % len(qs))
        for qi, q in enumerate(qs):
            qwhere = "%s.questions[%d]" % (where, qi)
            q_total += 1
            if not isinstance(q, dict):
                errors.append(qwhere + " must be an object")
                continue
            qid = q.get("qid")
            if not isinstance(qid, str) or not qid.strip():
                errors.append(qwhere + ".qid must be a non-empty string")
            else:
                if qid in qids:
                    errors.append("duplicate qid: " + qid)
                qids.append(qid)
            text = q.get("text")
            if not isinstance(text, str):
                errors.append(qwhere + ".text must be a string")
            elif not text.strip() and not allow_placeholder:
                errors.append(qwhere + ".text must be non-empty in strict mode")
            kind = q.get("kind")
            if kind not in KINDS:
                errors.append(qwhere + ".kind must be one of %s, got %r" % (list(KINDS), kind))
            else:
                kind_counts[kind] += 1
            if "expected" not in q:
                errors.append(qwhere + " missing expected")
            else:
                exp = q["expected"]
                if not isinstance(exp, str):
                    errors.append(qwhere + ".expected must be a string")
                elif exp in EXPECTED:
                    pass
                elif exp == PLACEHOLDER and allow_placeholder:
                    warnings.append(qwhere + ".expected is placeholder TBD")
                else:
                    errors.append(qwhere + ".expected must be one of %s, got %r" %
                                  (list(EXPECTED), exp))

    if q_total != 40:
        errors.append("questions must total exactly 40, got %d" % q_total)
    for k, want in (("detail", 24), ("lure", 16)):
        if kind_counts[k] != want:
            errors.append("kind %r must total exactly %d, got %d" % (k, want, kind_counts[k]))
    if len(scenario_ids) != 8:
        errors.append("unique scenario ids must total exactly 8, got %d" % len(scenario_ids))
    if len(qids) != 40:
        errors.append("unique qids must total exactly 40, got %d" % len(qids))

    return {
        "ok": not errors,
        "path": path,
        "errors": errors,
        "warnings": warnings[:20],
        "counts": {
            "scenarios": len(scenarios),
            "unique_scenarios": len(set(scenario_ids)),
            "questions": q_total,
            "unique_qids": len(set(qids)),
            "kind_detail": kind_counts["detail"],
            "kind_lure": kind_counts["lure"],
            "placeholder_expected": sum(1 for s in scenarios if isinstance(s, dict)
                                       for q in (s.get("questions") or [])
                                       if isinstance(q, dict) and q.get("expected") == PLACEHOLDER),
            "empty_source_text": sum(1 for s in scenarios if isinstance(s, dict)
                                     and not str(s.get("source_text") or "").strip()),
            "empty_question_text": sum(1 for s in scenarios if isinstance(s, dict)
                                       for q in (s.get("questions") or [])
                                       if isinstance(q, dict) and not str(q.get("text") or "").strip()),
        },
        "strict": not allow_placeholder,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixture", default=DEFAULT)
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()
    rep = validate_fixture(a.fixture, allow_placeholder=not a.strict)
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())