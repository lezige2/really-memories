# SCALE-40K · C 交付报告（仅脚本 + 不占 GPU 的 dry-run）

日期：2026-10-29 · seed 40000 · 未加载模型 / 未建块 / 未调 8765 / 未改产品代码

## 1 脚本

| 文件 | 作用 |
|---|---|
| `out/scale40k_build.py` | 分层抽样 → 插独立 `dst/chat.db` → `KVEngine` → `ms.build_block`；`--dry-run` 只抽样与映射 |
| `out/scale40k_run.py` | 读 `dst/queries.jsonl` → POST `/ask` → recall@k / pass / 泄漏 / 拒答 / P50-P95 → `dst/RESULT.json`；`--check` 离线校验 |

```
python -X utf8 out/scale40k_build.py --n 20 --dst /tmp/scale20 --dry-run
python -X utf8 out/scale40k_build.py --n 20 --dst kvmem/scale40k/n20 [--force]
python -X utf8 out/scale40k_run.py  --dst kvmem/scale40k/n20 --check
python -X utf8 out/scale40k_run.py  --dst kvmem/scale40k/n20 --endpoint http://127.0.0.1:8765 --label n20-k2off
```

非 dry-run 顺序：按 position 升序 INSERT（`text_kind=human_memory, contains_model_turns=0`，
`created_at` 显式 override，绕过只禁 UPDATE 的触发器）→ 断言 `lastrowid == 计划 id` →
`KVEngine(model, n_ctx=32768, n_seq=8, gpu=28, kv="q8_0")` → 逐块
`build_block(..., kv_type="q8_0", seq=6)` → 写 `queries.jsonl` / `build.json`。

## 2 dry-run n=20（`DRYRUN-n20.json`）

- 抽样 id（20）：`b0006 b0017 b0025 b0027 b0028 b0044 b0052 b0070 b0077 b0086 b0087 b0099 b0114 b0130 b0138 b0139 b0152 b0169 b0182 b0183`
- kind：chain 8 / fact 9 / noise 3
- family：plate 1, company 1, phone 1, bank 1, meeting 1, seat 4, car_color 5, cat 1, dog 1, hometown 1, noise 3
- position 五分位：0 档 5、1 档 4、2 档 4、3 档 4、4 档 3
- 链：ch06(seat/沈越)、ch07(car_color/卢婷)，各 4 块完整
- 反序证据（D 的 `created_at` 早于 C、id 更大）：
  - ch06：A b0027→id4、B b0086→id10、C b0138→id15（15:00）、D b0182→id19（13:30）
  - ch07：A b0028→id5、B b0087→id11、C b0139→id16（15:00）、D b0183→id20（13:30）
- 查询映射：100 → 13 目标命中 + 2 空目标（不存在负例）= 15 问可跑，85 跳过；反序重映射 6 条
  （q081/082/096 → C id15、幽灵 D id19；q083/084/097 → C id16、幽灵 D id20）
- key facts：2/12（b0025、b0099）

## 3 预计建库

| n | 块数 | 链/事实/噪声 | 可跑查询 | 预计（3–9 s/块） |
|---|---|---|---|---|
| 20 | 20 | 8 / 9 / 3 | 15 | 1–3 min |
| 50 | 50 | 20 / 22 / 8 | 28 | 2–8 min |
| 100 | 100 | 40 / 45 / 15 | 56 | 5–15 min |

三档取同一优先级序列的前缀 → **互相嵌套**，退化斜率可比；反序链固定 ch06/ch07；链时间戳按
chain_id 固定（与 n 无关）。id 一律 = 1..N（插入序 = position 升序）。

## 4 关键发现（会影响 100 档 K2-on 判读）

1. **链 C 块原文无族关键词**（"再后来又换成…"），`k2_family.classify_row` 认不出族：
   10 条链里只有 company 的 C 可识别。已仅对 2 条反序链的 C 做 text override
   （补"座位号 / 车身颜色"前缀，任务允许 text override），dry-run 自检 4/4 同族。
2. **K2 只认内置 owner 词表，不认任意人名** → 同族块跨人合并。n=100 实测
   `q071 郑凯现在的车牌号` → kept=`b0184`（蒋川），recall=0。plate/company/phone 各有两条链，
   n=100 开 K2 会稳定互踩 → **K2-on 结论只宜对 bank/seat/car_color（单链族）下**，其余三族请 K2-off。
3. 反序链在 n=100 的 K2 解析实测：kept=C、hidden 含 D → k2 确实按 `created_at` 排序（族内可识别时）。
4. 会议类查询需日期槽：`q027 下周那个会` 无明确日期 → `resolve_family` 返回 None，K2 不介入（按回退算）。
5. 分层按族/位置，不强保 12 条 key facts：n=20 覆盖 2、n=100 覆盖 5。
6. 与 spec §4.2 "建 200 一次、子库切 DB 行" 的差异：本实现每档独立 DB+blocks
   （20/50/100 共 170 块）；若走共享块方案，`memory_block.path` 必须指向同一 blocks 目录。

## 5 自检（均未占 GPU）

- `py_compile` 两脚本通过；同参数两次 dry-run 的 `DRYRUN.json` 哈希一致（确定性）。
- 假 engine + stub `build_block` 跑通非 dry-run 全链路：20 行插入、`lastrowid==计划 id`、
  `created_at` 各异、C 前缀/hash 正确、13 个目标 id 全部存在；随后删除测试库。
- `scale40k_run.py --check` 对 20/50/100 均 `problems: none`。
- 指标层用 stub HTTP 验证：正常命中 → pass=1；模拟 K2 取幽灵 D → recall=0、leak=1、ghost_picked=6。