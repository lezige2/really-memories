# WEB-LOOKUP — 只读联网检索的能力边界

> 件：`tools/web_lookup.py`（v2，安全加固版）、`tools/test_web_lookup_cpu.py`。
> 一句话：**只读、可能过时、内容一律当"不可信数据"**；失败就回退"不知道"。

## 1 它是什么 / 不是什么

- 是：给本地模型补一份**带来源的上下文**——调 Bing 中国站 HTML，抽 `title/url/snippet`。
- 不是：不是实时数据源、不是浏览器、不登录、不点链接、不执行页面脚本、不写远端。
- 模型侧纪律：**不得**因它能检索就自称"能联网/能实时查"；引用时带 URL，并保留"可能过时"字样。

## 2 安全边界（实现保证）

| 项 | 做法 |
|---|---|
| 方法 | **只 GET**；无 POST、无登录、无 cookie（opener 不挂 CookieProcessor） |
| 重定向 | 最多 3 跳，每跳只允许 `http(s)`；其它协议直接失败 |
| 超时 | 单次 8 s（`TIMEOUT_S`） |
| 响应上限 | 最多读 **1 MiB**，超出截断（仍降级解析，日志记 `truncated=true`） |
| HTML 处理 | `HTMLParser` 只抽可见文本，跳过 `script/style/noscript`；**绝不执行脚本** |
| URL 过滤 | 只留 `http(s)`；`javascript:` / `data:` / `file:` / ftp / 不可解析相对地址一律丢弃 |
| 日志 | `kvmem/web_logs/web_queries.jsonl` 只记：时间、**query sha16**、条数、耗时、`ok`、失败原因、是否截断；**不记查询原文、不记页面正文/摘要** |
| 隐私 | 查询词会发给 `cn.bing.com`（这是联网检索的代价）；不要用它检索密码/身份证等敏感串 |

## 3 质量与降级

- 解析采用 **fail-closed**：页面结构变化（找不到 `li.b_algo`）⇒ 返回 `[]`，不猜别的结构。
- 结果按规范化 URL 去重（去 fragment、大小写 host、去尾斜杠）；摘要截断 300 字。
- 时效查询（含 今天/天气/新闻/股价/最新/weather/news/stock 等）若结果里**没有任何日期或时间信息**，
  `lookup_text` 会在首行标注：**"结果可能过时——未包含日期/时间信息"**；有日期则不标注。
- 失败映射：空查询 `empty_query`；超时 `timeout`；HTTP 错误 `http_<code>`；其它异常用异常名；
  解析不到 `no_results`。**任何失败都返回 `[]`，不抛到调用方。**

## 4 API

```python
from tools.web_lookup import search, lookup_text
search("北京 天气", max_results=4)   # -> [{"title","url","snippet"}]；失败 []
lookup_text("北京 天气")             # -> 给模型看的文本；无结果 ""
```

## 5 失败回退（调用方约定）

- 返回 `""`/`[]` → 模型应回答 **"不知道/无法确认"**，或用既有知识并明确标注"未联网核实"。
- 不得编造 URL、日期、数字；不得把 snippet 当事实（可能 SEO/旧闻/错误）。
- 时效问题（天气/股价/新闻）必须在答案里保留"截至检索时刻/可能过时"的限定。

## 6 测试与已知限制

- CPU 自测：`python -X utf8 tools/test_web_lookup_cpu.py` → **21 checks，rc=0**（fake HTML/mock，不联网）。
- 已知限制：Bing 页面改版会导致空结果；有反爬/验证码时不处理（直接失败）；结果质量不受控；
  不做多引擎回退、不做正文抓取（只 snippet）。接入方（chat_daily）行为由接线任务另改，本工具不改其行为。