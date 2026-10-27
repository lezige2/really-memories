#!/bin/bash
# 六臂 b09：命令逐字来自 lead 的 GO 消息；每臂一次，exit 不符即原停（不重跑）。
cd /d/llama-mem/kvmem/m4c_leases || exit 99
PY=/c/Users/lezige/.dsh/dsh-runtimes/dsh-next-primary-runtime/dependencies/python/python.exe
export M4C_BATCH_ID=b09 PYTHONUTF8=1 PYTHONIOENCODING=utf-8
LOG=tmp/sixarms-b09.log
: > "$LOG"
arm () {  # name expected_exit  (rest: command)
  local name=$1 want=$2; shift 2
  local st en rc
  st=$(date +%Y-%m-%dT%H:%M:%S)
  "$@" > "tmp/arm-$name.log" 2>&1
  rc=$?
  en=$(date +%Y-%m-%dT%H:%M:%S)
  echo "$name | start=$st | end=$en | exit=$rc | want=$want | cmd=$*" | tee -a "$LOG"
  if [ "$rc" != "$want" ]; then echo "STOP: $name exit=$rc want=$want" >> "$LOG"; return 10; fi
  return 0
}
export M4C_FIXTURE_FILE=
arm green    0 "$PY" run_site3.py green                b09-green          || exit 10
arm red      1 "$PY" run_site3.py red                  b09-red            || exit 10
export M4C_FIXTURE_FILE=no_such_fixture.py
arm inject   5 "$PY" run_site3.py green                b09-inject         || exit 10
export M4C_FIXTURE_FILE=
arm drop     0 "$PY" run_site3.py unmount-dropnonempty b09-drop           || exit 10
arm base     0 "$PY" redcheck_delete.py 1 base         b09-base           || exit 10
arm deleted  0 "$PY" redcheck_delete.py 1 deleted      b09-deleted        || exit 10
echo "ALL SIX DONE" | tee -a "$LOG"
