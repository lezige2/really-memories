# ARTIFACTS-KEY —— 关键产物清单（判决点名即收，**不计入文档索引**）

> **as-of**：`2026-10-26T19:00+08:00`（doc-scribe 现场扫判决 + 磁盘实算；本轮新增 §13.32 (b4) 验收 + A/B 23 件）。

> **范围（定死）**：**只收"被判决文件点名的坐标产物"** —— `LANDED-*.json` / `REGISTER.json` / `anchors_history.json` / `M6A-*` / `M6B-*` / 判决正文引用过的判定与红证产物。**不收** `out/*.json` 全集（数百个），不收未被判决引用的产物。

> **不计入 INDEX 计数**：这是"产物索引"，与 `INDEX.md` 的 46 行"文档索引"分开记；`INDEX.md` 顶部有指针指向本表。

> **复算**：`sha256sum <path> | cut -c1-16`、`wc -c <path>`；本表 sha **一律现值**（工作区原始字节、不归一）。

> **与判决的关系**：判决里写的是**签署时坐标**；本文给的是**现值**。两者不同时按 ANCHORS 的 R→A 降级处理，**不要用本表覆盖判决读数**。


## A 台账类（落地/登记/锚历史）—— 判决引作"落地坐标"

| 路径 | sha16 | 字节 | 被哪份判决引用（首个位置） |
|---|---|---:|---|
| `kvmem/m2_visibility/chat_lease/LANDED-m6a-fix.json` | `33cdf5027a75c6bb` | 13636 | M6A-FIX-VERDICT-lead.md（M6A-FIX-VERDICT-lead.md:3） |
| `kvmem/m2_visibility/chat_lease/LANDED-s1-dry.json` | `671035f30bf13462` | 18419 | M2-FULL-S1A-ACCEPT-lead.md（M2-FULL-S1A-ACCEPT-lead.md:22） |
| `kvmem/m2_visibility/chat_lease/LANDED-s1-real.json` | `797a845029f3f374` | 36120 | G4-CLOSURE-lead.md、M2-FULL-S1-ACCEPT-lead.md（G4-CLOSURE-lead.md:71） |
| `kvmem/m2_visibility/m1/LANDED-m18-3v2.json` | `766f44d645ce504a` | 7868 | M1.8-VERDICT-lead.md（M1.8-VERDICT-lead.md:45） |
| `kvmem/m2_visibility/m1/LANDED-m18.json` | `643a90871b38a26e` | 17103 | M1.8-VERDICT-lead.md（M1.8-VERDICT-lead.md:44） |
| `kvmem/m2_visibility/m1/LANDED-refreeze.json` | `5075fc4bc23b816f` | 6736 | M1.8-VERDICT-lead.md（M1.8-VERDICT-lead.md:108） |
| `kvmem/m2_visibility/m1/LANDED-restore.json` | `fe1f2ff914a80196` | 16683 | M1.8-VERDICT-lead.md（M1.8-VERDICT-lead.md:118） |
| `kvmem/m2_visibility/m1/_before/REGISTER.json` | `6e44d86a1358d5a8` | 22874 | M5-VERDICT-lead.md（M5-VERDICT-lead.md:27） |
| `kvmem/m2_visibility/m2_planner/LANDED-m2accept.json` | `5275b600ba6c3ca8` | 1561 | M2-ACCEPT-lead.md（M2-ACCEPT-lead.md:5） |
| `kvmem/m2_visibility/m2_planner/LANDED-m2planner-regen.json` | `5a3ea9533d2c5fc0` | 8592 | M2-ACCEPT-lead.md、M2-FULL-P1-ACCEPT-lead.md（M2-ACCEPT-lead.md:98） |
| `kvmem/m2_visibility/m2_planner/LANDED-p1.json` | `73522bc3cb69967b` | 11134 | M2-FULL-P1-ACCEPT-lead.md（M2-FULL-P1-ACCEPT-lead.md:43） |
| `kvmem/m2_visibility/m2_planner/_before/REGISTER.json` | `d42012673d836a53` | 9890 | M5-VERDICT-lead.md（M5-VERDICT-lead.md:27） |
| `kvmem/m2_visibility/m3/LANDED-l1.json` | `db2893ee4fc75802` | 6739 | M2-FULL-L1-ACCEPT-lead.md（M2-FULL-L1-ACCEPT-lead.md:43） |
| `kvmem/m2_visibility/m3/LANDED-l2.json` | `467e0b3f31cd3ff2` | 11260 | M2-FULL-L2-ACCEPT-lead.md（M2-FULL-L2-ACCEPT-lead.md:37） |
| `kvmem/m2_visibility/m4/_before/REGISTER.json` | `dbde8582ed239bec` | 14756 | M5-VERDICT-lead.md（M5-VERDICT-lead.md:27） |
| `kvmem/m2_visibility/m4/anchors_history.json` | `f200e6473adc2c0c` | 2275 | M4-ACCEPT-lead.md（M4-ACCEPT-lead.md:75） |
| `kvmem/m2_visibility/m6b/LANDED-m6b-b2a.json` | `00e26b42823747ee` | 8143 | M6B-PREREG-ACCEPT-lead.md（M6B-PREREG-ACCEPT-lead.md:3） |
| `kvmem/m4c_leases/out/LANDED-b09.json` | `1efd3701c335b518` | 1228 | M4C-VERDICT-lead.md（M4C-VERDICT-lead.md:25） |
| `kvmem/m4c_leases/out/LANDED-b10.json` | `80dedabcfcb992b8` | 1333 | M4C-CLOSURE-lead.md（M4C-CLOSURE-lead.md:13） |

| `kvmem/m2_visibility/m7/LANDED-m7-e3-cpu.json` | `631dfde6acad6ee2` | 7925 | M7 终判 §1/§7（落地台账） |
| `kvmem/m2_visibility/m7/LANDED-m7-f1.json` | `89f26fc4739b167c` | 7647 | M7 终判 §1/§7（落地台账） |
| `kvmem/m2_visibility/m7/LANDED-m7-f2.json` | `e6c7e8cc7c7be34f` | 12067 | M7 终判 §3/§7（落地台账） |

| `kvmem/m2_visibility/m7/LANDED-vram-ramp.json` | `d5dbf30c6f9f3c67` | 3168 | PROGRESS §13.15（显存爬坡落地台账：环境 + 三档 + 结论指针） |

| `kvmem/m2_visibility/m7/LANDED-m7-e3-gpu.json` | `cebe77646204a173` | 9827 | §13.16 落地台账（四场景 + 装置 + 主机侧） |
| `kvmem/m2_visibility/m6/LANDED-m6a2.json` | `98e0f090c8a5db59` | 5157 | §13.17 落地台账（M6a-2 可达性） |

| `kvmem/m2_visibility/m7/LANDED-m6b-atomic-supp.json` | `0b1eeac728e6a03f` | 7016 | §13.19 落地台账（M6b 补充证据包） |

| `kvmem/m2_visibility/m7/LANDED-m7-e3-gpu-b1rev.json` | `aef342f128efee68` | 4702 | §13.20 E3-GPU 现行台账（B1 修复后收尾轮） |
| `kvmem/m2_visibility/m6/LANDED-m6b-b1.json` | `155779f43d4aa574` | 22699 | §13.20 M6b-B1 落地台账（Python 层可签；B1 总体仍未接上） |

| `kvmem/m2_visibility/m5/LANDED-m5-c.json` | `f6c517db7815f153` | 15315 | §13.24 (c) 36 层落地台账（装置可用 / 判据作废 / 行为读数有效） |

## B 判定 / 红证 / 复算产物 —— 判决引作读数坐标或红证

