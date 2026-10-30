# S2 检索复现（n200 只读副本，K2-off/time-off，每条 3 次）

- 源 `D:\llama-mem\kvmem\scale40k\n200\chat.db` sha `2d84aefda3c76ece`；副本 `D:\llama-mem\tmp\s2\chat.db`；不改代码/不起服务/不写产品库。
- 参数：`memory_service.retrieve(topk=20)`；确定性：**一致**

| query | target | rank×3 | 空结果×3 | top1 分数×3 | 原因 |
|---|---|---|---|---|---|
| q048 | 53 | [3, 3, 3] | [True, True, True] | [None, None, None] | gate_below_threshold |
| q052 | 70 | [4, 4, 4] | [True, True, True] | [None, None, None] | gate_below_threshold |
| q060 | 25 | [1, 1, 1] | [True, True, True] | [None, None, None] | gate_below_threshold |
| q062 | 130 | [22, 22, 22] | [False, False, False] | [2.0, 2.0, 2.0] | low_rank_beyond_20 |
| q063 | 144 | [26, 26, 26] | [False, False, False] | [2.0, 2.0, 2.0] | low_rank_beyond_20 |

## 逐条证据

### q048 `杨帆那车牌子你还记得不？` → target 53
- 目标块：exists=True，file=True，size=17342212
- 3 次：ids 一致=True；gate=below_threshold；candidates=50；top1=None
- 目标得分/覆盖/命中：2.0 / 0.2 / ['杨帆', '车牌']；全排序 rank=3
- best：{'id': 8, 'score': 2.0, 'coverage': 0.2, 'hits': ['得不', '杨帆']}；查询 token 缺于目标：['你还', '子你', '帆那', '得不', '牌子', '记得', '还记', '那车']
- 原因：['top1_coverage 0.200 < 0.30', 'index_path: R.search empty', 'no_query_rewrite（_retrieval_text 仅剥寒暄前缀）']；同义词假设：['牌子~车牌号']
- R.search(k=20)：empty=True rank=None

### q052 `周昊号码多少来着？` → target 70
- 目标块：exists=True，file=True，size=79602756
- 3 次：ids 一致=True；gate=below_threshold；candidates=10；top1=None
- 目标得分/覆盖/命中：1.0 / 0.14285714285714285 / ['周昊']；全排序 rank=4
- best：{'id': 12, 'score': 1.0, 'coverage': 0.14285714285714285, 'hits': ['周昊']}；查询 token 缺于目标：['号码', '多少', '少来', '昊号', '来着', '码多']
- 原因：['top1_coverage 0.143 < 0.30', 'top1_score 1.0 < 2.0', 'index_path: R.search 未含目标', 'no_query_rewrite（_retrieval_text 仅剥寒暄前缀）']；同义词假设：['号码~手机号', '来着=口语']
- R.search(k=20)：empty=False rank=None

### q060 `杨帆那个会定在几号几点了？` → target 25
- 目标块：exists=True，file=True，size=79602756
- 3 次：ids 一致=True；gate=below_threshold；candidates=70；top1=None
- 目标得分/覆盖/命中：3.0 / 0.2727272727272727 / ['定在', '杨帆', '那个']；全排序 rank=1
- best：{'id': 25, 'score': 3.0, 'coverage': 0.2727272727272727, 'hits': ['定在', '杨帆', '那个']}；查询 token 缺于目标：['个会', '会定', '几号', '几点', '号几', '在几', '帆那', '点了']
- 原因：['top1_coverage 0.273 < 0.30', 'index_path: R.search 未含目标', 'no_query_rewrite（_retrieval_text 仅剥寒暄前缀）']；同义词假设：['会~会议', '几号几点~时间']
- R.search(k=20)：empty=False rank=None

### q062 `王强是哪儿人？` → target 130
- 目标块：exists=True，file=True，size=81692036
- 3 次：ids 一致=True；gate=pass；candidates=38；top1=2.0
- 目标得分/覆盖/命中：1.0 / 0.2 / ['王强']；全排序 rank=22
- best：{'id': 4, 'score': 2.0, 'coverage': 0.4, 'hits': ['哪儿', '王强']}；查询 token 缺于目标：['儿人', '哪儿', '强是', '是哪']
- 原因：['target_rank 22 > 20（score 1.0 vs best 2.0）', 'index_path: R.search 未含目标', 'no_query_rewrite（_retrieval_text 仅剥寒暄前缀）']；同义词假设：['哪儿人~老家']
- R.search(k=20)：empty=False rank=None

### q063 `杨帆是哪儿人？` → target 144
- 目标块：exists=True，file=True，size=16715428
- 3 次：ids 一致=True；gate=pass；candidates=36；top1=2.0
- 目标得分/覆盖/命中：1.0 / 0.2 / ['杨帆']；全排序 rank=26
- best：{'id': 25, 'score': 2.0, 'coverage': 0.4, 'hits': ['哪儿', '杨帆']}；查询 token 缺于目标：['儿人', '哪儿', '帆是', '是哪']
- 原因：['target_rank 26 > 20（score 1.0 vs best 2.0）', 'index_path: R.search rank 9', 'no_query_rewrite（_retrieval_text 仅剥寒暄前缀）']；同义词假设：['哪儿人~老家']
- R.search(k=20)：empty=False rank=9

## 结论

- 5 条 3 次结果一致，无非确定；空结果 = top1 门槛清空，低排 = 词面覆盖不足（改写/口语词与块用词不匹配），
- 目标块均存在可读、索引无缺失；产品改写对本组 query 不生效（无寒暄前缀）。
