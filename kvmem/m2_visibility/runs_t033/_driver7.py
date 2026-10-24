# -*- coding: utf-8 -*-
"""X1: the missing 2x2 cell — 57 cells with an exact project copy at slot 4.
Same code path as every other arm; only a layout is added in memory."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ISO2 = os.path.join(os.path.dirname(HERE), "runs_iso2")
sys.path.insert(0, ISO2)
import _driver2 as D2  # noqa: E402

D2.LAYOUTS["iso_x1_57copy"] = {"spacing": 64, "segs": [
    (1, "home", "home"), (2, "project", "project"), (4, "project2", "project")]}

if __name__ == "__main__":
    sys.argv = [sys.argv[0], "--layout", "iso_x1_57copy", "--target", "home"] + sys.argv[1:]
    D2.main()
