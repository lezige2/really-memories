# score_at probe — delivery report (2026-10-24)

Scope: add `kvshim_score_at` to the C shim, bind it in Python, and use it to decide whether
a mounted memory block is *used*. **The pre-registered positive/negative control fails**, so
the Δ / Δ' / Δ(A) table (task item 4) was NOT produced. Numbers and diagnosis below.

## 1) Neutral baselines

`make_blocks_filler21_G18.py` — text used verbatim, measured count must equal the target,
nothing padded. Written **without BOS** so the cell count IS the quoted 21 / 18 (with BOS the
same text is 22 / 19 cells and can no longer occupy home's [4075,4096) with home's delta).

| block | text | n_tokens | cells (load / scan) | add_bos | base | how | sha256 |
|---|---|---|---|---|---|---|---|
| `blk_filler21_nb.kvmem` | 小区门口的早餐店换了老板，豆浆还是两块钱一杯，油条涨了五毛。 | 21 | 21 / 21 | False | 0 | exact | `db3520ab3941705d319c942f416573921aaa427ab870a5b9234fbd2308507ad1` |
| `blk_g18_nb.kvmem` | 楼下快递柜的取件码每天都会更新，超过三天不取就要退回。 | 18 | 18 / 18 | False | 0 | exact | `e32667d98b3d9b40fc56b61e2308d677608ff42a0501aba02d470d11d337a42e` |

Both sit at base 0, the pristine `home.kvmem` base, so mounting `blk_filler21_nb` at
[4075,4096) needs delta 4075 — home's delta — and its span is home's span exactly.

BOS note: `P.measure()` counts BOS, so the brief's "21 tokens / 18 tokens" is the
*content-token* count (same convention as `evidence/t030/token_search.py`, which prints n-1).
First attempt with BOS produced 22 / 19 cells and was quarantined by a concurrent executor
(`blocks/quarantine/*.bad_bos`); those files are theirs to keep, my deliverables are the
`_nb` pair above.

## 2) Build (task item 5)

Only `tools/kvshim.cpp` and `tools/kvslots.py` were touched — `llama.cpp/` is untouched
(`git diff --stat -- llama.cpp` empty), so step 1 of the build recipe was not needed and step 2
was run:

    powershell -NoProfile -ExecutionPolicy Bypass -File D:\llama-mem\tools\build_tools.ps1 -Gpu -Dll -Only kvshim
    == building kvshim_vk.dll
       ok -> D:\llama-mem\tools\kvshim_vk.dll

    libllama.a mtime before 1792855433.698493
    libllama.a mtime after  1792855433.698493      (unchanged: no lib rebuild happened)
    dll sha256 648e724485b328e17728007f392ee4ad7f299dfb9c4ed8ae854511a9a3109e9c
    exports    kvshim_score_at, kvshim_piece, kvshim_ask_at, kvshim_ask_at_topk

Additive only: `kvshim_score_at` (per-token logprob / rank, teacher forced) plus
`kvshim_piece` (token id -> text piece; there was no export for this, and item 3 requires
printing the piece next to every id). Nothing existing was modified.

## 3) Acceptance

| # | item | result |
|---|---|---|
| 0 | positive/negative control ①/③ | **FAIL — metric invalid** (details below) |
| 1 | default off: iso_dup4 / home answer sha unchanged | **PASS** `7ec1430d972d949e5c1d306c6d838c06335bcdd1d1dac8bebde0dbb8a04622fd` (== reference), answer `你住在广陵路 12 号 2 单元 602。…` |
| 2 | determinism, same input twice | **PASS** tokens / logprob bits / ranks / sum / mean / last / pieces all identical (bitwise, `struct.pack("<f")`), both in-process (two calls) and across two separate engine processes (`selftest.json` vs `selftest_run2.json`: same 8 bit patterns, sum `-7.901542817942714` both times) |
| 3 | id + piece per token | **PASS** e.g. `18 '3' / 220 ' ' / 9754 '月' / 9754→'月' …`, joined `3 月 14 日上线` |
| 4 | cap bounds | **PASS** cap=3 -> rc=-3, n=3, first three logprobs identical to the full run; cap=0 -> -1; cap=-5 -> -1; null prompt -> -1; null answer -> -1; seq=99 -> -1; pos 8190 (past pool) -> -1; positions already busy -> -1; all out-pointers null -> 0 |
| 5 | build steps | **PASS** see §2 (step 2 only; libllama.a mtime unchanged; llama.cpp untouched) |

Self-test artifact: `evidence/score_at/selftest.json` (+ console table of id/piece/rank/logprob).