| 路径 | sha16 | 字节 | 被哪份判决引用（首个位置） |
|---|---|---:|---|
| `kvmem/m2_visibility/chat_lease/run_compare.json` | `1eb7029167edd7e0` | 9514 | AUDIT-RESPONSE-lead.md（AUDIT-RESPONSE-lead.md:39） |
| `kvmem/m2_visibility/m1/out/M18-A-after-M18-3v2.json` | `9a9483861eb146bd` | 5592 | M1.8-VERDICT-lead.md（M1.8-VERDICT-lead.md:46） |
| `kvmem/m2_visibility/m1/out/M18-A-after-refreeze.json` | `673a2c9334d2f4a7` | 5592 | M1.8-VERDICT-lead.md（M1.8-VERDICT-lead.md:84） |
| `kvmem/m2_visibility/m1/out/M18-A-pre-M18-3v2.json` | `79456d7762d3c300` | 5660 | M1.8-VERDICT-lead.md（M1.8-VERDICT-lead.md:46） |
| `kvmem/m2_visibility/m1/out/M18-A11-redproof.json` | `1997e32a2187e56f` | 5604 | M1.8-VERDICT-lead.md（M1.8-VERDICT-lead.md:107） |
| `kvmem/m2_visibility/m1/out/M18-CMP-m18-3v2-vs-before.json` | `69572f127b720bc2` | 4134 | M1.8-VERDICT-lead.md（M1.8-VERDICT-lead.md:47） |
| `kvmem/m2_visibility/m2_planner/out/GREEN-SUITE-regen.json` | `52fc03d40a11f0b2` | 8596 | M2-ACCEPT-lead.md（M2-ACCEPT-lead.md:98） |
| `kvmem/m2_visibility/m2_planner/out/GREEN-SUITE.json` | `d3485eb29a97e5cb` | 8596 | M2-ACCEPT-lead.md（M2-ACCEPT-lead.md:97） |
| `kvmem/m2_visibility/m2_planner/out/M2-ACCEPT-r1.json` | `76e2783343c3e196` | 18666 | M2-ACCEPT-lead.md（M2-ACCEPT-lead.md:4） |
| `kvmem/m2_visibility/m2_planner/out/P1-after.json` | `495a54de8fabb607` | 5229 | M2-FULL-P1-ACCEPT-lead.md（M2-FULL-P1-ACCEPT-lead.md:17） |
| `kvmem/m2_visibility/m2_planner/out/P1-pre.json` | `9d5df8c3acd2c355` | 4976 | M2-FULL-P1-ACCEPT-lead.md（M2-FULL-P1-ACCEPT-lead.md:16） |
| `kvmem/m2_visibility/m2_planner/out/P1-regression.json` | `02b1e9bc9bfa87a4` | 3393 | M2-FULL-P1-ACCEPT-lead.md（M2-FULL-P1-ACCEPT-lead.md:20） |
| `kvmem/m2_visibility/m2_planner/out/P1-variant-allpinned-silent.json` | `b70cef0e9826b797` | 5307 | M2-FULL-P1-ACCEPT-lead.md（M2-FULL-P1-ACCEPT-lead.md:19） |
| `kvmem/m2_visibility/m2_planner/out/P1-variant-no-filter.json` | `22d96d19c6cee471` | 5341 | M2-FULL-P1-ACCEPT-lead.md（M2-FULL-P1-ACCEPT-lead.md:18） |
| `kvmem/m2_visibility/m2_planner/out/PLAN-SELFTEST-regen.json` | `0003eb0b8dea8c52` | 8799 | M2-ACCEPT-lead.md（M2-ACCEPT-lead.md:98） |
| `kvmem/m2_visibility/m2_planner/out/PLAN-SELFTEST.json` | `653d8d8733959240` | 8799 | M2-ACCEPT-lead.md（M2-ACCEPT-lead.md:97） |
| `kvmem/m2_visibility/m2_planner/out/RED-SUITE-regen.json` | `13771a2d633a8bb4` | 10217 | M2-ACCEPT-lead.md（M2-ACCEPT-lead.md:98） |
| `kvmem/m2_visibility/m2_planner/out/RED-SUITE.json` | `13771a2d633a8bb4` | 10217 | M2-ACCEPT-lead.md（M2-ACCEPT-lead.md:46） |
| `kvmem/m2_visibility/m2_planner/out/S1-cases-main.json` | `c9211e5dffcb76d1` | 6876 | M2-FULL-S1A-ACCEPT-lead.md（M2-FULL-S1A-ACCEPT-lead.md:18） |
| `kvmem/m2_visibility/m2_planner/out/S1-default-unchanged.json` | `12cebec6e516fd3b` | 1398 | M2-FULL-S1A-ACCEPT-lead.md（M2-FULL-S1A-ACCEPT-lead.md:19） |
| `kvmem/m2_visibility/m2_planner/out/S1-dryrun-2.json` | `007015df0fd44407` | 6091 | M2-FULL-S1A-ACCEPT-lead.md（M2-FULL-S1A-ACCEPT-lead.md:17） |
| `kvmem/m2_visibility/m2_planner/out/S1-dryrun.json` | `f2ae36b3ab740214` | 6091 | M2-FULL-S1A-ACCEPT-lead.md（M2-FULL-S1A-ACCEPT-lead.md:17） |
| `kvmem/m2_visibility/m2_planner/out/S1-pre.json` | `8bb70d6ba6a2dc3e` | 6658 | M2-FULL-S1A-ACCEPT-lead.md（M2-FULL-S1A-ACCEPT-lead.md:16） |
| `kvmem/m2_visibility/m2_planner/out/S1-real-2.json` | `39b7f9dee736d86b` | 17854 | M2-FULL-S1-ACCEPT-lead.md（M2-FULL-S1-ACCEPT-lead.md:76） |
| `kvmem/m2_visibility/m2_planner/out/S1-real-default-regression.json` | `39aa2505d74724a4` | 4063 | M2-FULL-S1-ACCEPT-lead.md（M2-FULL-S1-ACCEPT-lead.md:76） |
| `kvmem/m2_visibility/m2_planner/out/S1-real-smoke.json` | `a067294a524e42c3` | 10034 | M2-FULL-S1-ACCEPT-lead.md（M2-FULL-S1-ACCEPT-lead.md:76） |
| `kvmem/m2_visibility/m2_planner/out/S1-real.json` | `3df8d70bec1c5b94` | 17854 | M2-FULL-S1-ACCEPT-lead.md（M2-FULL-S1-ACCEPT-lead.md:76） |
| `kvmem/m2_visibility/m3/out/M3-L1-after.json` | `6954b190ebd71d18` | 8132 | M2-FULL-L1-ACCEPT-lead.md（M2-FULL-L1-ACCEPT-lead.md:24） |
| `kvmem/m2_visibility/m3/out/M3-L1-pre.json` | `dc31efac9ecf82e5` | 7454 | M2-FULL-L1-ACCEPT-lead.md（M2-FULL-L1-ACCEPT-lead.md:24） |
| `kvmem/m2_visibility/m3/out/M3-L1-recheck-after-L2-v2.json` | `383516da95ecf92f` | 8132 | M2-FULL-L2-ACCEPT-lead.md（M2-FULL-L2-ACCEPT-lead.md:33） |
| `kvmem/m2_visibility/m3/out/M3-L1-variant.json` | `77db39ddd69f34c3` | 7496 | M2-FULL-L1-ACCEPT-lead.md（M2-FULL-L1-ACCEPT-lead.md:24） |
| `kvmem/m2_visibility/m3/out/M3-L2-after-v2.json` | `e68df9a404c5fadc` | 6726 | M2-FULL-L2-ACCEPT-lead.md（M2-FULL-L2-ACCEPT-lead.md:16） |
| `kvmem/m2_visibility/m3/out/M3-L2-pre-v2.json` | `428f4cfe3f9011da` | 6285 | M2-FULL-L2-ACCEPT-lead.md（M2-FULL-L2-ACCEPT-lead.md:16） |
| `kvmem/m2_visibility/m3/out/M3-L2-pre.json` | `5d2f864b301af8ec` | 3788 | M2-FULL-L1-ACCEPT-lead.md（M2-FULL-L1-ACCEPT-lead.md:72） |
| `kvmem/m2_visibility/m3/out/M3-L2-variant.json` | `0658aa48b64c1ce4` | 4043 | M2-FULL-L2-ACCEPT-lead.md（M2-FULL-L2-ACCEPT-lead.md:22） |
| `kvmem/m2_visibility/m4/run_m4_ablate_plate_a7.json` | `77e11a04aacd24c5` | 17238 | M4-ACCEPT-lead.md（M4-ACCEPT-lead.md:26） |
| `kvmem/m2_visibility/m4/run_m4_accept_recompute.json` | `0b865a97ac2a0a99` | 21644 | M4-ACCEPT-lead.md（M4-ACCEPT-lead.md:4） |
| `kvmem/m2_visibility/m4/run_m4_outfilter_selftest.json` | `a85ec0df2bfa3cd3` | 3856 | M4-ACCEPT-lead.md（M4-ACCEPT-lead.md:26） |
| `kvmem/m2_visibility/m4/run_m4_verify.json` | `857f13c514ad233e` | 13908 | M4-ACCEPT-lead.md（M4-ACCEPT-lead.md:57） |
| `kvmem/m2_visibility/m4/run_m4_verify_a4.json` | `59edbd82d4b9ae44` | 17332 | M4-ACCEPT-lead.md（M4-ACCEPT-lead.md:20） |
| `kvmem/m2_visibility/m4/run_m4_write.json` | `6408d8e2ecdf6ee5` | 13402 | M4-ACCEPT-lead.md（M4-ACCEPT-lead.md:22） |
| `kvmem/m2_visibility/m5/evidence_m5.json` | `0f57f4357452a865` | 20536 | M5-VERDICT-lead.md（M5-VERDICT-lead.md:25） |
| `kvmem/m2_visibility/m5/out/M5C-c01-r1.json` | `2fc02488554fad80` | 88271 | M5-VERDICT-lead.md（M5-VERDICT-lead.md:22） |
| `kvmem/m2_visibility/m5/run_m5_probe_a.json` | `be11284797667a79` | 26430 | M5-VERDICT-lead.md（M5-VERDICT-lead.md:20） |
| `kvmem/m2_visibility/m6/out/M6A-REACHABILITY.json` | `76eb3f56061ce35c` | 40850 | M6A-FIX-VERDICT-lead.md（M6A-FIX-VERDICT-lead.md:3） |
| `kvmem/m2_visibility/m6b/out/M6B-B2A-CHAT-RED.json` | `8aca9868cdeae5e1` | 6867 | M6B-PREREG-ACCEPT-lead.md（M6B-PREREG-ACCEPT-lead.md:3） |
| `kvmem/m2_visibility/m6b/out/M6B-B2A-RED.json` | `d96c561ac8ed3ee7` | 5056 | M6B-PREREG-ACCEPT-lead.md（M6B-PREREG-ACCEPT-lead.md:3） |
| `kvmem/m4c_leases/out/M4C-DELETE-SITE1-base-b09-base-e6463aa2.json` | `12950f6a3fd0226f` | 3806 | M4C-VERDICT-lead.md（M4C-VERDICT-lead.md:45） |
| `kvmem/m4c_leases/out/M4C-DELETE-SITE1-deleted-b09-deleted-2c795100.json` | `55cd3ba5216293b5` | 3858 | M4C-VERDICT-lead.md（M4C-VERDICT-lead.md:46） |
| `kvmem/m4c_leases/out/M4C-SITE3-green-b09-green-b11f1875.json` | `f3f6ce7fe5f04040` | 7781 | M4C-VERDICT-lead.md（M4C-VERDICT-lead.md:41） |
| `kvmem/m4c_leases/out/M4C-SITE3-green-b09-inject-18d4a704.json` | `62e7973dfa1287c3` | 1315 | M4C-VERDICT-lead.md（M4C-VERDICT-lead.md:43） |
| `kvmem/m4c_leases/out/M4C-SITE3-red-b09-red-1b6187f9.json` | `dd46774cae873989` | 5750 | M4C-VERDICT-lead.md（M4C-VERDICT-lead.md:42） |
| `kvmem/m4c_leases/out/M4C-SITE3-unmount-dropnonempty-b09-drop-014ff511.json` | `1636404475cf5390` | 7796 | M4C-VERDICT-lead.md（M4C-VERDICT-lead.md:44） |
| `kvmem/m4c_leases/out/SELFCHECK-0f699908.json` | `5fc96db90cce689f` | 2041 | M4C-VERDICT-lead.md（M4C-VERDICT-lead.md:27） |
| `kvmem/m4c_leases/out/SELFCHECK-409d2c82.json` | `12af1aede278361b` | 2041 | M4C-CLOSURE-lead.md（M4C-CLOSURE-lead.md:16） |
| `kvmem/m4c_leases/out/m4c4/M4C4-deleted-b10-m4c4-deleted-1b599550.json` | `4ada6cec7621b660` | 5537 | M4C-CLOSURE-lead.md（M4C-CLOSURE-lead.md:24） |
| `kvmem/m4c_leases/out/m4c4/M4C4-green-b10-m4c4-green-fd9b6f9f.json` | `08a197d2da7322cf` | 4173 | M4C-CLOSURE-lead.md（M4C-CLOSURE-lead.md:23） |

