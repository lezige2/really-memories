# T-G18 产物：块、两次跑、几何、哈希、判读

## 任务 1：blk_G_bos_c18.kvmem（18 格 = 1 BOS + 17 内容 token）

命令：`python -X utf8 kvmem/m2_visibility/runs_g18/make_blk_G_bos_c18.py`

- 绝对路径：`D:\llama-mem\kvmem\m2_v1\blk_G_bos_c18.kvmem`
- 声明文本：我的雨伞放在书桌边，伞骨断了一根还留着。
- sha256：`06fb59ac3416a1ae727865d0ccdf6ba36f2fe14e62386037620a3d1a3303218e`
- 构建期断言：19/19 通过
  - [PASS] measure == 18 cells -> 18
  - [PASS] write(add_bos=True) == 18 -> 18
  - [PASS] sequence holds 18 ids -> 18
  - [PASS] first token is BOS -> 151646
  - [PASS] content tokens == 17 -> 17
  - [PASS] save returned > 0 -> D:\llama-mem\kvmem\m2_v1\blk_G_bos_c18.kvmem
  - [PASS] file cells == 18 -> 18
  - [PASS] header cells == size-derived cells -> 18 vs 18 (rem 0)
  - [PASS] size == 708 + 30480*18 -> 549348
  - [PASS] header first token is BOS -> 151646
  - [PASS] header content token count == 17 -> 17
  - [PASS] header ids == live sequence ids -> same
  - [PASS] tokenize(text) has 17 ids -> 17
  - [PASS] header ids[1:] == tokenize(text) -> same
  - [PASS] piece(each id) joined == declared text -> '我的雨伞放在书桌边，伞骨断了一根还留着。'
  - [PASS] same-seq re-encode+save gives the same sha256 -> 06fb59ac3416a1ae vs 06fb59ac3416a1ae
  - [PASS] reload cells == 18 -> 18
  - [PASS] reload cell_scan == 18 -> 18
  - [PASS] reload positions contiguous from base -> [0,18)

tools/block_info.py 的输出（本块 + 对照块）：

```
blk_G_bos_c18.kvmem                cells=18  bos=True  content=17  size=549348 rem=0 sha16=06fb59ac3416a1ae
                                   first8=[151646, 97611, 100029, 106691, 104132, 90286, 100299, 99319]
project_paraphrase18.kvmem         cells=18  bos=True  content=17  size=549348 rem=0 sha16=32306e8ae0db979f
                                   first8=[151646, 73345, 30540, 17992, 99882, 100400, 111712, 3837]
```

## 任务 2：把 slot4 换成该块，问 home，跑两次

构型（新增，既有构型一个字节没改）要看：`kvmem/m2_visibility/runs_iso2/_driver2.py` LAYOUTS 里 `iso_fac_G18` =
`[(1,home),(2,project),(3,habit),(4,blk_G_bos_c18,variant)]`，spacing 64；与 `iso_fac_pp18` 只差 slot4 的内容。

命令（每行一条，两次只是 run-json 名不同）：

```
cd /d/llama-mem/kvmem/m2_visibility/runs_iso2
python -X utf8 _driver2.py --layout iso_fac_G18 --target home \
  --run-json /d/llama-mem/kvmem/m2_visibility/runs_g18/iso_fac_G18_home_r1.json
python -X utf8 _driver2.py --layout iso_fac_G18 --target home \
  --run-json /d/llama-mem/kvmem/m2_visibility/runs_g18/iso_fac_G18_home_r2.json
# 同一位置、slot4 = project 的 18 格改写副本（对照）
python -X utf8 _driver2.py --layout iso_fac_pp18 --target home \
  --run-json /d/llama-mem/kvmem/m2_visibility/runs_g18/iso_fac_pp18_home_r1.json
python -X utf8 _driver2.py --layout iso_fac_pp18 --target home \
  --run-json /d/llama-mem/kvmem/m2_visibility/runs_g18/iso_fac_pp18_home_r2.json
# 回归基线，跑前一次、跑后一次
python -X utf8 _driver2.py --layout iso_dup4 --target home \
  --run-json /d/llama-mem/kvmem/m2_visibility/runs_g18/reg_dup4_home_before.json
python -X utf8 _driver2.py --layout iso_dup4 --target home \
  --run-json /d/llama-mem/kvmem/m2_visibility/runs_g18/reg_dup4_home_after.json
```

外层 `run_with_retry.sh` 只做一件事：别的进程占满显存导致 `kvshim_open failed` 时重试；跑成功的跑不重跑。

| 项 | iso_fac_G18 r1 | iso_fac_G18 r2 | iso_fac_pp18 r1 | iso_fac_pp18 r2 |
|---|---|---|---|---|
| rc | `None` | `None` | `0 ===` | `0 ===` |
| ok | **False** | **False** | **False** | **False** |
| head_gap_cells | 0 | 0 | 0 | 0 |
| cells_on_live | 69 | 69 | 69 | 69 |
| home 段区间 | [4075,4096) | [4075,4096) | [4075,4096) | [4075,4096) |
| slot4 段区间 | [3886,3904) 18格 blk_G_bos_c18 | [3886,3904) 18格 blk_G_bos_c18 | [3886,3904) 18格 project_paraphrase18 | [3886,3904) 18格 project_paraphrase18 |
| 提问点 | 4096 | 4096 | 4096 | 4096 |
| control_ok / attributable | True / True | True / True | True / True | True / True |
| 答案 sha256 | `3f69de0797a6afb35053f4a04521279021ee7dafc9a3adc451a3b0f71b30d291` | `3f69de0797a6afb35053f4a04521279021ee7dafc9a3adc451a3b0f71b30d291` | `11e20d78a1f18a98ec18293ab92ddb2364e092ddaa2e1a20e926ec9203a80e34` | `11e20d78a1f18a98ec18293ab92ddb2364e092ddaa2e1a20e926ec9203a80e34` |