## 4) Gate: the positive/negative control does NOT separate ① from ③

Same 18-cell project block, same question `问：项目什么时候上线？答：`, baseline = the neutral
18-cell block (`blk_g18_nb`, same slot, same positions, same delta). Answer scored:
`3 月 14 日上线` (fact content of the block).

| case | geometry | S_sum block | S_mean block | S_sum neutral | S_mean neutral | **Δ_sum** | **Δ_mean** | generated |
|---|---|---|---|---|---|---|---|---|
| ① | block [4078,4095], q@4096 | −7.9015 | −0.9877 | −29.2728 | −3.6591 | **+21.371** | **+2.671** | `项目在3月14日上线。…` |
| ③ | block [4077,4094], q@4095 | −7.8105 | −0.9763 | −28.6104 | −3.5763 | **+20.800** | **+2.600** | `项目什么时候上线？…` (generation normal, memory not adopted) |

Δ(③)/Δ(①) = **0.973** on the mean (0.973 on the sum). On the brief's own scale that reads
"memory influence NOT weakened", for a configuration whose generation provably ignores the
memory. So the pre-registered rule (`≤0.1 ⇒ weakened`, `Δ ≈ 0` expected for ③) is violated
by a factor of ~26, and per task item 0 the metric is invalid: **the Δ table was not run.**

### Why it fails (two diagnostics, both saved)

* `diag_visibility.json` — block vs *no memory at all*: Δ_mean = +2.401 (①) / +2.443 (③).
  In ③ the block is read at least as strongly as in ①. ③ is not a visibility failure; the
  model reads the block and still does not answer from it.
* `diag_contrast.json` — a preference metric (`mean(fact continuation) − mean(question-echo
  continuation)`, then differenced against the neutral block): Δ_margin = +0.038 (①) /
  −0.068 (③). Same magnitude, no usable separation either.

Consequence: teacher-forced logprob of the fact string measures *influence of the block on the
logits*, not *adoption of the block's content in the answer*. ① and ③ differ in adoption only
(the greedy answer changes), and adoption is already exposed by the existing `fact_ok`
criterion, not by Δ.

## 5) Files

Code
  - `tools/kvshim.cpp` (`kvshim_score_at`, `kvshim_piece`; additive)
  - `tools/kvslots.py` (`KVEngine.score_at(...)`, `KVEngine.piece(...)`)
  - `kvmem/m2_visibility/make_blocks_filler21_G18.py`
  - `kvmem/m2_visibility/score_lib.py` (top-aligned geometry, 1 measurement = 1 reset+share)
  - `kvmem/m2_visibility/score_at_selftest.py` (acceptance 2/3/4)
  - `kvmem/m2_visibility/score_at_gate.py` (acceptance 0)
  - `kvmem/m2_visibility/score_at_diag_visibility.py`, `score_at_diag_contrast.py` (diagnostics)

Blocks
  - `kvmem/m2_visibility/blocks/blk_filler21_nb.kvmem`, `blocks/blk_g18_nb.kvmem`
  - `kvmem/m2_visibility/blocks_filler21_G18.json` (text / n_tokens / cells / sha / how)

Evidence
  - `kvmem/m2_visibility/evidence/score_at/selftest.json`, `selftest_run2.json` (second process)
  - `kvmem/m2_visibility/evidence/score_at/gate.json`
  - `kvmem/m2_visibility/evidence/score_at/diag_visibility.json`
  - `kvmem/m2_visibility/evidence/score_at/diag_contrast.json`
  - `kvmem/m2_visibility/evidence/score_at/reg_dup4_home.json` + `.log` (acceptance 1)

## 6) Deviations / environment notes

* Repo is on branch `main`; there is no `persistent-memory` branch in this clone.
* The llama.cpp build tree is `D:\llama-mem\build-vulkan` (not `llama.cpp/build-vulkan`);
  `libllama.a` lives there.
* A concurrent executor is writing in the same `kvmem/m2_visibility/blocks/` directory
  (it quarantined my first BOS-bearing pair and built its own `blk_filler_c21.kvmem` with the
  same no-BOS convention). My files use distinct `_nb` names and nothing of theirs was touched.
* `kvshim_score_at` requires the target positions to be free: on a sequence that already holds
  cells at `pos_start` the engine refuses the decode and the function returns -1 (recorded as
  the `positions_busy` guard). Every measurement here therefore resets the chat sequence and
  re-shares the blocks first.
* Pre-existing dirty files in the tree, not mine: `kvmem/m2_visibility/E10-NEXT2.md`,
  `patches/norm_pe.py`. No commit was made.