| `kvmem/m2_visibility/m6b/out/M6B-B2B-P3.json` | `bd8e36d8c5223b07` | 8641 | M6B-PREREG-ACCEPT-lead.md（§2 B2b） |
| `kvmem/m2_visibility/m6b/LANDED-m6b-b2b.json` | `3b1e4f016afd5016` | 7113 | M6B-PREREG-ACCEPT-lead.md（§2 B2b；lead 提示可能再变） |
| `kvmem/m2_visibility/m6b/_run_m6b_b2b.py` | `16a555835c7516a9` | 14374 | M6B-PREREG-ACCEPT-lead.md（§2 B2b） |
| `docs/_work/INSPECTOR-M6B-REVIEW.md` | `e7cb51a82aa2c22d` | 21436 | M6B-PREREG-ACCEPT-lead.md（终版，B2b 已判） |

| `kvmem/m2_visibility/m7/out/M7-F1-UNIT.json` | `98fb19da41f5fd5d` | 5356 | M7 终判 §1（F1-atomic/short-write） |
| `kvmem/m2_visibility/m7/out/M7-F2-UNIT.json` | `a8dfdbee99ec7877` | 8339 | M7 终判 §3/§4（F2-tail / F2-backward） |
| `kvmem/m2_visibility/m7/out/M7-F2-EVENTS.jsonl` | `16b8c10307deac8b` | 1885 | M7 终判 §3（事件流） |
| `kvmem/m2_visibility/m7/out/M7-E3-CPU-ATOMIC.json` | `69eff505382212b1` | 14643 | M7 终判 §1（E3-CPU 14B block 真机） |
| `kvmem/m2_visibility/m7/out/M7-E3-CPU-TAIL.json` | `65d9410b96d9b0ed` | 8100 | M7 终判 §3/§4/§5（E3-CPU tail 与 S4′/S4″） |
| `kvmem/m2_visibility/m7/out/M7-E3-CPU-EVENTS.jsonl` | `dc9bed6fcdcd640e` | 522 | M7 终判 §3（事件流） |
| `kvmem/m2_visibility/m7/out/M7-CPU-REBUILD.json` | `f55dfd9a571f1306` | 2493 | M7 终判 §7（provenance / vulkan_imported=false） |
| `kvmem/m2_visibility/m7/out/M7-CPU-REBUILD-VERIFY2.json` | `c6b3378857870ad6` | 1456 | M7 终判 §7（verify.sh 12/12 + item1 600/0） |

| `kvmem/m2_visibility/m7/out/M7-VRAM-RAMP.json` | `7953bba770f5b3f9` | 3751 | PROGRESS §13.15（三档显存爬坡原始读数：peak/load/prefill/decode/WS；100 ms 采样、无 kill） |

| `kvmem/m2_visibility/m7/out/M7-E3-GPU.json` | `5493d3ca4879eb6d` | 31688 | §13.16/§13.20 E3-GPU (a) 读数；**现行件 = B1 修复后收尾轮**（S1–S4 通过、峰值 7.3740/7.3352×4 GiB、`kill_arm=未做`）；§13.16 已签 `e6b03da6`/30,561 与 10:04 轮 `3011c9ec`/30,592 均保留、`corrections[]` 前驱链 |
| `kvmem/m2_visibility/m7/PREREG-M7-E3-GPU.md` | `e75a425b7ef15201` | 8833 | §13.16 预登记（self_sha16=d7f71236038527db；落盘时结果产物数=0） |
| `kvmem/m2_visibility/m6/out/M6A2-REACHABILITY.json` | `d89e5dab5ede0024` | 60176 | §13.17 三条不变量可达性探针（E-stub，非引擎红证） |
| `docs/_work/INSPECTOR-M7-E3GPU-AUDIT.md` | `e6a58bf315680610` | 9705 | §13.16 审计 R1（判不可签，列 B1–B3） |
| `docs/_work/INSPECTOR-M7-E3GPU-AUDIT-R2.md` | `a2d240884ef1a370` | 7190 | §13.16 审计 R2（判可签 (a)；G1–G5 缺口） |
| `docs/_work/INSPECTOR-M6A2-AUDIT.md` | `3338d3de9d4a12df` | 7355 | §13.17 独立审计（E-stub 证据等级核对） |

| `kvmem/m2_visibility/m7/out/_e3gpu_run.py` | `2c166ec71921585b` | 48970 | §13.16 E3-GPU 执行器（task-50 改版，`host_check()` 在 `:175`）；**旧 `cf152370d5fefffa` / 35,684 已作废** |

| `docs/_work/INSPECTOR-M6B-RECHECK.md` | `00490215083acb70` | 9557 | §13.18 M6b 复判依据（B2a 已修/CPU 行为级；B1、B2b-prefix 未接上；B2b-tail 部分覆盖；B3 不排期） |

| `kvmem/m2_visibility/m7/out/M6B-ATOMIC-STATIC.json` | `3482236d1daf0949` | 9382 | §13.19 静态不变量扫描（session 目标写点；产品非原子写=0） |
| `kvmem/m2_visibility/m7/out/M6B-FS-KILL.json` | `3bb5fee95189db5e` | 21508 | §13.19 文件层真 SIGKILL（原子 6/6 before|after、红 6/6 third） |
| `kvmem/m2_visibility/m7/out/_m6b_fs_kill.py` | `32d08a65b9311c9d` | 14177 | §13.19 文件层 SIGKILL 实验脚本 |
| `docs/_work/INSPECTOR-M6B-SUPP-AUDIT.md` | `bcacdc59d5ba8eaf` | 7203 | §13.19 独立审计（可签 E1/FS；4 条非阻塞风险） |

| `kvmem/m2_visibility/m5/out/M5-36A-pairs.json` | `f0767d84c16c31bb` | 7503 | §13.21 规则臂 30 对（model_calls=0、excluded=[]） |
| `kvmem/m2_visibility/m5/out/M5-36A-pairs-model.json` | `aa9e6106925657e1` | 7851 | §13.21 模型臂 accepted 16/30（excluded=14 全 verbatim_copy） |
| `kvmem/m2_visibility/m5/out/M5-36A-intent-sealed.json` | `9f14097996e5deb9` | 2184 | §13.21 规则臂 sealed intent |
| `kvmem/m2_visibility/m5/out/M5-36A-intent-sealed-model.json` | `6e4656d3c41ec7d7` | 1373 | §13.21 模型臂 sealed intent |
| `kvmem/m2_visibility/m5/out/M5-36A-adj.json` | `1f5d7a5447478802` | 10653 | §13.21 规则臂 ADJ（与 REVIEW 30/30） |
| `kvmem/m2_visibility/m5/out/M5-36A-judge.json` | `bff8a34ba652d1e2` | 27935 | §13.21 规则臂 JUDGE（28/30，不一致 P13/P25） |
| `kvmem/m2_visibility/m5/out/M5-36A-rule-arm-result.json` | `14dcc5a973d41359` | 2968 | §13.21 规则臂结果 |
| `kvmem/m2_visibility/m5/out/M5-36A-rule-arm-result-v2.json` | `01c8c1b54ff65b03` | 5716 | §13.21 规则臂结果 v2 |
| `kvmem/m2_visibility/m5/out/M5-36A-model-adj.json` | `1b52862fe64ad384` | 6035 | §13.21 模型臂 ADJ |
| `kvmem/m2_visibility/m5/out/M5-36A-model-judge.json` | `8bc7af8eb82aed86` | 17928 | §13.21 模型臂 JUDGE |
| `kvmem/m2_visibility/m5/out/M5-36A-model-arm-result.json` | `8f1cf092af54cc88` | 3103 | §13.21 模型臂结果 |
| `kvmem/m2_visibility/m5/out/M5-36A-alignment.json` | `b38c17f7be01a8e2` | 38475 | §13.21 对齐件 |
| `kvmem/m2_visibility/m5/out/M5-36A-pilot.json` | `f86ecbfd68cbc70e` | 7868 | §13.21 试跑台账（judge_adj.status=已接（含 1 类阻塞缺陷，2 例）） |
| `kvmem/m2_visibility/m5/out/M5-36A-pilot-model.json` | `b6f086bc771d37d4` | 22809 | §13.21 模型臂试跑台账 |
| `docs/_work/REVIEW-M5-36A-blind.json` | `39d1d24860294ee3` | 9143 | §13.21 独立盲标 REVIEW（与 ADJ 30/30，0 mismatch） |
| `docs/_work/PREREG-M5-JUDGE-v2.md` | `6c77b56f406432aa` | 35739 | §13.21 下一步：judge v2.1 预登记（θ=0.20 固档、回归 46 对） |

| `kvmem/m2_visibility/m6/out/M6B-B1-FIX.json` | `f37635532df1b673` | 23027 | §13.20 B1 修复链读数（红臂 5/5 / 绿臂 reset=0 / 零行为 9 字段 equal） |
| `kvmem/m2_visibility/m6/out/M6B-DURABILITY.json` | `7747655babffc2c6` | 3505 | §13.20 持久化单测（`durability_mode=write_through`、`fallback_used`） |
| `kvmem/m2_visibility/m7/out/M6B-FS-KILL-FUZZ.json` | `958d58a97e4575f6` | 19674 | §13.20 20+20 随机 kill fuzz（原子 third=0 / 红 third=20/20、seed 20261026） |
| `kvmem/m2_visibility/m6/out/M6B-B1-SCRATCH.json` | `9788dad6e2e27eca` | 1150 | §13.20 scratch 撞 seq 单测（`9788dad6`/1,150：red `[0,-1]` / green `[7,6]`） |
| `kvmem/m2_visibility/m6/out/_before/M6B-B1-baseline.json` | `f9ddccf555fbf626` | 845 | §13.20 零行为基线（9 字段 equal 的对照件） |
| `kvmem/m2_visibility/m7/out/M7-E3-CPU-B1.json` | `07eb446dbc2f8e9b` | 3315 | §13.20 E3-CPU 收尾（真 14B、`gpu=0`、pid 11308、load 38.74 s） |
| `kvmem/m2_visibility/m5/m5_ground_v2.py` | `5e11e1ac06f022c7` | 66413 | §13.23 judge v2.1 实现（`supersedes m5_ground.py 86b7c501`） |
| `kvmem/m2_visibility/m5/out/M5-JUDGE-v2-regression.json` | `205a61dc51b3cb4a` | 193316 | §13.23 46 对回归读数（`diff_vs_v1` 只 P13/P25） |
| `kvmem/m2_visibility/m5/LANDED-m5-judge-v2.json` | `8bb5e4dec15c59c1` | 11068 | §13.23 judge v2.1 落地台账（in-sample / 未校准限定） |
| `docs/_work/INSPECTOR-M6B-B1-AUDIT.md` | `47094ac4fa83e282` | 14106 | §13.20 独立审计（可引用 §8；缺口 A/C/D） |
| `docs/_work/INSPECTOR-M5-JUDGE-V2-AUDIT.md` | `9b453349ab719d2a` | 18046 | §13.23 独立审计（限定可签）；**现盘为 R1–R6 整改后重出件**（含「附：整改增量复核」；整改前快照 `29c87901`/11,946 留痕） |

