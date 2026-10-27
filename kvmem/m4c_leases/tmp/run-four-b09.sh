#!/bin/bash
# 四臂 b09（inject/drop/base/deleted）：命令逐字来自 lead 的 GO；各一次，不重跑前两臂。
cd /d/llama-mem/kvmem/m4c_leases || exit 99
PY=/c/Users/lezige/.dsh/dsh-runtimes/dsh-next-primary-runtime/dependencies/python/python.exe
export M4C_BATCH_ID=b09 PYTHONUTF8=1 PYTHONIOENCODING=utf-8
LOG=tmp/fourarms-b09.log
: > "$LOG"
run () {
  local name=$1; shift
  echo "$name start $(date +%T)" >> "$LOG"
  "$@" > "tmp/arm-$name.log" 2>&1
  local rc=$?
  echo "$name end $(date +%T) exit=$rc cmd=$*" >> "$LOG"
}
export M4C_FIXTURE_FILE=no_such_fixture.py
run inject  "$PY" run_site3.py green                b09-inject
export M4C_FIXTURE_FILE=
run drop    "$PY" run_site3.py unmount-dropnonempty b09-drop
run base    "$PY" redcheck_delete.py 1 base         b09-base
run deleted "$PY" redcheck_delete.py 1 deleted      b09-deleted
echo "FOUR DONE" >> "$LOG"
