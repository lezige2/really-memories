#!/usr/bin/env bash
# The whole evidence set under one DLL sha: G18 x2, pp18 x2, dup4 before/after.
set -u
HERE=/d/llama-mem/kvmem/m2_visibility/runs_g18
cd "$HERE" || exit 9
rm -f sha_log.txt
bash run_with_retry.sh iso_fac_G18 home  "$HERE/iso_fac_G18_home_r1.json"  "$HERE/all_g18_r1.log"  8
bash run_with_retry.sh iso_fac_G18 home  "$HERE/iso_fac_G18_home_r2.json"  "$HERE/all_g18_r2.log"  8
bash run_with_retry.sh iso_fac_pp18 home "$HERE/iso_fac_pp18_home_r1.json" "$HERE/all_pp18_r1.log" 8
bash run_with_retry.sh iso_fac_pp18 home "$HERE/iso_fac_pp18_home_r2.json" "$HERE/all_pp18_r2.log" 8
bash run_with_retry.sh iso_dup4 home     "$HERE/reg_dup4_home_before.json" "$HERE/all_dup4_b.log"  8
bash run_with_retry.sh iso_dup4 home     "$HERE/reg_dup4_home_after.json"  "$HERE/all_dup4_a.log"  8
echo ALLDONE >> "$HERE/sha_log.txt"