| `kvmem/m2_visibility/m5/out/M5C-36-r1.json` | `c3b8c062e84b2463` | 317123 | §13.24 (c) 8 场景主跑原始件 |
| `kvmem/m2_visibility/m5/out/M5C-36-r1.attempt1-6f21294685dfa400.json` | `6f21294685dfa400` | 12489 | §13.24 attempt#1（工具 OverflowError，`counted_in_verdict=false`） |
| `kvmem/m2_visibility/m5/out/M5C-36-cand-raw.json` | `ea7a5a5bc46883ed` | 28786 | §13.24 候选 raw 文本（R9 地址「2 单元 602」证据） |
| `kvmem/m2_visibility/m5/out/M5C-36-adj.json` | `0d882f20987fea70` | 60432 | §13.24 ADJ 基准（185 句：64/18/0/103）；主口径分母来源 |
| `kvmem/m2_visibility/m5/out/M5C-36-review.json` | `3666cf58b1c55317` | 87811 | §13.24 独立 REVIEW（183 句：68/18/2/95，2 处切句差异） |
| `kvmem/m2_visibility/m5/out/M5C-36-judge.json` | `9c2d2be5aa839068` | 261594 | §13.24 JUDGE（非空 185 句） |
| `kvmem/m2_visibility/m5/out/M5C-36-alignment.json` | `aaed082264712c59` | 245640 | §13.24 三方对齐件（245,640 B） |
| `kvmem/m2_visibility/m5/out/M5C-36-resume-S8.kvmem` | `479683b524f136b1` | 19640216 | §13.24 S8 save→新进程 load 件（19,640,216 B） |
| `kvmem/m2_visibility/m5/out/_k1_park_child.py` | `acc8f4fd77e1e682` | 39224 | §13.27 K1 子进程（**现盘 = fsync-every 版**；pre-instrument 原件另列，`93391078/24,243`） |
| `kvmem/m2_visibility/m5/out/_k1_park_parent.py` | `7ac8cef82a1bbff3` | 20254 | §13.25 K1 父进程（真 `TerminateProcess` 计划；本轮 `armed=false`） |
| `kvmem/m2_visibility/m5/out/_k1_recovery.py` | `52f33f17e10ee7ca` | 7029 | §13.25 K1 恢复段脚本（本轮 `load_strict` = `skipped`） |
| `kvmem/m2_visibility/m5/out/_k1_fixture_manifest.json` | `d2d6ab0b6f806e15` | 594 | §13.25 K1 夹具清单 |
| `kvmem/m2_visibility/m5/out/M5-K1-DRYRUN.json` | `2507a2a59362e2c7` | 29461 | §13.25 空枪试装（3/3 save third=0、`signals_sent=0`、`armed=false`、`kill_attempts=0`） |
| `kvmem/m2_visibility/m5/out/M5-K1-DRYRUN.attempt1-c1a8603ab264b8d2.json` | `c1a8603ab264b8d2` | 13246 | §13.25 试装 attempt#1 |
| `kvmem/m2_visibility/m5/out/_k1_park_result_001.json` | `56525002f2645b64` | 3765 | §13.25 停放子进程单次结果 |
| `kvmem/m2_visibility/m5/out/M5-K1-IO-MICROBENCH.json` | `66577f63bd129dfa` | 227945 | §13.25 纯文件微基准（稳态 0.529 s、最慢 chunk 8.003 ms、`>1s` chunk=0）⇒ 129 s 停顿不归因 save |
| `kvmem/m2_visibility/m5/out/_k1_io_microbench.py` | `c5b9edb689cc889e` | 10648 | §13.25 微基准脚本 |
| `docs/_work/PREREG-M5-C.md` | `250dbb417a7e7470` | 14071 | §13.24 (c) 预登记（8 场景逐字、n_predict=192、θ=0.20 固档） |
| `kvmem/m2_visibility/m5/PREREG-M5-PROBE-C.md` | `32bb07a0ac4a5f22` | 14588 | §13.24 被取代的旧 (c) 预登记（`superseded by 250dbb41`） |
| `docs/_work/PREREG-KILL-ARM-v2.md` | `42434b91d3923d1a` | 18253 | §13.25 K1 预登记（100 次真杀分布；禁「GPU kill 通过」） |
| `docs/_work/LEAD-M5-C-ADJUDICATION.md` | `60fedd7d4bbf0556` | 10023 | §13.24 LEAD 裁决（§0 主口径 / §2 机制 / §3 四态 / §5 十三件坐标） |

| `docs/_work/PREREG-M5-JUDGE-v2.2.md` | `fdf7ca2ae939a3a4` | 9351 | §13.26 v2.2 判据预登记（先立·不实现；(c) 为其 in-sample，有效性须新样本外集） |

