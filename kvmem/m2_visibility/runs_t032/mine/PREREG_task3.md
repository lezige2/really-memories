# T-031 任务 3 预登记（掩码偏置探针）—— 在任何阶梯运行之前写死

## 探针（引擎侧，llama.cpp/src/llama-kv-cache.cpp 的 set_input_kq_mask_impl）

- 环境变量 `LLAMA_KV_MASK_BIAS="lo:hi:b"`，未设 ⇒ 行为完全不变（解析块只在 env 非空时生效）。
- 只对**位置在 [lo,hi] 内、且值恰为 mask_keep** 的格加 b；位置取自 `cells.pos_get(j2)`（真实 cell），
  不使用行号；被 mask_drop 的格永不改动；空 cell（无位置）跳过。
- 每次 mask 构建打一行 `[MASKBIAS] lo=.. hi=.. b=.. n_cells_touched=.. type=..`，
  n_cells_touched 是该次调用内真实写入的格数（多行 ubatch 时按 (行,格) 计）。
- home 在本构型占位置 4075..4095（21 格）。

## 验收（先做，做不过就不做阶梯）

1. 不设 env：iso_dup4 问 home，answer sha16 必须 == **7ec1430d972d949e**（回归基线）。
2. `LLAMA_KV_MASK_BIAS=4075:4095:0.0`：与不设时答案**逐字节相同**（证明路径无副作用）。
3. `build-vulkan/src/libllama.a` mtime 必须变化（证明真编了）。已记录：1792855433.698493 → 需新的值。

## 阶梯（iso_car_back 问 home，home 在该构型下失败）

b = 1 / 2 / 4，各跑一次，env 固定 `4075:4095:<b>`。

## 预登记结论分支（先写死）

- **某一档开始答对（ok=True）** ⇒ 信息在场且可达，只是注意力没落上去（分配问题）。
- **全档都答错** ⇒ 问题在更上游（编码/读出），不在注意力分配。

## 已知副作用（必须写进结论，不是缺陷）

- b ≠ 0 时 Vulkan 的 mask_opt 快路径失效（该快路径只对全 0 / 全 -inf 的掩码成立），
  **变慢是预期的**，不是新发现；每条运行的 elapsed 一并记录。

## 并发污染检查（本次特有）

- 若一次 mask 构建出现**两行** [MASKBIAS]，说明源文件被第二个写者又插了一段同逻辑
  （偏置会被叠加成 2b）⇒ 该次数据作废，必须在产物里写明。
