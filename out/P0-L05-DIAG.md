# P0 L05 归因（event on/off 各 5 次）

- 两副本均由 daily 备份重建（`kvmem/l05/{off,on}`）；K2 off、verifier v1、TTS off
- 按 L05 原 pre_state：`/remember 我的车是白色 SUV` + 8 轮闲聊 → 问「我的车是什么颜色、什么车型？」

| 臂 | pass | verify_fallback | block_ids | event_date（新建块） |
|---|---|---|---|---|
| event off | **2/5** | 3/5 | [21, 3, 12, 13] | 无 event 列 |
| event on | **2/5** | 3/5 | [21, 3, 12, 13] | **None（恒空）** |

## 判定

- **两臂完全同型**：都是 2 次 natural、3 次「这条我没法从记忆里核对，先不猜。」，取块一致 `[21,3,12,13]`。
- event on 时该会话写入块 **event_date 恒 NULL**，查询句也无时间词 ⇒ `filter_expired` 对本例无实际作用。
- ⇒ **L05 与 event 无关，是答案层 flaky**。

## 影响

- P0 首轮 extra 18→17 的新增 L05，**很可能是抽样噪声**，不足以判 event 因果；按“同日不二次迁移”未复测，daily 保持回滚态（uv=0）。

## 建议

- 定 event 去留需换日、加大样本（extra 3×）；当前证据不支持“event 造成回归”。