| `kvmem/m2_visibility/m5/out/_k1_park_child.pre-instrument.py` | `9339107866cbc84c` | 24243 | §13.27 K1 子进程**未加仪表原件**（`§13.25` 主语；现盘同名文件已被 `acc8f4fd` 覆盖） |
| `kvmem/m2_visibility/m5/out/M5-K1-WARMUP.json` | `a23abaf26c651c83` | 15752 | §13.27 原版 warm-up：冻结 **10.006 s**（`warmup_timeout_terminate=1`、`formal_stage_kills=0`）
| `kvmem/m2_visibility/m5/out/M5-K1-WARMUP-SETTLE.json` | `2ed0e41306849e0e` | 28145 | §13.27 settle 4 KiB 探针 + 重试：仍冻结 @3 MiB
| `kvmem/m2_visibility/m5/out/M5-K1-WARMUP-1MIB.json` | `020be5a92f264ff2` | 4969 | §13.27 1 MiB 小载荷：**冻结 @629,148 B（~0.25 s）**
| `kvmem/m2_visibility/m5/out/M5-K1-SLEEP-S1.json` | `08ca4d70ae2baeef` | 9219 | §13.27 park 后真等 5 s：**冻结 @3,670,016 B（0.359 s）**
| `kvmem/m2_visibility/m5/out/M5-K1-FSYNC-B1.json` | `26352059fd79f1a0` | 9922 | §13.27 fsync 每 8 chunk：冻结 @4,194,304 B / 64 chunks（0.421 s） |
| `kvmem/m2_visibility/m5/out/M5-K1-FSYNC-B3.json` | `9a417c78ef4d0e03` | 9503 | §13.27 fsync 每 1 chunk：**冻结 @4,194,304 B / 64 chunks**（0.438 s）
| `kvmem/m2_visibility/m5/out/M5-K1-STALL-LOCATE.json` | `007ba7b215d93e29` | 138990 | §13.27 定位臂：`vk=on` 180 s 硬停冻结 / **`vk=off` 5.299 s 正常完成、5/5 `third=0`** |
| `kvmem/m2_visibility/m5/out/M5-K1-STALL-MECH.json` | `81af2798702531e4` | 414827 | §13.27 机理臂 V1/V2/V3（逐边界 trace+fsync）：**全部「通过」= Heisenbug 被掩蔽**，不作可行配置
| `kvmem/m2_visibility/m5/out/M5-K1-UNATTACHED.json` | `dff70c0775e46b94` | 5938 | §13.27 汇总件：`status=未接上（环境冻结）`、`l1_runs=0`、`kill_attempts=0`、`criteria_unchanged=true` |
| `docs/_work/PREREG-M5-JUDGE-v2.3.md` | `5a3f12f2a742a864` | 10394 | §13.28 v2.3 判据预登记（成分分级 A/B + 系词白名单 + 前导修剪；未实现） |
| `kvmem/m2_visibility/m5/m5_ground_v2_2.py` | `ae5ceea994c05691` | 36005 | §13.28 v2.2 判据实现（已实现、`not_adopted`；**不得写成已否决判据/已验证**） |
| `kvmem/m2_visibility/m5/out/M5-JUDGE-v2.2-INSAMPLE-REPLAY.json` | `29a9498f0750ba29` | 211198 | §13.28 v2.2 in-sample 重放：**抓 18/18、误伤 41/64**（`in_sample_replay=true`、`not_acceptance=true`） |
| `kvmem/m2_visibility/m5/out/_v22_selftest.json` | `f1b061ddcd851f84` | 3948 | §13.28 v2.2 selftest：**13/13 全过** |
| `kvmem/m2_visibility/m5/m5_ground_v2_3.py` | `cc03e48c360ae0ee` | 44209 | §13.29 新判据实现（in-sample 达线；`not_acceptance=true`、`design_accepted_in_sample=true` ≠ 有效） |
| `kvmem/m2_visibility/m5/out/M5-JUDGE-v2.3-INSAMPLE-REPLAY.json` | `fb4045afd7d87f04` | 223401 | §13.29 新判据首次实现重放：抓 partial hit **16/16**、总 **17/18**、**误伤 5/64**、极性冲突 0 |
| `kvmem/m2_visibility/m5/out/_v23_selftest.json` | `e238d140a47ffc66` | 4462 | §13.29 selftest **17/17** + `freeze` 锁定 v2.1/v2.2/预登记三件未动 |
| `kvmem/m2_visibility/m5/out/_v23_regression_stdout.json` | `e234b2733c047163` | 3233 | §13.29 实现轮回归 stdout（旁证；`--regression` 默认 `write=False`） |
| `kvmem/m2_visibility/m5/out/_v23_diagnose_stdout.json` | `861d5bb18327a216` | 965 | §13.29 实现轮诊断 stdout（旁证；误伤 5 条逐句定位） |
| `docs/_work/PREREG-M5-B.md` | `8102950d9de660be` | 12053 | §13.30 (b) rev1 预登记（8 场景/16 题；样本量 74<150 作废，LEAD 设计错误） |
| `docs/_work/PREREG-M5-B2.md` | `482a94820917d16e` | 12695 | §13.30 (b2) 预登记（8 场景/40 题；两率线 ≤20% / ≤15% 先定） |
| `docs/_work/LEAD-M5-B-ADJUDICATION.md` | `df1ae09cc9ecc0d2` | 5627 | §13.30 (b2) LEAD 裁定散文版（未通过；14/14 同因；预登记缺陷） |
| `kvmem/m2_visibility/m5/out/M5B-BATCH-b-rev1.json` | `a79e25dc4bff13b8` | 4835 | §13.30 b rev1 批次件（`未接上（样本量不足）`，未盲标未算两率） |
| `kvmem/m2_visibility/m5/out/M5B-fixture.json` | `82703b8c67e6ce7a` | 4759 | §13.30 b rev1 夹具（8 场景/16 题） |
| `kvmem/m2_visibility/m5/out/M5B-GEN.json` | `e74ee1951aa41c31` | 47750 | §13.30 b rev1 生成件（墙钟 245 s / 峰值 7.6265 GiB） |
| `kvmem/m2_visibility/m5/out/M5B-JUDGE.json` | `7acb93fd5373479f` | 80628 | §13.30 b rev1 判据输出（含空段计 `no_fact` 缺陷，仅记录） |
| `kvmem/m2_visibility/m5/out/M5B2-fixture.json` | `b09149fe42f4ff91` | 7236 | §13.30 b2 夹具（8 场景/40 题） |
| `kvmem/m2_visibility/m5/out/M5B2-GEN.json` | `d8fd814958699336` | 110382 | §13.30 b2 生成件（10m53s、峰值 7.6664 GiB、`signals=false`） |
| `kvmem/m2_visibility/m5/out/M5B2-GEN-pre-repair.json` | `064b4fdcc35e7570` | 100808 | §13.30 b2 生成件修复前留痕（不作判据输入） |
| `kvmem/m2_visibility/m5/out/M5B2-JUDGE.json` | `5deead7180dbb6a8` | 229930 | §13.30 b2 判据输出（510 非空句；判据 sha 前后未变） |
| `kvmem/m2_visibility/m5/out/M5B2-SENTENCES.json` | `6529e151568dc593` | 78825 | §13.30 b2 句表（510 非空 / raw 1,139 / 空段 629） |
| `kvmem/m2_visibility/m5/out/M5B2-adj-labels.json` | `b08521482b88faa8` | 50903 | §13.30 b2 ADJ 盲标（71/34/386/19） |
| `kvmem/m2_visibility/m5/out/M5B2-review-labels.json` | `1dfbb60436133b93` | 50691 | §13.30 b2 REVIEW 盲标（69/32/384/25；与 ADJ 500/510=98.04%） |
| `kvmem/m2_visibility/m5/out/M5B2-RATES.json` | `9ac66b6dfaf8f804` | 11407 | §13.30 b2 **两率最终件**（14/35=40.00%、10/71=14.08%、对齐 mismatch 0） |
| `kvmem/m2_visibility/m5/out/M5B2-LEAD-RULING.json` | `65a2124b73f17d53` | 4192 | §13.30 b2 裁决件（gold 71/35/385/19、10 条分歧裁定、`judge_viability=不成立`） |
| `docs/_work/PREREG-M5-B3-v2.4.md` | `37e3742c0e4056ef` | 5320 | §13.31 v2.4 口径更正预登记（只改判定词：`no_fact∧no_a_component`→`undecidable`） |
| `docs/_work/PREREG-M5-C2-SEMANTIC.md` | `4fc889483d4f49b3` | 7115 | §13.31 **待决**语义蕴含路线预登记（R1 NLI CPU / R2 14B GPU 自判；未实现，须用户拍板） |
| `kvmem/m2_visibility/m5/m5_ground_v2_4.py` | `1387b851450bde44` | 44286 | §13.31 v2.4 实现（vs v2.3 功能 diff 仅 L373 一行 + 2 行 selftest 调整） |
| `kvmem/m2_visibility/m5/out/_m5b3_selftest_v24.json` | `08e6e92c715fec58` | 4467 | §13.31 v2.4 selftest **17/17** + `freeze` 锁 v2.1/v2.2/预登记 v2.3 |
| `kvmem/m2_visibility/m5/out/M5B3-v24-RATES.json` | `3d5f5907e1e4e869` | 12830 | §13.31 (b2) 重算 **in-sample 非验收**：93 句改判 `undecidable`，漏判仍 14/35=40.00%、`same_as_v23=true` |
| `kvmem/m2_visibility/m5/out/_m5b3_v23_v24.diff` | `19c62687404532c6` | 1591 | §13.31 v2.3→v2.4 diff 证据（3 hunks / +3−3；功能 1 行） |
| `docs/_work/PREREG-M5-C2-B4.md` | `f30d89e30262b148` | 10910 | §13.32 (b4) 样本外验收集预登记（8 场景×5 题；rev5.1 冻结；`pass=false`） |
| `docs/_work/PREREG-M5-C2-B2EVAL.md` | `6b0d750abbd06b1b` | 4113 | §13.32 前序：(b2) 106 句读数预登记（**部分污染、非验收**） |
| `docs/_work/PREREG-M5-C2-REV5.md` | `81a5bb3ea4df642e` | 4807 | §13.32 前序：rev5 离线重判预登记（R4+ 证据存在性 / derived 可组合性） |
| `docs/_work/PREREG-M5-C2-REV4-1.md` | `69c8d48ea026c50a` | 6201 | §13.32 前序：rev4.1 预登记（修第 2 层 R1/R2 + 确定性臂） |
| `docs/_work/PREREG-M5-C2-REV4.md` | `be618108a82c2f42` | 6996 | §13.32 前序：rev4 抽取式判据预登记（`rev4_arch_ok=false`） |
| `docs/_work/PREREG-M5-C2-ORDER.md` | `fb0da1b792004fa2` | 5453 | §13.32 前序：列举顺序置换预登记（12 例×3 顺序） |
| `docs/_work/PREREG-M5-C2-FLOOR-REV2.md` | `54faca9edb3a8daf` | 6173 | §13.32 前序：FLOOR 正式协议 rev2（39 例） |
| `docs/_work/PREREG-M5-C2-FLOOR.md` | `dfc36bece621f871` | 7242 | §13.32 前序：FLOOR rev1（已被 FLOOR-REV2 取代，历史件） |
| `docs/_work/JUDGE-ROBUSTNESS-SPEC.md` | `5ad46f8efb762c6d` | 8555 | §13.32 前序：抽取式判据失效模式与兜底规范（冻结，§4 四规则） |
| `kvmem/m2_visibility/m5/out/M5B4-GEN.json` | `6eef5955bdf04e8e` | 77903 | §13.32 (b4) 生成件（8 场景/40 题/261 句、峰值 7.7899 GiB） |
| `kvmem/m2_visibility/m5/out/M5B4-SENTENCES.json` | `c349ca5a93192aac` | 99636 | §13.32 (b4) 句表（261 非空句） |
| `kvmem/m2_visibility/m5/out/M5B4-adj-labels.json` | `dc133ccd9523f6aa` | 16478 | §13.32 (b4) 盲标 A（与 B 一致率 242/261 = 92.72%） |
| `kvmem/m2_visibility/m5/out/M5B4-review-labels.json` | `3cf0f0e521bd8b78` | 16495 | §13.32 (b4) 盲标 B（独立复核） |
| `kvmem/m2_visibility/m5/out/M5B4-LEAD-RULING.json` | `9273ebc97aa1413a` | 13195 | §13.32 (b4) **金标当前版**（19/19 条 ruled 补全；`gold_changed=false`）。首版 `9054479b32b79eb1/10,208` 仅 11/19 留痕，已被本版替换、磁盘不再单独存在 |
| `kvmem/m2_visibility/m5/out/M5B4-JUDGE.json` | `6a3001b6ca23ef7d` | 452456 | §13.32 (b4) 判据 rev5.1 输出（246 前向、layer0 跳过 15、`parse_fail=1`） |
| `kvmem/m2_visibility/m5/out/M5B4-RATES.json` | `783d423a39db02e3` | 121993 | §13.32 (b4) 两率主件（漏判 4/41=9.76%、误判 7/46=15.22%、`pass=false`） |
| `kvmem/m2_visibility/m5/out/M5B4-RATES.md` | `661f44ceb9db6dac` | 5401 | §13.32 (b4) 读数摘要（含题级双口径与 abstain 敏感性） |
| `kvmem/m2_visibility/m5/out/M5B4-AB-OLD-VS-NEW.json` | `0ff84d2617ab8b99` | 68603 | §13.32 受控 A/B 原始件（old v2.3 × new rev5.1，同 261 句同金标） |
| `kvmem/m2_visibility/m5/out/M5B4-AB-OLD-VS-NEW.md` | `f3562a624c1f927f` | 4694 | §13.32 受控 A/B 摘要（Δ 不显著、口径敏感性两读） |
| `kvmem/m2_visibility/m5/out/M5B4-AUDIT.md` | `afb17aa6d858ecbd` | 8788 | §13.32 (b4) 独立复核（主读数一致；审出金标 8 条无留痕、题级分母歧义、parse_fail 敏感性缺失） |
| `kvmem/m2_visibility/m5/out/M5C2-REV5-OFFLINE.json` | `f304690658cb328d` | 138974 | §13.32 前序：rev5 离线重判件（零 GPU） |
| `kvmem/m2_visibility/m5/out/M5C2-REV5-1-OFFLINE.json` | `fb2d54a2cc502183` | 141242 | §13.32 前序：rev5.1 离线重判件（(b4) 判据前代） |
| `kvmem/m2_visibility/m5/out/M5C2-B2EVAL.json` | `553a96fc481fcf9c` | 153626 | §13.32 前序：(b2) 106 句读数（**部分污染、非验收**） |

## C 其他（会话态快照）

