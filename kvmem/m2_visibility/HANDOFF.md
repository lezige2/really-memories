# 对接文稿（换对话前必读）

生成：2026-10-25 凌晨 ｜ 分支 main ｜ 工作树 D:\llama-mem
上一段工作的完整报告在同目录 `NIGHT-REPORT.md`；台账 `E10-NEXT2.md`（约 3200 行，检测员维护）。

---

## 0. 一句话交接

**做的是什么**：这个仓库是 llama.cpp 的一个分支，把"长期记忆"存成**常驻在注意力里的 KV 张量**（不是提示词文本）。
把记忆块（`.kvmem`）按位置铺进 KV 缓存，再在紧贴其后提问，让模型"像记得一样"回答。

**现在到哪了**：4 个干净观测点组成一张 2×2 表（见 §1），结论是**"近似重复只在满载时致命"**；
掩码偏置探针证明**信息在场且可达，只差半个对数单位**；下一步要换 14B 验证规模假设（见 §6）。

---

## 1. 当前唯一可靠的核心结果（2×2，同一把尺子）

```
                     69 格（habit 在场）        57 格（habit 缺席）
第4块 = 项目副本      过  (E)                    过  (X1)
第4块 = 项目改写      败  (F)                    过  (B57)
```

四点位置完全相同：home `[4075,4096)`、project `[4014,4032)`、第4块 `[3886,3904)`。
各点 2–4 次独立跑，答案逐字节相同。

**读法（不许再简化）**：
- 副本两格都过 ⇒ "副本 vs 改写"**单独**不成立；
- 改写只在 69 格败 ⇒ "总格数"**单独**不成立；
- **两者交互：近似重复只在满载时失效。**

**失败形态**（机器判定，顺序不许换）：
1 `fact_ok` → none ｜ 2 空串 ｜ 3 复述提问 ｜ 4 改写成填空模板 ｜ 5 拒答 ｜ 6 编造具体值 ｜ 7 其他。
实测出现过：改写成模板（F）、编造具体值（换掉 home 内容时答"杭州西湖边"）。

---

## 2. 掩码偏置探针（已实现并跑完）

环境变量：`LLAMA_KV_MASK_BIAS="lo:hi:b"` —— 给真实位置落在 `[lo,hi]` 的允许格加 `+b`。

| b | iso_fac_pp18 | iso_car_back |
|---|---|---|
| 不设 / 0 | 败（填不出） | 败（答"杭州市拱墅区"） |
| 0.5 | **过** | 未测 |
| 1 | 过 | **过** |
| 2 | 过 | **过**（直答事实串） |
| 4 / 8 | 无结论 | 无结论 |

**b≥4 无效的真实原因是：偏置窗口同时命中了控制臂**（控制文本也占 4075..4095），
控制臂退化成复读，driver 门禁拒判。**不是"注意力过头"。**

三条口径（必须一起继承，否则会被读歪）：
1. +b 成功只证明**信息在场且可达**，它是**测量工具，不是修复方案**；
2. 窗口 0.5–2 是**这个构型这个尺度上**的窗口，不许写成"注意力差 0.5"；
3. **偏置非单调有益**，任何"再加大点试试"都是错的。

---

## 3. 已确凿的其他事实

| # | 事实 | 备注 |
|---|---|---|
| 1 | 提问点必须紧贴被问块的末格 +1（`gap==0`），否则 `rc=-1`、空答、**无任何诊断** | |
| 2 | 单块构型下记忆能被正确读出 | |
| 3 | 把被问的 home 内容换成无关事实 ⇒ 答错且**编造具体值** | |
| 4 | 12 格 @3892 位置上，副本与两种不同改写产出**逐字节相同**的答案 ⇒ 该位置对内容不敏感 | 2 份块 × 2 跑 |
| 5 | 对数似然差 Δ 与"是否采纳"**反号** ⇒ 该指标作废 | Δ 比 0.973 |
| 6 | 块 = 708 字节头 + 30480 字节/格；`30480` 是 **7B + q8_0** 的每 token 尺寸 | 见 §5 换模型的后果 |

