# M18-3 规格作废记录（lead 2026-10-25T19:40+08:00 裁）

**结论**：`M1.8-CONFLICTS-inspector.md` §2.2 的 M18-3 两条改法与 §3 的 A9、以及真实库探针 P2 **在数值上不可同时成立** ⇒ 规格作废，两种变体补丁留档但**不作数**（`invalidates`）。lead 不接受 A、也不接受 B，不许悄悄改 A9 或 P2 的期望。M18-3 由 inspector 重出规格（方向：例外按「命中的罕见字属于所问属性的词表」放行，而非「命中 1 个罕见字」）。

## 变体 A（照 §2.2 字面两条全改）
`active = (rare + bigrams) if used_fallback else (bigrams + unigrams)` + `need = 2`

- 补丁：`evidence/M18-3-literal-cov+need2.patch`
- 产物：`out/M18-A-after-M18-3.json`（A9 红）
- 算式（`我几点睡觉` vs 块 `12点半 睡。`，10 篇库）：
  - rare = `[u:点, u:睡]`（df=1，n_docs=10）⇒ idf 各 = log(1+9.5/1.5) ≈ **1.99**，分子 = 3.98
  - 缺失 bigram 4 个（我几/几点/点睡/睡觉），idf_absent = log(1+10.5/0.5) ≈ **3.09** ⇒ 分母 = 3.98 + 12.36 = 16.34
  - **cov = 3.98/16.34 = 0.24 < COV_MIN 0.35** ⇒ 块在 `retrieval.py:299` 被 `continue` 掉
- ⇒ 与 §3 A9「`我几点睡觉` 必须仍返回该块（回退的原始动机）」直接冲突。

## 变体 B（只改 `need = 2`）
- 补丁：`evidence/M18-3-need2-only.patch`
- 产物：`out/M18-A-after-M18-3b.json`（A8/A9 双绿，10/11）、`out/M18-CMP-step3-vs-step2.json`（**P2 worse**）
- 机理：`need = 1 if (allowed is not None and len(allowed) <= 2) else 2` 那条例外，经 **M18-1** 收窄 `allowed` 后正是真实库 P2「我的住址是什么」的承重件 ——
  P2 的 `allowed=[3,5]`（2 块），回退只能命中 1 个罕见字 `u:住`，靠例外才被放行到块 5；删掉例外 ⇒ P2 从块 5 退回 ABSTAIN。
- ⇒ 与真实库不变量「8 条探针任一变差即停」冲突（逐步比较 worse=1）。

## 状态
- `M18-3`：**landed=false**，`invalidated=true`；在此状态前一切「M1.8 四步全落」的说法都不成立。
- 等 inspector 新规格（会带 A-断言与反例），届时再跑一次并记 `invalidates`。