| 路径 | sha16 | 字节 | 被哪份判决引用（首个位置） |
|---|---|---:|---|
| `kvmem/sessions/live.json` | `4b18d1a8b0e6e74d` | 1595 | M4C-VERDICT-lead.md（M4C-VERDICT-lead.md:31） |

**统计**：A **29** ｜ B **195** ｜ C **1** ｜ **D 9** ｜ **E 32** ｜ **F 2** ｜ 合计 **268** 件（现场分段落数，不手写；task-78 +14、task-81 +5、task-84 +16、task-86 +6、b4 收敛 +23、b5 验收 +9、b7′ 开跑 +14、b7′ 判定 +15、headline 口径升级/SUPPLEMENT +1、终版引用（MERGE v3/INSPECTOR v2 v2/SUPPLEMENT v2/FINAL-REPORT）+2、C 版 v1.1 回归 +2。**更正**：旧统计行「A 31 / B 129」与基线实际（A 29 / B 131）不符，已按实际重数）。

## D M5C2 `(b5)` 验收链（2026-10-27）—— 唯一结论来源是 VERDICT

> **口径**：**b5 = 擦边**（H1；误判 9/72 = 12.50%，Wilson 上界 22.08% > 15%；漏判 0/29，上界 11.70%；三套 gold 一致）。**禁写「通过」「未通过」**。以下为 VERDICT `evidence_chain` 点名的产物现值。

| 路径 | sha16 | 字节 | 说明 |
|---|---|---:|---|
| `kvmem/m2_visibility/m5/out/M5C2-B5-VERDICT.json` | `fa93b38cdedea58e` | 4922 | **b5 唯一结论来源**（H1=擦边；禁写通过/未通过；00:12 corrections：caveats[4] 9/72、miss 上界 0.116970，grade 不变） |
| `kvmem/m2_visibility/m5/out/M5C2-B5-VERDICT-FREEZE.json` | `906d9fcc0643906f` | 842 | VERDICT 冻结 pin（frozen_at 2026-10-27T00:06，LEAD；含 corrections 块） |
| `kvmem/m2_visibility/m5/out/M5C2-B5-GEN.json` | `2b63a02463994c03` | 68184 | 生成 40/40（n_forward 40，one_shot_consumed） |
| `kvmem/m2_visibility/m5/out/M5C2-B5-SENTENCES.json` | `ba92635c8ad0c410` | 116566 | 句表 326 句 |
| `kvmem/m2_visibility/m5/out/M5C2-B5-GOLD.json` | `54aa3da53c45da69` | 64148 | LEAD-gold（agreement 319/326 = 97.85%，n_fp 72 / n_leak 29） |
| `kvmem/m2_visibility/m5/out/M5C2-B5-EXTRACT.json` | `93505eecc539634a` | 444613 | 抽取 326/326（elapsed 2,418.298 s，peak 8.0423 GiB） |
| `kvmem/m2_visibility/m5/out/M5C2-B5-DECIDE.json` | `59da64cb6f2464de` | 741080 | 判据读数（supported 102 / unsupported 206 / undecidable 17 / parse_fail 1） |
| `kvmem/m2_visibility/m5/out/M5C2-B5-AUDIT.json` | `f72d267ec9b7eef1` | 109477 | 独立第二实现，DECIDE 逐句 diff=0（n_diff=0） |
| `kvmem/m2_visibility/m5/out/M5C2-B5-RATES.json` | `aae1b790d19dfa73` | 75582 | 两率/CI 与三套 gold 敏感性 |

（以上 9 件为 D 批；`h1_feasibility b514f3bd`、`sensitivity 02f5927c`、盲标 A/B 等见 VERDICT `evidence_chain`，不重复计行。）

## E M5C2 `(b7′)` 批（2026-10-27）—— rev7.2 首测（新数据集；**读数未出，不写结论**）

> **口径**：b7′ = 15 场景 × 5 题 = 75 题（3 detail + 2 lure，题型比同 b5）；题面先冻；跑前冻结、one_shot。最终读数件 `M5C2-B7-READINGS.json` **待落盘**，本节只登记已落盘件与预置读法件。

| 路径 | sha16 | 字节 | 说明 |
|---|---|---:|---|
| `kvmem/m2_visibility/m5/out/M5C2-B7-QUESTIONS.json` | `f1f059539453d562` | 15964 | 题面 75 题（15×5；pin `1baeda859bc05549`） |
| `kvmem/m2_visibility/m5/out/M5C2-B7-QUESTIONS-FREEZE.json` | `1baeda859bc05549` | 1697 | 题面冻结 pin |
| `kvmem/m2_visibility/m5/out/M5C2-B7-GEN.json` | `041b51eb7837aa90` | 140514 | 生成 75/75（n_forward 75、one_shot_consumed、peak 8.1819 GiB） |
| `kvmem/m2_visibility/m5/out/M5C2-B7-SENTS.json` | `c5a49a696b66f0c7` | 288805 | 切句 623 句（pin `60b369bf8cfcef2b`） |
| `kvmem/m2_visibility/m5/out/M5C2-B7-SENTS-FREEZE.json` | `60b369bf8cfcef2b` | 1317 | 切句冻结 pin（frozen_at 11:41） |
| `kvmem/m2_visibility/m5/out/M5C2-B7-BLIND-A.json` | `50d1b6da781e2c3b` | 37632 | 盲标 A（四态 148/65/377/33） |
| `kvmem/m2_visibility/m5/out/M5C2-B7-BLIND-B.json` | `d8e51d652c4e333f` | 40023 | 盲标 B |
| `kvmem/m2_visibility/m5/out/M5C2-B7-GOLD.json` | `d5726d9cc59bb6f6` | 110099 | LEAD-gold **v2**（盲标一致 597/623 = 95.83%；四态 148/380/63/32；v1 `3afddd24`/109,291 已作废、保留追溯：改判 1 条 `b7-s4-q3-s07` no_fact→support_present，独立复核 `f8aa4bfb` 采纳） |
| `kvmem/m2_visibility/m5/out/M5C2-B7-GOLD-FREEZE.json` | `19a6a653f86f6b01` | 1249 | gold 冻结 pin（v2 rev2；supersedes v1 pin `df72edea`） |
| `kvmem/m2_visibility/m5/out/M5C2-B7-HOSTGATE-BEFORE.json` | `bdd354bfbdc7f871` | 2284 | 严格 host gate 记录（读法件 §0-5） |
| `kvmem/m2_visibility/m5/out/M5C2-B7-ATTEMPTS.json` | `8398324ffefb128c` | 13614 | 一次性运行台账（含 extract/decide 等阶段记录） |
| `kvmem/m2_visibility/m5/out/M5C2-B7-SCRIPTS-FREEZE.json` | `558fd9aa28ad691c` | 3629 | b7′ 脚本冻结 pin |
| `kvmem/m2_visibility/m5/out/M5C2-B7-READINGS-FREEZE.json` | `529915a667f7dbe6` | 2147 | 读法层脚本冻结 pin（最终版；A2/A3/A4/A5 pins） |
| `kvmem/m2_visibility/m5/out/M5C2-B7-WIDE-SENSITIVITY.json` | `3e46633a6b27a561` | 854236 | 宽读法 B 正式读数（FP 21/147、漏判 11/62；与 A diff 11） |
| `kvmem/m2_visibility/m5/out/M5C2-B7-VERDICT.json` | `1cb7a7961aefe0c6` | 4165 | **b7′ 唯一结论来源**：擦边（两读一致；A 窄 headline 22/147、10/62） |
| `kvmem/m2_visibility/m5/out/M5C2-B7-VERDICT-FREEZE.json` | `686f0ac963b1226d` | 586 | VERDICT 冻结 pin |
| `kvmem/m2_visibility/m5/out/M5C2-B7-VERDICT-SUPPLEMENT.json` | `5046d1c0fc697356` | 3070 | headline 口径升级件 **v1（已作废，保留追溯）**；被 v2 `a58c3c87` 取代 |
| `kvmem/m2_visibility/m5/out/M5C2-B7-VERDICT-SUPPLEMENT.json`（v2） | `a58c3c87393a5b0c` | 3871 | **口径升级件 v2 终值**：headline 三句 / operating point 四行 / 可达界 12.70% / layer0 with-without / 禁语 / terminal_reason；governance 收 MERGE v3 `6048139a`、INSPECTOR-S5 v2 `ee0abc1c` |
| `kvmem/m2_visibility/m5/out/M5C2-B7-READINGS.json` | `15190c2e53137905` | 15100 | 两读并列读数件（A/B 四档、Wilson、分母、caveat） |
| `kvmem/m2_visibility/m5/out/M5C2-B7-READINGS-AUDIT.json` | `97e28543c468f926` | 18240 | 读数独立复核 |
| `kvmem/m2_visibility/m5/out/M5C2-B7-DECIDE.json` | `adaf010425a4f30d` | 1863426 | 判据（rev7.2）判定产物 |
| `kvmem/m2_visibility/m5/out/M5C2-B7-EXTRACT.json` | `2804fbbb26bff2a3` | 951539 | 抽取产物（n_forward 581、layer0_skipped 42） |
| `kvmem/m2_visibility/m5/out/M5C2-B7-PROVENANCE-V2.json` | `96cd4bfe8df05185` | 13992 | 证据 provenance v2 |
| `kvmem/m2_visibility/m5/out/M5C2-B7-INVARIANCE20.json` | `a1d928df8affc5aa` | 8549 | 20/20 byte-identical 不变量 |
| `kvmem/m2_visibility/m5/out/M5C2-B7-MERGE-CHECK.json` | `6048139a67876f99` | 17060 | 合并检查 **v3**：**59/59、failed=[]、verdict=pass、evidence{C1,C2,C3} 齐全、falsifiability C1/C2/C3 均 fail_detected**（旧 `b599a62d`/`6ce45a78` 作废追溯） |
| `kvmem/m2_visibility/m5/out/M5C2-B7-GOLD-REVIEW.json` | `f8aa4bfbdf4ec8de` | 5461 | gold 独立复核（1 条改判来源） |
| `kvmem/m2_visibility/m5/out/M5C2-B7-INSPECTOR.json` | `9de882c8492ef717` | 17015 | b7′ 独立巡查 |
| `kvmem/m2_visibility/m5/out/M5C2-B7-INSPECTOR-S5.json` | `ee0abc1cad05c935` | 15341 | S5 巡查 **v2 终值**：①–④ pass、overall pass、无阻断（D1–D6 非阻断 caveat；旧 `9d838e56` 作废追溯） |
| `docs/_work/B7-FINAL-REPORT.md` | `9b0ed2d3178616d7` | 5294 | **b7′ 收口报告**（三数据集总表 / 可达界论证 / 完整证据链 / 披露 / 负结果价值 / 下一步两条） |
| `kvmem/m2_visibility/m5/out/M5C2-B7-EXTRACT-NOTES.json` | `73118d5da940c506` | 3804 | 抽取阶段说明/留痕 |
| `kvmem/m2_visibility/m5/out/M5C2-B7-EXTRACT-RESUME-SCRIPT-FREEZE.json` | `19f1e9d2a508a55b` | 1877 | 抽取续跑脚本冻结 pin |
| `kvmem/m2_visibility/m5/out/M5C2-B7-PROVENANCE-FIX-SCRIPT-FREEZE.json` | `ae3b9ddcc9266ae7` | 1030 | provenance 修复脚本冻结 pin |

