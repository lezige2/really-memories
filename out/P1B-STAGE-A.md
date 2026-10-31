# P1b Stage A：块可判率（只读，无模型）

- daily `D:\llama-mem\kvmem\daily\chat.db` sha `0a7eae495c4be89c`；n200 `D:\llama-mem\kvmem\scale40k\n200\chat.db` sha `2d84aefda3c76ece`
- 定义：显式 subject + 单一 predicate 才算可判；**我/我的 只记 default_self，不当兜底主体**。

## 主门槛（daily 真实文本）

| 数据集 | n | 显式可判 | 显式率 | 默认自我 | 默认率 | 不可判 |
|---|---|---|---|---|---|---|
| daily | 20 | 2 | **10.0%** | 12 | 60.0% | 6 |
| n200（补充） | 200 | 118 | 59.0% | 24 | 12.0% | 58 |

- 门槛显式率 ≥70% → daily **10.0%**：**STOP**

## 谓词分布（可判块）

- daily：{'plate': 2}
- n200：{'bank': 3, 'cat': 12, 'color': 4, 'company': 20, 'hometown': 12, 'meeting': 15, 'phone': 18, 'plate': 18, 'seat': 16}

## n200 不可判原因分布

- {'no_predicate': 48, 'no_subject': 10}

## daily 抽不出的块与原因

- `15` 对话归档（原文）：
用户：第128段：今天天气一般，不太想出门，就继续把手上事情做完 ← no_predicate
- `16` 自动摘要：天气一般，继续处理手头工作；有些事情推进慢但总体可控，别着急；周末计划去附 ← no_subject
- `17` 用户：第128段：今天天气一般，不太想出门，就继续把手上事情做完。今天天气一般，不太 ← no_subject
- `18` 用户：第132段：有些事情推进得比预期慢一点，不过总体还在可控范围。我在想下一步先把 ← no_predicate
- `19` 用户：第136段：我在想下一步先把哪块理顺，避免来回返工。今天的工作安排有点满，上午 ← no_predicate
- `20` 用户：第140段：我在想下一步先把哪块理顺，避免来回返工。我在想下一步先把哪块理顺， ← no_predicate

## daily 显式可判块

- `3` subject=阿泽 predicate=plate ← 我叫阿泽，今天（2026-10-27）我们做完了 b7 实验，结论是擦边；我的车牌号
- `12` subject=阿泽 predicate=plate ← 我叫阿泽，我的车牌号是京A88888。

## 判定

- **STOP（显式可判率 <70%）**：daily 显式主体率 10.0%（门槛 70%）；默认自我率 60.0%。
- 只读；未写 daily、未碰 tags、未改读写路径、未 commit。
