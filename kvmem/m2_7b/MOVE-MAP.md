# 7B / 14B 目录分离（2026-10-25）

按用户要求：**7B 的东西不放在 14B 的工作目录里**。

- `kvmem/m2_visibility/` = **14B 线**（M2 落地 + 四格实验 + 判定文档），只保留 14B 与共享记录
- `kvmem/m2_7b/` = **7B 线全部产物**（跑、块、证据），已冻结，不再产出

## 旧路径 -> 新路径

| 旧路径（14B 目录内） | 新路径（7B 目录） |
|---|---|
| `kvmem/m2_visibility/runs/` | `kvmem/m2_7b/runs/` |
| `kvmem/m2_visibility/runs_bias/` | `kvmem/m2_7b/runs_bias/` |
| `kvmem/m2_visibility/runs_g18/` | `kvmem/m2_7b/runs_g18/` |
| `kvmem/m2_visibility/runs_head/` | `kvmem/m2_7b/runs_head/` |
| `kvmem/m2_visibility/runs_iso{,2,3,4}/` | `kvmem/m2_7b/runs_iso{,2,3,4}/` |
| `kvmem/m2_visibility/runs_mask/` | `kvmem/m2_7b/runs_mask/` |
| `kvmem/m2_visibility/runs_t031/` `runs_t032/` `runs_t033/` | `kvmem/m2_7b/runs_t031/` … |
| `kvmem/m2_visibility/runs_var/` | `kvmem/m2_7b/runs_var/` |
| `kvmem/m2_visibility/runs_7b64/` | `kvmem/m2_7b/runs_7b64/` |
| `kvmem/m2_visibility/blocks/`（7B 块） | `kvmem/m2_7b/blocks/` |
| `kvmem/m2_visibility/evidence/`（7B 期评分） | `kvmem/m2_7b/evidence/` |
| `kvmem/m2_v1/`（7B 块） | `kvmem/m2_7b/m2_v1/` |
| `kvmem/blocks/`（2 个旧块） | `kvmem/m2_7b/blocks_old/` |
| `kvmem/m2_visibility/_t005_backup/` | `kvmem/_backup_t005/` |

## 留在 14B 目录的（未动）
`m2_visibility/m2/`（M2 交付）｜`m2_visibility/mine/`（预登记、盲判据、台账、验收、交付记录）｜
`m2_visibility/archive/`（本次归档包 + MANIFEST）｜`m2_visibility/runs_m14b/`（四格原始证据 + DLL 归档）｜
`kvmem/m2_v1_14b/`（14B 块，未动）｜顶层文档 HANDOFF.md / E10-NEXT*.md / ISOLATION-REPORT.md 等

## 影响
1. **14B 与 M2 的可复现性不受影响**：M2 驱动只引用 `runs_m14b/fixtures_14b.json` 与 `m2_v1_14b/`，两者都没动。
2. **7B 的旧驱动若直接跑会找不到路径**（它们按旧相对路径写死）。需要复跑 7B 时，按上表把路径改到 `m2_7b/` 下，或从 git 历史取回旧布局。
3. 历史文档里出现的 `runs_t031/…` 等路径，按上表换算即可。

## 已清理
测试目录内全部 `__pycache__` / `*.pyc`（共 12 处，可再生，无信息损失）。