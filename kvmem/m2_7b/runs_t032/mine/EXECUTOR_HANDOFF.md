# T-032 executor hand-off (written at the stop order; no engine run, no rebuild)

## State at stop
- Rebuild: NOT performed by me. Two-step rebuild was prepared and the spin-wait loop ran
  (poll 1..10); busy_python reached COUNT=0 at poll 10.
- The write-open lock test then failed with **FileNotFoundError** on
  `D:/llama-mem/build-vulkan/bin/kvshim_vk.dll` - that path does not exist, so the test
  answered the wrong question (path wrong, not lock). My script treated it as "locked" and
  stopped before rebuilding. Net effect: no rebuild happened, which matches the stop order.
- The DLL is yours from here. I did not touch `llama.cpp/` or `tools/kvshim_vk.dll` in this stage.

## Runs I produced, with the binary each one used
| artifact | layout/target | DLL sha256 (recorded in the json) | answer sha256 |
|---|---|---|---|
| t030/E_reg_nobias.json | (not produced - stopped before) | - | - |
| t030/E_reg_b0.json | (not produced - stopped before) | - | - |
| runs_mask/t030_E_rc.json | iso_dup4 / home | 648e724485b328e1... (FULL) | 7ec1430d972d949e |

Binary map as corrected by inspector (do not mix these up):
- c7ea09bbc7cb : t031_e/f, t032_f, t032_h1_r1/r2, t032_h2_r1/r2, t032_pp18only
- 648e724485b3 : t032_hp12_r1/r2, runs_t033/h1_r1/r2, t030_E_rc

## Facts I established this session (each with its own instrument)
1. Block provenance is machine-checkable at load time, but the engine refusal text is a
   catch-all: a MISSING file was reported as "incompatible state (model, rope, kv type or
   n_rot_k differs)". Never read that text as a field-level diagnosis.
2. `cells` is not a token-identity check. Existing blocks (home/project/habit/car/pp18/pet)
   all start with BOS id 151646; my two filler blocks were built without BOS, so "21 cells"
   meant 20 content tokens for the family and 21 for mine. Only a token-sequence comparison
   catches this; I added `kvshim_tokenize` / `kvshim_seq_tokens` for exactly that.
3. `kvshim_ask_at` and `kvshim_ask_at_topk` return the same rc and the same answer on the
   same geometry, so the top-k export is additive.
4. Where the block sits decides whether the engine can use it: ask position must equal
   tail+1 (gap 0). gap>=1 or a 1-cell overlap returns rc=-1. Shifting block+question
   together (+1, +8) still works, so no absolute 4096 magic constant exists (N_CTX=8192).
5. Slot4 replacement at delta 3886, 18 cells: project copy -> pass (E); project paraphrase
   -> fail (F). Same geometry, same BOS convention, so the pair is controlled.
6. Home replaced by an unrelated real fact (21 cells, same position/delta) -> fail and the
   model invents an answer. Removing home content is what breaks it.

## Not done (state them as not-done, never as no-effect)
- bias ladder b=0.5/1/2/4/8 (blocked: DLL ownership moved to the lead; and per the new
  instruction the bias probe is a measuring tool, not a fix - if it does not work, switch
  to the 14B model rather than digging)
- `kvshim_score_at` and the Delta/Delta-prime/Delta(A) table
- habit->pet replacement arms with the five guards
- rebuild + regression + b=0.0 byte-equality (requires the DLL)
## Cost of each not-done item (so the next planner can rank them)

| not-done item | runs needed | rebuild? | blocked by |
|---|---|---|---|
| bias ladder b=0.5/1/2/4/8 on a "position unusable" layout (@3885 or @3892) | 4 arms x 2 runs = 8 | yes, already-built [MASKBIAS] only (no code change if the env parse is intact) | DLL write ownership; one mask build must print exactly 1 [MASKBIAS] line |
| kvshim_score_at + Delta / Delta-prime / Delta(A) table | 6 layouts x 2 texts x 2 runs = 24, plus 2 determinism reruns | yes (new shim export, link only) | needs the DLL; also needs T and T-prime with equal token counts |
| habit -> pet replacement with the five guards | 2 arms x 2 runs = 4 | no (blocks already exist: habit 6c210314, pet 27a62f72) | none technical; only needs a free engine slot |
| rebuild + regression + b=0.0 byte equality | 2 runs | yes | DLL ownership (the lead holds it) |

Cheapest first: habit->pet (4 runs, no rebuild). Then bias ladder (8 runs, existing binary).
score_at is the expensive one and, per the new instruction, a measuring tool rather than a fix.

## Archive rule adopted from inspector
Every conclusion must have its binary: copy the exact DLL to
`kvmem/m2_visibility/dll_archive/<runid>_<sha8>.dll` **and recompute its sha at archive time**.
Reason: c7ea09bb (recorded by t031/t032 products) no longer exists anywhere on disk, and
`tools/kvshim_vk_t031.dll` hashes to ed91cbe0 - so the archive is broken and F vs F-prime
cannot be replayed. A conclusion whose binary is gone is a story, not a measurement.

## errno must be split, never merged
FileNotFoundError => the path is wrong (fix the path, do not wait).
PermissionError   => the file is mapped/locked (wait, do not rebuild).
The real DLL path is D:/llama-mem/tools/kvshim_vk.dll; build-vulkan/bin/ has no such file.
Merging the two into "cannot open" made me stop for the wrong reason once tonight.
