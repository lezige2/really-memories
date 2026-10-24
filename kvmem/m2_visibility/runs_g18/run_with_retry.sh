#!/usr/bin/env bash
# Run the driver once, retrying when (a) the engine cannot open (a concurrent GPU user) or
# (b) tools/kvshim_vk.dll changed while the run was in flight (sha before != sha after).
# The DLL is rebuilt on this machine by other sessions, so a run only counts when the
# binary it loaded is the binary that was on disk on both sides of it.
set -u
LAYOUT="$1"; TARGET="$2"; OUTJSON="$3"; LOG="$4"; MAX="$5"
HERE=/d/llama-mem/kvmem/m2_visibility/runs_g18
cd /d/llama-mem/kvmem/m2_visibility/runs_iso2 || exit 9

dllsha() {
  python -X utf8 -c "import hashlib;print(hashlib.sha256(open(r'D:\llama-mem\tools\kvshim_vk.dll','rb').read()).hexdigest())"
}

for i in 1 2 3 4 5 6 7 8 9 10; do
  if [ "$i" -gt "$MAX" ]; then break; fi
  before=$(dllsha)
  echo "=== attempt $i $(date +%H:%M:%S) layout=$LAYOUT target=$TARGET dll_before=$before ===" >> "$LOG"
  python -X utf8 _driver2.py --layout "$LAYOUT" --target "$TARGET" --run-json "$OUTJSON" >> "$LOG" 2>&1
  rc=$?
  after=$(dllsha)
  echo "=== attempt $i rc=$rc dll_after=$after ===" >> "$LOG"
  echo "$LAYOUT $TARGET rc=$rc dll_before=$before dll_after=$after $(basename "$OUTJSON")" >> "$HERE/sha_log.txt"
  if [ "$before" != "$after" ]; then
    echo "--- dll changed under this run, discarding and retrying ---" >> "$LOG"
    rm -f "$OUTJSON"
    sleep 10
    continue
  fi
  if [ "$rc" = "0" ]; then exit 0; fi
  if grep -q "kvshim_open failed" "$LOG"; then
    echo "--- engine busy, sleeping 25s ---" >> "$LOG"
    sleep 25
  else
    exit "$rc"
  fi
done
exit 7
