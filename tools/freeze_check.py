# -*- coding: utf-8 -*-
"""freeze_check.py -- M2 guard: the retrieval layer must not change while M2 is in progress.

M2 moves blocks between slots. If block *selection* also changes, a failed run cannot be
attributed: you cannot tell "the wrong block was chosen" from "the right block was placed
wrongly". So the three selection files carry frozen digests, and every M2 measurement runs
this check first.

To change the selection layer on purpose, bump the digests here in the same commit that
changes the code, and say so in the report. Silently drifting past this check is the failure
mode this file exists to prevent.
"""
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

FROZEN = {
    "analysis.py": "49e91c7bd3dd32ef",
    "retrieval.py": "43f660196ab90a14",
    "evidence.py": "dccf7f010eaf9c7e",
}

# thresholds are part of the selection behaviour
FROZEN_THRESHOLDS = {"GATE": 1.30, "COV_MIN": 0.35, "REL_CUT": 0.55}
FROZEN_VERSIONS = {"INDEX_VERSION": 5, "ANALYSIS_VERSION": 4}


def digest(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]


def check(verbose=True):
    """Return (ok, problems). Does not raise, so callers can report and then decide."""
    problems = []
    for name, want in FROZEN.items():
        path = os.path.join(HERE, name)
        if not os.path.exists(path):
            problems.append("%s is missing" % name)
            continue
        got = digest(path)
        if got != want:
            problems.append("%s changed: %s -> %s" % (name, want, got))

    sys.path.insert(0, HERE)
    try:
        import retrieval as R
        import analysis as A
    except Exception as exc:                       # noqa: BLE001 - report, do not crash
        problems.append("cannot import the selection layer: %s" % exc)
    else:
        for key, want in FROZEN_THRESHOLDS.items():
            got = getattr(R, key, None)
            if got != want:
                problems.append("%s changed: %r -> %r" % (key, want, got))
        if getattr(R, "INDEX_VERSION", None) != FROZEN_VERSIONS["INDEX_VERSION"]:
            problems.append("INDEX_VERSION changed: %r -> %r"
                            % (FROZEN_VERSIONS["INDEX_VERSION"], R.INDEX_VERSION))
        if getattr(A, "ANALYSIS_VERSION", None) != FROZEN_VERSIONS["ANALYSIS_VERSION"]:
            problems.append("ANALYSIS_VERSION changed: %r -> %r"
                            % (FROZEN_VERSIONS["ANALYSIS_VERSION"], A.ANALYSIS_VERSION))

    if verbose:
        if problems:
            print("SELECTION LAYER: CHANGED (%d)" % len(problems))
            for p in problems:
                print("  - %s" % p)
            print("  M2 measurements are not attributable until this is resolved.")
        else:
            print("SELECTION LAYER: FROZEN (%d files, %d thresholds, versions %s)"
                  % (len(FROZEN), len(FROZEN_THRESHOLDS), FROZEN_VERSIONS))
    return (not problems), problems


if __name__ == "__main__":
    ok, _ = check()
    sys.exit(0 if ok else 1)