**落盘状态**：EXTRACT / DECIDE / READINGS / VERDICT 均**已落盘**（见上表；最终结论件 `M5C2-B7-READINGS.json 15190c2e` / `M5C2-B7-VERDICT.json 1cb7a796`）。

（以上 32 件为 E 批；`RULING-M5C2-B7.md 3dfafd12`、`A2 320b643a`、`A3 10a23960`、`A4 8b7a7d47`、`ABORT` 为裁定文档，记 INDEX/文档侧，不重复计行。）

## F C 版产品可用性（产品证据；**不得进入研究线引用链**）

> **边界**：本节为**产品可用性**证据，与 H1/判据结论严格分开；**不得出现在研究线引用链**（不引为 H1/判据结论、不参与 b5/b6/b7 判定、不得据其宣称接地能力已验证）。

| 路径 | sha16 | 字节 | 说明 |
|---|---|---:|---|
| `kvmem/m2_visibility/m5/out/C-V1-1-REGRESSION.json` | `611fc849f7cb3118` | 6084 | **C 版 v1.1 回归**（mode=real_engine、verdict=通过、caveats=[]；V11-1 4/4、V11-2 rollover、V11-3 长回答 328 字/23.45 s、V11-4 三日志根 verify rc=0；supersedes `fb205637` 首轮假阴性留痕） |
| `kvmem/m2_visibility/m5/out/C-V1-1-REGRESSION-FREEZE.json` | `d2fe383ccbc750cd` | 878 | 回归件 **LEAD 外钉**（frozen_at 2026-10-27T14:02；isolation=产品证据/不入研究链） |

## 维护约定

1. **只增行、只换 sha**：产物更新（如 `LANDED-m6b-b2a.json` 指针修正）⇒ 换本表该行 sha，并在此留一行变更记录；不删旧行证据。
2. **新产物入表门槛**：必须有判决文件点名；否则不进（避免表膨胀）。
3. **待追加**：`M6B-B2B-*`（P3 出件后 lead 给 sha）。

### 变更记录

