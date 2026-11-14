# P1 · V9MT04 配对 5×

| 臂 | pass | 每次 state |
|---|---|---|
| 默认 on（cap+access） | **2/5** | verify_fallback, natural, verify_fallback, verify_fallback, natural |
| 显式 off（--no-lifecycle-cap --no-memory-access） | **5/5** | natural, natural, natural, natural, natural |

- 默认 on 的 3 次失败**全部是 `verify_fallback`**（罐头句「这条我没法从记忆里核对，先不猜。」），不是答错旧值。
- 显式 off 5/5 全 natural，答案均为「周二晚上七点四十」。
- 统计：RD（off−on）= **+0.60**，95%CI **[+0.17, +1.03]**；Fisher 双侧 **p = 0.167**。

## 判定
- 按“两次接近记 flaky、明显差则暂停”：n=5 尚未过 0.05，**但方向一致、差距大（0.40 vs 1.00）且失败形态集中（全为校验回退）**，不能简单记为偶发。
- 结论：**建议暂停默认开启**，先定位 cap/access 是否改变挂载顺序/校验输入；若确认无关再恢复。

## 后续建议
1. 扩到 20 次/臂确认差距是否稳定；
2. 对比两侧的 `block_ids` 顺序与 verify mismatches（本例失败被罐头句掩盖，需看 verify 事件）。