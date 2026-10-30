# S2 gate-free 端到端（诊断）

- 配置：8766、n200 只读副本（200 行）、`S2_GATE_OFF=1`、`VERIFIER_VERSION=v2.2`、K2 auto、`--event-date` off、单监听
- 探针：`out/S2-GATE-HELDOUT-20.jsonl`（10 target + 10 负例），每挂载各 1 次
- 输出：`out/S2-GATE-FREE-E2E.json`

## top4（唯一可测挂载）

| 指标 | 值 |
|---|---|
| target 在挂载中 | 7/10 |
| 答案含期望值 | 3/10 |
| 两者同时成立（recall） | **3/10 = 0.3** |
| 负例实质拒答 | 9/10 |
| 负例被当有依据回答 | **1/10**（H12） |

- H12「Wi-Fi 密码」→ 答「储物柜密码是 4821，别跟别人说。」：**4821 是库内块 191 的真实值**，属跨题串味而非凭空编造，但对负例而言仍是错误作答。
- target 失败主因：20 名同族猫互串（小杏/小柠），gate-free 把同类噪声一并挂载。

## top20（不可测）

- 每次 `/ask` 均 **HTTP 500 `OSError: access violation reading 0xFFFFFFFFFFFFFFFF`**（首次请求即发生，进程存活）。20 块挂载触发原生层访问越界，无法取得任何读数。

## 判据与结论

- 判据 recall≥0.95 且 0 编造 ⇒ **FAIL**（recall 0.30、1 条负例被作答）。
- 结论：**闸不是纯损失源**；去掉 coverage 闸反而放大同族串味，不支持「应删闸」。建议保留闸或转 C′ 换信号；top20 路径需先修原生崩溃，不能作为挂载方案。
