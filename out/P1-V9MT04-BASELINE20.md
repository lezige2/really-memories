# P1 · V9MT04 全关基线 20×

- 臂：`--no-lifecycle-cap --no-memory-access --no-lifecycle-archive --no-lifecycle-fallback --no-audit`
- 同副本 `kvmem/v9m04c`、同 pre_state，20 次。

| pass | fallback |
|---|---|
| **20/20** | **0** |

- 结论：基线 **20/20 稳定、0 fallback** ⇒ V9MT04 **不是 flaky**；默认全开时的 10/20 与基线 11/20 之差不是纯噪声，需继续按两臂定位（见 `P1-V9MT04-TWOARM.md`）。