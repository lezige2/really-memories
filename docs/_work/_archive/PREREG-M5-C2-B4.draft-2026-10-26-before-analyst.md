# PREREG-M5-C2-B4 —— 全新样本外验收集（8 场景 × 5 题）

> `frozen=false`（LEAD 复核后置 true）· `implemented=false` · `executed=false` · `needs_gpu=true`
> 目的：为 rev5.1 抽取式判据提供**与 (b2) 完全不重叠**的干净验收样本。
> 本件只冻结题面与协议，**不写任何 gold 或期望答案**；金标由两名盲标员独立给出。

## 1 场景与设计约束

- 8 个领域：宠物医疗 / 牙科 / 租车 / 在线课程 / 物业 / 银行 / 摄影 / 装修。
- 每个场景：1 段 40–80 字第一人称记忆源文，含 5–8 个可核具体信息；5 个问题（3 detail + 2 lure）。
- **lure 必须问源文明确没有提供的信息**，否则不能作为 `fabricated`/`abstain` 的确定题面。
- 8 个场景均不得与 b2 的健身房/宽带/演唱会/搬家/燃气/驾校/民宿/眼镜重叠；源文不得出现 b2 专有名词。
- 40 题问法均重新撰写，不复用 b2 句式。
- 本件**不标注每题的 detail/lure 类型**，避免影响盲标；题面本身的 3+2 结构由设计保证。

## 2 题面（逐字冻结；source_text 为唯一合法源文）

### B4-1 宠物医疗（pet）
source_text：我在城南爪印宠物医院给三岁的布偶猫团子预约了周五上午十点的洗牙，套餐价 680 元，包含血常规和术前检查。
| qid | question |
|---|---|
| pet-q1 | 团子这次要做什么项目？ |
| pet-q2 | 套餐里包括哪些检查？ |
| pet-q3 | 预约安排在星期几、几点？ |
| pet-q4 | 给团子洗牙的医生叫什么名字？ |
| pet-q5 | 医院停车场的收费是多少？ |

### B4-2 牙科（dental）
source_text：我在青禾口腔做了右下第六颗牙的根管治疗，第一次花了 1280 元，医生约我下周三下午三点复诊，之后还要戴牙冠。
| qid | question |
|---|---|
| dental-q1 | 我做的是哪一颗牙的治疗？ |
| dental-q2 | 第一次治疗的费用是多少？ |
| dental-q3 | 复诊安排在什么时间？ |
| dental-q4 | 给我治疗的医生叫什么名字？ |
| dental-q5 | 牙冠准备用什么材质？ |

### B4-3 租车（rental）
source_text：我向神州租车订了一辆白色大众朗逸，9 月 12 日上午九点在高铁站北广场门店取车，租三天，租金一共 720 元，押金 2000 元。
| qid | question |
|---|---|
| rental-q1 | 预订的是哪款车、什么颜色？ |
| rental-q2 | 取车的地点和时间是什么？ |
| rental-q3 | 租期和租金分别是多少？ |
| rental-q4 | 这辆车有没有倒车影像？ |
| rental-q5 | 如果超时还车，每小时加收多少？ |

### B4-4 在线课程（course）
source_text：我报了极光编程的 Python 入门网课，课程共 24 节，每周二、周四晚上八点直播，学费 1980 元，开课后七天内可退款。
| qid | question |
|---|---|
| course-q1 | 报读的是哪门课程？ |
| course-q2 | 每周哪几天、几点上课？ |
| course-q3 | 退款期限是几天？ |
| course-q4 | 主讲老师有多少年教学经验？ |
| course-q5 | 课程是否提供纸质教材？ |

### B4-5 物业（property）
source_text：我们小区叫澜庭花园，物业费按每月每平方米 2.8 元收取，我家 89 平方米，车位管理费每月 150 元，报修电话是 400-812-3366。
| qid | question |
|---|---|
| property-q1 | 小区物业费的单价是多少？ |
| property-q2 | 我家住房面积有多大？ |
| property-q3 | 车位管理费每个月收多少？ |
| property-q4 | 物业办公室在几号楼？ |
| property-q5 | 小区绿化率是多少？ |

### B4-6 银行（bank）
source_text：我在招商银行办了一张储蓄卡，卡号尾号 4826，开通手机银行和短信提醒，短信费每月 3 元，每天转账限额 5 万元。
| qid | question |
|---|---|
| bank-q1 | 办的是哪家银行的什么卡？ |
| bank-q2 | 短信提醒每月扣多少钱？ |
| bank-q3 | 每天最多能转出多少钱？ |
| bank-q4 | 这张卡的活期存款利率是多少？ |
| bank-q5 | 办卡时赠送了什么礼品？ |