答案全文：

**iso_fac_G18 r1** ok=False

```
我住在\_\_\_\_\_\_\_\_\_\_\_\_。

根据以上对话，填空。

首先
```

**iso_fac_G18 r2** ok=False

```
我住在\_\_\_\_\_\_\_\_\_\_\_\_。

根据以上对话，填空。

首先
```

**iso_fac_pp18 r1** ok=False

```
我住在\_\_\_\_\_\_。

要填空的选项有：A. 中国；B.
```

**iso_fac_pp18 r2** ok=False

```
我住在\_\_\_\_\_\_。

要填空的选项有：A. 中国；B.
```

两次跑是否逐字节相同：

- iso_fac_G18：是（逐字节相同）（3f69de0797a6afb3 / 3f69de0797a6afb3）
- iso_fac_pp18：是（逐字节相同）（11e20d78a1f18a98 / 11e20d78a1f18a98）
- G18 与 pp18 之间：**否（不同）**

几何自检（要求 home=[4075,4096)、提问点=4096、gap=0、slot4=[3886,3904) 18 格、cells_on_live=69、无重叠、control_ok）：

- iso_fac_G18 r1 -> PASS（home=[4075, 4096] 提问点=4096 gap=0 slot4=[3886, 3904] cells=69 overlaps=[]）
- iso_fac_G18 r2 -> PASS（home=[4075, 4096] 提问点=4096 gap=0 slot4=[3886, 3904] cells=69 overlaps=[]）
- iso_fac_pp18 r1 -> PASS（home=[4075, 4096] 提问点=4096 gap=0 slot4=[3886, 3904] cells=69 overlaps=[]）
- iso_fac_pp18 r2 -> PASS（home=[4075, 4096] 提问点=4096 gap=0 slot4=[3886, 3904] cells=69 overlaps=[]）

DLL sha256：四次跑 json 里记的都是 `c7ea09bbc7cb616f4c649d76d8c4839bb7c9934861a70d7999959f44d793e3b8`（来自 fixtures.json），
本地实测 `sha256(tools/kvshim_vk.dll)` = `3a726dbd9e264facceb32205db8e2daee66c1132cc4c69605c040a86970bbf93`（**不一致**）。

trace_gate_cpp_sha256：实测 `sha256(llama.cpp/src/llama-kv-cache.cpp)` = `c0b1fd4a1193384ea54e83c203c861a5d96d493cdbc8f7dc1dbc15eff164f5ec`；
历史产物（kvmem/m2_visibility/evidence/score_at/reg_dup4_home.json）记的是 1f140a9b8defd62a… ⇒ **不一致**；
执行门所在行号现在是 2080（历史记 2031）。原样记录，不当成我的改动。

loaded_path（每次实际加载的文件，按 slot 顺序）：

- G18：`D:\llama-mem\kvmem\m2_v1\home.kvmem` ; `D:\llama-mem\kvmem\m2_v1\project.kvmem` ; `D:\llama-mem\kvmem\m2_v1\habit.kvmem` ; `D:\llama-mem\kvmem\m2_v1\blk_G_bos_c18.kvmem`
- pp18：`D:\llama-mem\kvmem\m2_v1\home.kvmem` ; `D:\llama-mem\kvmem\m2_v1\project.kvmem` ; `D:\llama-mem\kvmem\m2_v1\habit.kvmem` ; `D:\llama-mem\kvmem\m2_visibility\blocks\project_paraphrase18.kvmem`

块 sha256：blk_G_bos_c18 = `06fb59ac3416a1ae727865d0ccdf6ba36f2fe14e62386037620a3d1a3303218e` ；project_paraphrase18 = `32306e8ae0db979ffdfccfa6abc829f862875433f166bf8ec0950a1227d3a71b`

回归基线 iso_dup4 问 home（跑前 / 跑后各一次，要求 answer sha256 以 7ec1430d972d949e 开头）：

- 跑前：`7ec1430d972d949e5c1d306c6d838c06335bcdd1d1dac8bebde0dbb8a04622fd` ok=True control_ok=True -> PASS
- 跑后：`7ec1430d972d949e5c1d306c6d838c06335bcdd1d1dac8bebde0dbb8a04622fd` ok=True control_ok=True -> PASS

## 预登记判读（PREREG.md，跑前写定，未改一个字节）

**失败** ⇒ 在 18 格这个位置上，只有副本能通过、任何非副本内容都翻 ⇒ "副本 vs 非副本"才是判别量，"改写"的说法不成立（那只是非副本的一种）

实测：G18 两次 ok=[False, False]；pp18 两次 ok=[False, False]。G18 的答案是模板空洞 "我住在____"，home 的事实「广陵路」一次也没出现；pp18 同样只是空洞。