---

## 4. 已撤回（都是我撤的，别再拿出来用）

| 撤回 | 理由 |
|---|---|
| "跨长度复现：副本过改写败" | 12 格位置上**副本也败**，且逐字节相同 |
| "副本类都过" | 12 格那次放的正是副本 |
| "位置分档 3886 能用" | delta 与 cells 在同一布局是同一个数；打包规则不一；非单调；0 对对照 + 1 反例 |
| "Δ 能衡量采纳" | 与采纳反号 |
| "project 与其改写共存才致命" | B57 里两者都在场却过 |
| "不是内容，是容量" | E vs F 同 69 格结局相反 |

**根因是一条**：每次都是**一对对照里差异字段数 > 1，却写成了单因子结论**。
**可操作检查：读任何一对对照，先把两边不同的字段全列出来，数一数；>1 就不许下单因子结论。**

---

## 5. 环境与操作手册（照抄可用）

### 路径
```
仓库        D:\llama-mem          （bash 里 /d/llama-mem）
模型 7B     D:\models\DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf
模型 14B    D:\models\DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf   （见 §6，可能未下完）
DLL         D:\llama-mem\tools\kvshim_vk.dll     ← 只有这一个位置！
            build-vulkan\bin\kvshim_vk.dll **不存在**，别去那儿找
块           kvmem\m2_v1\*.kvmem ｜ kvmem\m2_visibility\blocks\（只读，别再写）
夹具         kvmem\m2_visibility\fixtures.json   ← 里面的 dll_sha256 是**陈旧的常量**，别当实测
驱动         kvmem\m2_visibility\runs_iso2\_driver2.py（已改为实测 DLL sha）
             runs_t032\_driver3.py ｜ runs_t033\_driver4.py ｜ _driver5.py ｜ runs_t033\_driver7.py
构建树       D:\llama-mem\build-vulkan
```

### 编译（两步，缺一不可）
```bash
cd /d/llama-mem && cmake --build build-vulkan --target llama          # 必须先编库
cd /d/llama-mem && powershell -NoProfile -ExecutionPolicy Bypass -File "D:/llama-mem/tools/build_tools.ps1" -Gpu -Dll -Only kvshim
```
**坑 1**：`-File` 后面必须用**正斜杠**，反斜杠会被 bash 吃掉（`D:llama-memtoolsbuild_tools.ps1`）。
**坑 2**：只跑 ps1 等于没编（它只链接）。验收看 `build-vulkan/src/libllama.a` 的 mtime 是否变化。
**坑 3**：DLL 被任何进程映射时链接会失败（`ld.lld: Permission denied`）。判断方法：
```python
import os; os.rename(p, p+".t"); os.rename(p+".t", p)   # PermissionError = 有人持有
```
按 errno 分开处理：`FileNotFoundError` = 路径错（改路径）；`PermissionError` = 被占用（等，别重编）。

### 跑一次臂
```bash
cd /d/llama-mem/kvmem/m2_visibility/runs_iso2 && python -X utf8 _driver2.py --layout iso_dup4 --target home --run-json ../out.json
cd /d/llama-mem/kvmem/m2_visibility/runs_t033 && python -X utf8 _driver7.py --run-json ../out.json     # X1（57 格副本）
LLAMA_KV_MASK_BIAS="4075:4096:0.5" python -X utf8 _driver2.py --layout iso_fac_pp18 --target home --run-json ../b05.json
```

### 别踩的坑
- `sha256sum` 不存在，用 `python -X utf8 -c "import hashlib..."`。
- 读 json 前先 `print(sorted(d.keys()))`，别猜键名。
- **同名不同源今晚出现 5 次**（B / habit 改写 / DLL / cells / 位置）；引用前先报 sha。
- 块的"三件套"：**cells ｜ 首 token 是否 BOS ｜ 内容 token 数**。缺一不许引用。
  home 21 格 = 1 BOS + 20 内容；我们自造的 21 格块若不含 BOS，结构就不同。