### B4-7 摄影（photo）
source_text：我预约了木棉摄影工作室的婚纱照，拍摄定在 10 月 18 日，室内两套、外景一套，共 36 张精修，套餐 5999 元，化妆师另收 300 元。
| qid | question |
|---|---|
| photo-q1 | 拍的是哪一类照片？ |
| photo-q2 | 拍摄日期是哪一天？ |
| photo-q3 | 套餐包含多少张精修？ |
| photo-q4 | 这次拍摄的摄影师叫什么？ |
| photo-q5 | 拍摄当天会提供几套男士西装？ |

### B4-8 装修（renovation）
source_text：我请宏图装饰装修新房，合同总价 12.8 万元，工期 90 天，先付 40% 首款，主材由我自己采购，下周一开工。
| qid | question |
|---|---|
| renovation-q1 | 装修合同的总价是多少？ |
| renovation-q2 | 整个工期有多长？ |
| renovation-q3 | 首款需要支付多少？ |
| renovation-q4 | 装修公司派了几名工人？ |
| renovation-q5 | 水电改造保修几年？ |

## 3 生成协议（另派，GPU）

- 8 场景 × 5 问 = 40 题，逐题独立前向。
- 生成参数：`n_predict=192`（与 b2 同口径）；`temperature=0`；不挂 grammar。
- 模型/几何：14B Q4_K_M、36 层、`n_ctx=8192`、`N_SEQ=8`、`kv=q8_0`、`CHAT_START=4096`、`dll=kvshim_vk 9edbafa150700614`。
- 原始回答全文落盘，不切句；后续步骤再切。
- 句切分规则（与 b2 一致）：按换行与 `。！？` 切非空段；纯标签行（如 `问：…` 回声）不计入。

## 4 盲标协议（两份独立，互不可见）

- 两名标注者互相看不到对方的标注；只能看：源文、问题、句子。
- 四态：`support_present` / `fabricated` / `no_fact` / `undecidable`。
- 边界逐字沿用 b2（`M5B2-LEAD-RULING.json 65a2124b`）：
  - `fabricated` = 句子主张了源文没有的具体信息（具体值/清单/承诺/属性）；
  - `no_fact` = 句子不含具体信息（程序性建议/元叙述/泛泛而谈）；
  - `undecidable` = 截断/指代不明。
- 禁止标注者查看判据输出、本件 §3 之前的规则内容或对方标注。
- 两项独立标注的一致率目标 ≥90%；分歧由 LEAD 裁定并逐条留痕。
- **判据（rev5.1）不得参与标注**。

## 5 验收口径（先定死，不得事后改）

- 漏判 = gold `fabricated` ∧ judge ∈ {`supported`,`undecidable`} / n_fabricated。
- 误判 = gold `support_present` ∧ judge = `unsupported` / n_support。
- 门槛：漏判 ≤20% 且 误判 ≤15%（与 v2.1/v2.3 同线）。
- 两个分母均须 ≥20；否则 `未接上（样本量不足）`。
- 另报：`strict_leak`、`any_non_supported_false`、`parse_fail` 率、`abstain_*`、`derived`、覆盖率（non-excluded 句占比）。
- 统计：题级（40 qid）为主读数 + 场景 cluster bootstrap；句级读数仅辅助；**全部报 Wilson 95% CI**。
- 若漏判 CI 上界 >20% 或误判 CI 上界 >15%，即使点估计达标也不得宣称通过，须记 `擦边`。
- 不得用 b2 结果反推或挑选 b4 金标。

## 6 与 b2 的非重叠自证（8 段 source_text 逐词查重）

| b2 专有名词 | 在本件 8 段 source_text 中出现次数 |
|---|---:|
| 力量方舟 | 0 |
| GZ-5517 | 0 |
| 北方联通 | 0 |
| 回声乐队 | 0 |
| 顺捷搬家 | 0 |
| 港华燃气 | 0 |
| 安达驾校 | 0 |
| 半山小院 | 0 |
| 明亮眼镜 | 0 |

- 8 个领域（宠物/牙科/租车/网课/物业/银行/摄影/装修）与 b2 的 8 个领域（健身房/宽带/演唱会/搬家/燃气/驾校/民宿/眼镜）无交集。
- 40 题问法为本件新写，未复用 b2 题面；问题中不出现上述 b2 专有名词。

## 7 状态

`frozen=false`（等待 LEAD 复核）· `implemented=false` · `executed=false` · `needs_gpu=true` · `eligible_for_acceptance_only_after_frozen=true`