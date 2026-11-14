# 关系 LoRA 预登记（B 三条前置，先记后跑）

> 数据 sha `414f7582be545b5555f038ee0eefd156847463646bcdb704766a6f38188ac0ec`（train 1616 / dev 202 / test 202；correct 755 / new_subject 647 / ambiguous 618）。
> 模型：Qwen2.5-14B-Instruct QLoRA r16/1ep；adapter 不合并、不切默认、不进产品路径；时间盒 11:30。

## 1 结论口径（B①）

- 本轮 held-out 60 与补的 420 条**同分布**（都用了 held-out 风格句式），所以：
  - 只能写"**能否学到目标表达分布**"；
  - **不能写"泛化"**。
- 真正的泛化探针由 B 在训后另出 20 条**第三种风格**；本轮不碰、不调。

## 2 指标

- **欠拟合门（B③）**：test 202 内部 acc **<85% → 判"没训够"，该次训练无效**，不得据此说 LoRA 不行。
- 主报告：test 202 acc 与 held-out 60 acc **并列**；held-out 四向（错隐藏/重复/漏判/正则）。
- **per-class precision（B②）**：必须报 correct/new_subject/ambiguous 三类 precision；总 acc 不作结论。类别失衡（correct 755 最多）会把模型推向 correct，即"错隐藏"方向，重点看 correct 的 precision。
- 配对：与规则 v2（held-out 36/60）、P（41/60）比；**held-out 净增 <5 条 → 判不成立**（预注册）。
- 置信段：本轮生成式不产可靠 confidence，不报"0.9 桶"；只报 per-class precision，并注明缺 confidence 是限制。

## 3 失败判据

- 错隐藏（ambiguous→correct）≥1 → 该版本不得用于产品路径；
- 灾难错（correct↔new_subject）≥1 → 记录，不自动否决（本轮只研究）；
- parse_fail >0 → 该臂不可用；
- OOM/NaN 两次 → abort。

## 4 交付

- adapter sha、训练日志（loss/NaN）、test/held-out eval JSON；
- 阴性也交；不引用为"训练有效"；
- 未做清单 + 回滚（删 adapter/保持 flag off）。