| 日期 | 变更 |
|---|---|
| 2026-10-25 | 建表：`LANDED-m6b-b2a.json` = `00e26b42823747ee` / 8,143 B（executor 修指针 + 补 `corrections[]` 后；旧 `0b0a6ff2` 作废）；`M6B-B2A-CHAT-RED.json` = `8aca9868cdeae5e1` / 6,867 B（旧 `dce1f205` / 5,356 作废）；`M6B-B2A-RED.json` = `d96c561ac8ed3ee7` / 5,056 B |
| 2026-10-25（追加） | B2b/P3 批：`M6B-B2B-P3.json` `bd8e36d8` / 8,641；`LANDED-m6b-b2b.json` `074ded0b` / 5,549（**lead 提示可能再变**）；`_run_m6b_b2b.py` `16a55583` / 14,374；`INSPECTOR-M6B-REVIEW.md` **`290b9c79` / 19,917（现盘；lead 给的 `b258f2b8` / 19,774 与现盘不符，见台账 §13）** |
| 2026-10-25（终版批） | `INSPECTOR-M6B-REVIEW.md` 终版 **`e7cb51a8` / 21,436**（含 P4 复核 + B2b 拆行 + chat/block 可达性差异；旧 `0a97ec2e`/`463037ee`/`290b9c79`/`b258f2b8`/`c37efa04` 全作废）；`LANDED-m6b-b2b.json` **`e6466c4b` / 6,262**（executor 加 `B2b_overall`/`B2b_tail` 字段，旧 `074ded0b`/5,549 作废）；`M6B-PREREG-ACCEPT-lead.md` 终版 **`a85dcb9e` / 7,101**（B2b 拆两行） |
| 2026-10-26（M7 判决批） | 新增 11 个 M7 锚（`M7-F1-UNIT` 98fb19da / `M7-F2-UNIT` a8dfdbee / `M7-F2-EVENTS` 16b8c103 / `M7-E3-CPU-ATOMIC` 69eff505 / `M7-E3-CPU-TAIL` 65d9410b / `M7-E3-CPU-EVENTS` dc9bed6f / `M7-CPU-REBUILD` f55dfd9a / `M7-CPU-REBUILD-VERIFY2` c6b33788 / `LANDED-m7-e3-cpu` 631dfde6 / `LANDED-m7-f1` 89f26fc4 / `LANDED-m7-f2` e6c7e8cc）；另 `M7-E3-F2-PREREG abdb0082/1,567` 未入表（仅台账引用） |
| 2026-10-26（task-42） | 新增 `M7-VRAM-RAMP.json` `7953bba7`/3,751（B 组）与 `LANDED-vram-ramp.json` `d5dbf30c`/3,168（A 组，落地台账）；同批 `PROGRESS §13.15` 落盘、§13.13 规则 4 行末加指针（状态更新见 §13.15） |
| 2026-10-26（task-52） | 新增 E3-GPU 批：`M7-E3-GPU e6b03da6/30,561`、`LANDED-m7-e3-gpu cebe7764/9,827`、`PREREG-M7-E3-GPU e75a425b/8,833`、审计 R1 `e6a58bf3/9,705`、R2 `a2d24088/7,190`；M6a-2 批：`M6A2-REACHABILITY d89e5dab/60,176`、`LANDED-m6a2 98e0f090/5,157`、审计 `3338d3de/7,355` |
| 2026-10-26（task-55） | `_e3gpu_run.py` 新增坐标 **`2c166ec71921585b` / 48,970**（old `cf152370d5fefffa`/35,684 作废，C1 式留痕）；`_e3gpu_harness.py` `b5493470`/9,063 **未入库**（被 run 版取代、自述禁止运行，只留盘，见 PROGRESS §13.16-8）；git 收口 main=`d3f1e2b` / full=`741dde9`（C20）/ `main..full=5` / full 未 push |
| 2026-10-26（task-58） | 新增 `INSPECTOR-M6B-RECHECK.md` `00490215083acb70`/9,557（§13.18 依据）；`tools/kvslots.py` 坐标 **`71498ea3`/23,769 → `a5c06b19`/25,933**（B2a 修复，旧值作废留痕） |
| 2026-10-26（task-64） | 新增 `M6B-ATOMIC-STATIC 3482236d/9,382`、`M6B-FS-KILL 3bb5fee9/21,508`、`_m6b_fs_kill.py 32d08a65/14,177`、`LANDED-m6b-atomic-supp 0b1eeac7/7,016`、审计 `INSPECTOR-M6B-SUPP-AUDIT bcacdc59/7,203`；口径：**E1/FS 文件层可签，GPU kill 臂仍 未做、本件不替代** |
| 2026-10-26（task-67） | 新增 M5 36 层 (a) 批 15 件（`M5-36A-*` 14 件 + `REVIEW-M5-36A-blind 39d1d248/9,143`）+ 预登记 `PREREG-M5-JUDGE-v2 6c77b56f/35,739`；口径：**装置可用 + 判据层 1 类阻塞缺陷（judge_defect 两层），不写“试跑通过”，(c) 未做** |
| 2026-10-26（task-67 附） | **漂移告警**：`m7/out/M7-E3-GPU.json` 于 10:04:52 被重跑覆盖 → 现盘 `3011c9ec93eb4235`/30,592（原 §13.16 引用 `e6b03da6f75cb851`/30,561）；本表随盘更新，**§13.16 已签读数不改写**，需 lead 裁定是否补记新跑 |
| 2026-10-26（task-70） | 新增 §13.20 批（`M6B-B1-FIX f3763553/23,027`、`M6B-DURABILITY 7747655b/3,505`、`M6B-FS-KILL-FUZZ 958d58a9/19,674`、`M6B-B1-SCRATCH 9788dad6/1,150`、baseline `f9ddccf5/845`、`M7-E3-CPU-B1 07eb446d/3,315`、`LANDED-m7-e3-gpu-b1rev aef342f1/4,702`、`LANDED-m6b-b1 155779f4/22,699`、审计 `47094ac4/14,106`）+ §13.23 批（`m5_ground_v2 5e11e1ac/66,413`、`M5-JUDGE-v2-regression 205a61dc/193,316`、`LANDED-m5-judge-v2 8bb5e4de/11,068`、审计 `29c87901/11,946`）；`M7-E3-GPU.json` 现行为 `5493d3ca/31,688` |
| 2026-10-26（task-75） | 新增 §13.24 (c) 批 9 件（`M5C-36-*`：r1 `c3b8c062/317,123`、adj `0d882f20/60,432`、review `3666cf58/87,811`、judge `9c2d2be5/261,594`、alignment `aaed0822/245,640`、resume `479683b5/19,640,216`、cand-raw、attempt1）+ 预登记 `PREREG-M5-C 250dbb41/14,071` + 裁决 `60fedd7d/10,023` + 旧预登记 `32bb07a0` 标 superseded；§13.25 批 10 件（K1 夹具四件、`M5-K1-DRYRUN 2507a2a5/29,461`、io-microbench `66577f63/227,945`、脚本两件、attempt1、park-result）+ 预登记 `PREREG-KILL-ARM-v2 42434b91/18,253` |
| 2026-10-26（task-75 附） | **漂移告警**：`INSPECTOR-M5-JUDGE-V2-AUDIT.md` 于 11:16 后重出 → 现盘 `9b453349ab719d2a`/18,046（原 §13.23 引用 `29c87901`/11,946）；结论不变（可签限定，坐标已替换为 `5e11e1ac/205a61dc/8bb5e4de`），§13.23 已加一行补记 |
| 2026-10-26（事故留痕） | **INDEX 覆盖事故**：`docs/_work/INDEX.md` 由 **`full:C22` git 对象恢复**（`44941f18ef260035`/25,431 B），task-75 增量重做；**根因 = 脚本写目标混用**（PROGRESS 缓冲被写入 INDEX 路径）；PROGRESS / ARTIFACTS-KEY 未受影响 |
| 2026-10-26（task-77） | 新增判据预登记 `PREREG-M5-JUDGE-v2.2 `fdf7ca2ae939a3a4/9,351（§13.26，先立不实现）；口径：**方向反转=句级每个可核成分各自被覆盖**、**(c) 为 in-sample 不进验收**、**伪改善预声明须双率并列**、v2.1 冻结 |
| 2026-10-26（task-78） | 新增 §13.27 K1 九变体件（`M5-K1-WARMUP a23abaf2/15,752`、`WARMUP-SETTLE 2ed0e413/28,145`、`WARMUP-1MIB 020be5a9/4,969`、`SLEEP-S1 08ca4d70/9,219`、`FSYNC-B1 26352059/9,922`、`FSYNC-B3 9a417c78/9,503`、`STALL-LOCATE 007ba7b2/138,990`、`STALL-MECH 81af2798/414,827`、`UNATTACHED dff70c07/5,938`）+ `_k1_park_child.pre-instrument 93391078/24,243`；`_k1_park_child.py` 现盘更新为 `acc8f4fd/39,224`（fsync-every 版）。 |
| 2026-10-26（task-78 附） | 新增 §13.28 判据版本链四件（`PREREG-M5-JUDGE-v2.3 5a3f12f2/10,394`、`m5_ground_v2_2 ae5ceea9/36,005`、`M5-JUDGE-v2.2-INSAMPLE-REPLAY 29a9498f/211,198`、`_v22_selftest f1b061dd/3,948`）；**version-chain 口径**：v2.2 = 已实现 `not_adopted`（抓 18/18、误伤 41/64），**不得写成已否决判据或已验证**；v2.3 = 预登记未实现；对外 README 不列版本号。 |
| 2026-10-26（task-81） | 新增 §13.29 三件（`m5_ground_v2_3 cc03e48c/44,209`、`M5-JUDGE-v2.3-INSAMPLE-REPLAY fb4045af/223,401`、`_v23_selftest e238d140/4,462`）；口径：`design_accepted_in_sample=true` **≠ 判据有效**、`(c)` 为其样本内、有效性须 (b) 层新样本外集（未做）；冻结源件 v2.1/v2.2/预登记跑前跑后未动。 |
| 2026-10-26（task-81 补） | 追加 §13.29 两件旁证（`_v23_regression_stdout e234b273/3,233`、`_v23_diagnose_stdout 861d5bb1/965`）；AK 178→180，**INDEX 不加非文档行**（lead 裁定：`kvmem/` 产物只由 AK 承载）。 |
| 2026-10-26（task-84） | 新增 §13.30 十六件 = 两预登记（`PREREG-M5-B 8102950d/12,053`、`PREREG-M5-B2 482a9482/12,695`）+ 裁定散文版（`df1ae09c/5,627`）+ b rev1 四件（批次/夹具/GEN/JUDGE）+ b2 八件（夹具/GEN/pre-repair/JUDGE/句表/ADJ/REVIEW/RATES `9ac66b6d/11,407`）+ 裁决件（`65a2124b/4,192`）；口径：**(b2) = 未通过**（漏判 40.00%），旧中间字节作废。 |
| 2026-10-26（task-86） | 新增 §13.31 六件（`PREREG-M5-B3-v2.4 37e3742c/5,320`、`PREREG-M5-C2-SEMANTIC 4fc88948/7,115`、`m5_ground_v2_4 1387b851/44,286`、`_m5b3_selftest_v24 08e6e92c/4,467`、`M5B3-v24-RATES 3d5f5907/12,830`、`_m5b3_v23_v24.diff 19c62687/1,591`）；口径：**口径更正、能力不变**（漏判仍 40.00%），C2 路线待拍板。 |
| 2026-10-26（b4 收敛） | 新增 §13.32 二十件 + 前序三件 = 23：B4 预登记/B2EVAL/REV5/REV4.1/REV4/ORDER/FLOOR-REV2/FLOOR/SPEC 九件文档 + b4 产物十一件（GEN/句表/两盲标/金标当前版/JUDGE/RATES/RATES.md/AB×2/AUDIT）+ 前序三件（REV5-OFFLINE/REV5-1-OFFLINE/B2EVAL）；口径：**(b4) = `pass=false`**、A/B Δ 不显著、口径两读并列；金标当前版 `9273ebc9/13,195`（首版已被替换）。 |
| 2026-10-27（b5 验收） | 新增 **D 批 9 件**（`M5C2-B5-VERDICT fa93b38c/4,922`、pin `906d9fcc/842`、GEN `2b63a024/68,184`、SENTENCES `ba92635c/116,566`、GOLD `54aa3da5/64,148`、EXTRACT `93505eec/444,613`、DECIDE `59da64cb/741,080`、AUDIT `f72d267e/109,477`、RATES `aae1b790/75,582`）；口径：**b5 = 擦边**（H1：误判 9/72=12.50%、Wilson 上界 22.08%>15%；漏判 0/29、上界 11.70%；三套 gold 一致），**禁写「通过」「未通过」**，唯一来源 VERDICT `fa93b38c`（初版 7622f585/4,500 已被 00:12 corrections 取代；PROGRESS §13.34）。 |
| 2026-10-27（b7′ 开跑） | 新增 **E 批 14 件**（QUESTIONS `f1f05953/15,964`、qpin `1baeda85/1,697`、GEN `041b51eb/140,514`、SENTS `c5a49a69/288,805`、spin `60b369bf/1,317`、BLIND-A `50d1b6da/37,632`、BLIND-B `d8e51d65/40,023`、GOLD `d5726d9c/110,099`、gpin `df72edea/832`、HOSTGATE `bdd354bf/2,284`、ATTEMPTS `c08f6007/2,596`、SCRIPTS-FREEZE `558fd9aa/3,629`、READINGS-FREEZE `e210aa11/1,512`、WIDE-SENSITIVITY `5e5555f9/1,577` 占位）；口径：b7′ = rev7.2 首测（75 题/623 句，gold 147/63），**DECIDE/WIDE/READINGS 未出 ⇒ 不写结论**；EXTRACT/DECIDE/READINGS 待落盘补行（PROGRESS §13.35）。 |
| 2026-10-27（b7′ GOLD v2） | GOLD 由 v1 `3afddd2446e621f8/109,291` 更新为 **v2 `d5726d9cc59bb6f6/110,099`**（pin `19a6a653/1,249`）；**改判 1 条** `b7-s4-q3-s07` no_fact→support_present（独立复核 `f8aa4bfb` 采纳）；新计数 support 148 / fabricated 63，预置线 FP ≤13/148=8.78%、漏判 ≤6/63=9.52%；v1 保留追溯。 |
| 2026-10-27（b7′ 判定） | 新增 **15 件** = VERDICT `1cb7a796/4,165`+pin `686f0ac9/586`、READINGS `15190c2e/15,100`、READINGS-AUDIT `97e28543/18,240`、DECIDE `adaf0104/1,863,426`、EXTRACT `2804fbbb/951,539`、PROVENANCE-V2 `96cd4bfe/13,992`、INVARIANCE20 `a1d928df/8,549`、MERGE-CHECK `6aceb95c/7,415`、GOLD-REVIEW `f8aa4bfb/5,461`、INSPECTOR `9de882c8/17,015`、INSPECTOR-S5 `9d838e56/15,753`、EXTRACT-NOTES `73118d5d/3,804`、EXTRACT-RESUME-SCRIPT-FREEZE `19f1e9d2/1,877`、PROVENANCE-FIX-SCRIPT-FREEZE `ae3b9ddc/1,030`；并更新 ATTEMPTS→`8398324f/13,614`、READINGS-FREEZE→`529915a6/2,147`、WIDE-SENSITIVITY 占位→正式 `3e46633a/854,236`。口径：**b7′ = 擦边（两读一致；A 窄 22/147、10/62）**，b5 擦边/b6 未接上/b7 擦边 ⇒ R10 终止；不得写「通过」。 |
| 2026-10-27（b7′ headline 口径升级） | 新增 SUPPLEMENT `5046d1c0/3,070`（headline 三句、operating point 四行、可达界 12.70%、layer0 两版、禁语、terminal_reason）；MERGE-CHECK 引用改 v2 `b599a62d/15,741`（59/59、C1/C2/C3 齐全；旧 `6aceb95c` 作废）；口径：**判据操作点超 H1 可达界 ⇒ 当前设计下不可达标（非样本量问题）**，b5 永久降 dev；不写结论升级、INSPECTOR-S5 待 v2。 |
| 2026-10-27（b7′ 引用终值） | MERGE-CHECK → **v3 `6048139a/17,060`**（59/59、C1/C2/C3、falsifiability 3/3 fail_detected）；INSPECTOR-S5 → **v2 `ee0abc1c/15,341`**（①–④ pass、overall pass、无阻断，D1–D6 非阻断 caveat）；SUPPLEMENT → **v2 `a58c3c87/3,871`**（v1 `5046d1c0` 作废追溯）；新增 `docs/_work/B7-FINAL-REPORT.md 9b0ed2d3/5,294`（三数据集总表/可达界/证据链/披露/负结果价值/下一步两条）。口径不变：b7′ = 擦边，判据操作点超可达界 ⇒ 当前设计不可达标（非样本量），R10 终止。 |
| 2026-10-27（C 版 v1.1 回归） | 新增 **F 批 2 件**（产品证据，不入研究链）：`C-V1-1-REGRESSION.json 611fc849/6,084`、外钉 `C-V1-1-REGRESSION-FREEZE.json d2fe383c/878`；口径：v1.1 回归通过（real_engine、4/4 检索、rollover、长回答 328 字/23.45 s、日志 verify rc=0），**不得进入研究线引用链/不参与 b5/b6/b7 判定**。 |