- `tools/block_info.py` 是零引擎头解析器（毫秒级），但**不能**核 model/rope/type 这些编码配置。
- 不要并发跑多个引擎：显存会爆（`ggml_vulkan: ErrorOutOfDeviceMemory`），DLL 也会被占。
  **同一时刻只允许一个执行者。**

---

## 6. 换 14B：先说清代价

**KV 张量是模型专属的。** 每 token 尺寸 `30480 = 708 头 + (28 层 × 4 kv head × 128 维 × 2(K/V) ≈ 28672 元素) × q8_0(~1.0625 B) + 余量`。
14B（Qwen2.5-14B：48 层 × 8 kv head × 128 维）每 token 约 **104 KB**，与 7B **完全不兼容**。

⇒ **换模型 = 所有 `.kvmem` 块全部作废，必须用 14B 重新编码一遍。**
⇒ 换之前必须做的：
1. 改 `kvmem/m2_visibility/m2_visibility_probe.py:85` 的 `MODEL` 常量（或加环境变量）；
2. 用 14B 重建 home / project / habit / pp18 / project 副本 这几块，**保持同一段文本**；
   造块脚本参照 `tools/t031_habit_para.py`、`kvmem/m2_visibility/make_t032_blocks.py`（都带断言）；
3. 新块的"三件套"必须重新登记（BOS 口径、内容 token 数会随分词器变）；
4. 位置 `[4075,4096)` 等是**按 4096 的 CHAT 算的**，与模型无关，可沿用——但要重建后核对。

**14B 下载状态**：后台任务 `win-bash-02eb61bd8efd4e4f`，
脚本 `tools/dl_14b_par.py`（8 路 Range 并行，源 `hf-mirror.com`，落 `D:\models\*.dl` 完成后改名）。
测速：源站 ~0.5 MB/s，镜像 ~8 MB/s。断了就重跑该脚本，它会复用已有 .dl。

---

## 7. 下一步（判据先定死，不许事后改）

### 主路径
```
用 14B 重建块 → 重跑 2×2 四格
  14B 上「69 格 + 改写」也过  ⇒ 规模/分配假设成立，7B 的这条线收工，写进 E10-NEXT2.md
  14B 上仍然败              ⇒ 不是规模问题，回到"关系结构"（精确重复 vs 近似重复）上查
```

### 备用（若 14B 短期下不来，可先做，成本低）
- `X0`：69 格里把第 4 块换成**与在场所有块都无关的 18 格真事实**（`m2_v1/G_bos_c18.kvmem` 已存在，18 格含 BOS）。
  过 ⇒ 只有"与在场块有关系"的内容才触发；败 ⇒ 任何第 4 块都不行。**2 跑，零新块，无需重编。**

### 不建议做（已判定为低信息）
- `habit → pet` 换块：12 格 @3892 已对内容不敏感，第三份内容大概率还是同一个答案。
- 继续加大偏置：b≥4 已被证明会打坏控制臂。

---

## 8. 协作纪律（今晚用血换的）

1. **同一时刻全场只允许一个执行者。** 冲突面不止目录：DLL 文件、引擎进程、同一个源文件。
2. **一个目录一个写者**，产物落各自的 `mine/` 子目录。
3. 简报里写的**每个数值都要自己先核**（今晚因简报写错 BOS 口径、块路径、cells 数各浪费过一轮）。
4. **引用接口要像引用数字一样小心**：`make()` / `how=="exact"` 都曾是我凭记忆编的。
5. **代理指标与目标反号时，越精确越有害**（Δ 就是）。
6. **实验无效 ≠ 假设被否证**。四词纪律：未检验 / 实验无效 / 未测出·欠功率 / 无效应。
7. **二进制没了的结论是故事，不是测量。** 跑出结论的 DLL 要立刻归档并复算 sha。
   （现状：产出 E/F 的 `c7ea09bb` 全盘已无副本 ⇒ 那批**不可复跑**；现行 DLL 是 `3a726dbd` 或更新。）
