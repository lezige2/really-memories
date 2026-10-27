# -*- coding: utf-8 -*-
"""极简只读联网检索：Bing HTML -> 标题/摘要/链接（安全加固版 v2）。

安全边界（任何一条都不是可选项）：
- 只发 GET；不带 cookie、不带登录态；跟随重定向最多 3 跳且每跳只允许 http(s)；
- 单次请求 8 s 超时；响应最多读 1 MiB（超出截断，仍可降级解析）；
- HTML 只做文本抽取（HTMLParser 剥标签/脚本/样式），**不执行任何脚本**；
- 结果链接只接受 http(s)，`javascript:`/`data:`/`file:`/相对不可解析 一律丢弃；
- 每次查询只写元数据日志到 `kvmem/web_logs/web_queries.jsonl`
  （query sha16、条数、耗时、成功/失败原因、是否截断）；**不记查询原文、不记页面正文/摘要**。

质量边界：
- Bing 结构变化时 `parse_results` 返回 []（不抛异常），调用方回退"不知道"；
- 结果按规范化 URL 去重；摘要截断到 300 字符；
- 对"天气/新闻/股价/最新"这类时效查询，若结果中没有任何日期/时间信息，
  `lookup_text` 会在文本前加一行"结果可能过时"标注。

用法：`from tools.web_lookup import search, lookup_text`
- `search(query, max_results=4) -> [{"title","url","snippet"}]`
- `lookup_text(query, max_results=4) -> str`（无可信结果时返回 ""）
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LOG_DIR = REPO / "kvmem" / "web_logs"
LOG_FILE = LOG_DIR / "web_queries.jsonl"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
SEARCH_URL = "https://cn.bing.com/search?q={q}&setlang=zh-CN"
TIMEOUT_S = 8
MAX_BYTES = 1024 * 1024          # 1 MiB
MAX_REDIRECTS = 3
SNIPPET_MAX = 300
ALLOWED_SCHEMES = ("http", "https")

TIME_SENSITIVE_RE = re.compile(
    r"今天|今日|现在|实时|最新|本周|这周|天气|气温|新闻|股价|股票|行情|汇率|油价|"
    r"(?i:today|now|latest|weather|news|stock|price)",
)
TIME_INFO_RE = re.compile(
    r"\d{4}\s*[-/年.]\s*\d{1,2}(\s*[-/月.]\s*\d{1,2})?|\d{1,2}\s*[:：]\s*\d{2}|"
    r"今天|今日|昨天|前天|刚刚|分钟前|小时前|上午|下午|晚间|早间|"
    r"(?i:today|yesterday|minutes? ago|hours? ago|GMT|UTC)",
)


# --------------------------------------------------------------------------
# 安全的 HTTP 读取（只 GET）
# --------------------------------------------------------------------------
class _NoCookieRedirect(urllib.request.HTTPRedirectHandler):
    """限制重定向跳数与协议，且不引入 cookie 处理。"""

    max_redirections = MAX_REDIRECTS

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        scheme = urllib.parse.urlsplit(newurl).scheme.lower()
        if scheme not in ALLOWED_SCHEMES:
            raise urllib.error.HTTPError(newurl, code, "redirect to disallowed scheme", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _opener() -> urllib.request.OpenerDirector:
    # 显式构造 opener：不挂 HTTPCookieProcessor，避免任何 cookie/登录态。
    return urllib.request.build_opener(_NoCookieRedirect())


def _read_capped(read, max_bytes: int = MAX_BYTES) -> tuple[bytes, bool]:
    """按上限读取；返回 (bytes, truncated)。read(n) 由调用方提供，便于单测。"""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = read(min(65536, max_bytes + 1 - total))
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
        if total > max_bytes:
            return b"".join(chunks)[:max_bytes], True
    return b"".join(chunks), False


def _fetch_html(url: str, timeout_s: float = TIMEOUT_S) -> tuple[str, bool]:
    """GET 一个页面；返回 (html_text, truncated)。异常上抛，由 search 统一归因。"""
    req = urllib.request.Request(url, method="GET", headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "zh-CN,zh;q=0.9",
    })
    with _opener().open(req, timeout=timeout_s) as resp:
        status = getattr(resp, "status", 200)
        if status != 200:
            raise urllib.error.HTTPError(url, status, "unexpected status", resp.headers, None)
        raw, truncated = _read_capped(resp.read, MAX_BYTES)
        ctype = (resp.headers.get("Content-Type") or "").lower()
    if ctype and "html" not in ctype and "xml" not in ctype:
        raise ValueError("non-html content-type")
    for enc in ("utf-8", "gb18030", "gbk"):
        try:
            return raw.decode(enc), truncated
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace"), truncated


# --------------------------------------------------------------------------
# HTML 文本抽取 / 结果解析
# --------------------------------------------------------------------------
class _TextExtractor(HTMLParser):
    """只提取可见文本；跳过 script/style/noscript。"""

    SKIP = {"script", "style", "noscript", "template"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0 and data:
            self.parts.append(data)


def _text(fragment: str) -> str:
    parser = _TextExtractor()
    try:
        parser.feed(fragment or "")
        parser.close()
    except Exception:  # noqa: BLE001 - 解析永不抛出到调用方
        pass
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()


def _clean(s: str) -> str:
    return _text(s)


def _safe_url(href: str, base: str = "https://cn.bing.com/") -> str:
    href = html.unescape((href or "").strip())
    if not href:
        return ""
    try:
        target = urllib.parse.urljoin(base, href)
        parts = urllib.parse.urlsplit(target)
    except ValueError:
        return ""
    if parts.scheme.lower() not in ALLOWED_SCHEMES or not parts.netloc:
        return ""
    # 去掉 fragment（展示与去重都用清理后的 URL）
    return urllib.parse.urlunsplit((parts.scheme.lower(), parts.netloc, parts.path, parts.query, ""))


def _dedupe_key(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    path = parts.path.rstrip("/") or "/"
    return f"{parts.scheme.lower()}://{parts.netloc.lower()}{path}?{parts.query}"


def _truncate(text: str, limit: int = SNIPPET_MAX) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


_BLOCK_RE = re.compile(r'<li[^>]*class="[^"]*b_algo[^"]*"[^>]*>(.*?)</li>', re.S | re.I)
_LINK_RE = re.compile(r'<h2[^>]*>.*?<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.S | re.I)
_P_RE = re.compile(r"<p[^>]*>(.*?)</p>", re.S | re.I)


def parse_results(page: str, max_results: int = 4) -> list[dict]:
    """从 Bing HTML 解析结果；结构不符/解析失败返回 []，不抛异常。"""
    if not page:
        return []
    out: list[dict] = []
    seen: set[str] = set()
    try:
        blocks = _BLOCK_RE.findall(page)
        if not blocks:
            # 结构变化/非搜索结果页：严格降级为空（fail closed），不猜页面上的其它 h2>a。
            return []
        for block in blocks:
            link_m = _LINK_RE.search(block)
            if not link_m:
                continue
            url = _safe_url(link_m.group(1))
            if not url:
                continue
            title = _clean(link_m.group(2))
            if not title:
                continue
            key = _dedupe_key(url)
            if key in seen:
                continue
            seen.add(key)
            snippet = ""
            p_m = _P_RE.search(block)
            if p_m:
                snippet = _truncate(_clean(p_m.group(1)))
            out.append({"title": _truncate(title, 200), "url": url, "snippet": snippet})
            if len(out) >= max(1, int(max_results)):
                break
    except Exception:  # noqa: BLE001 - 任何解析异常都降级为空
        return []
    return out


# --------------------------------------------------------------------------
# 日志（只元数据；不写查询原文/正文）
# --------------------------------------------------------------------------
def _log_query(query: str, *, n_results: int, elapsed_ms: float, ok: bool,
               reason: str = "", truncated: bool = False) -> None:
    record = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "query_sha16": hashlib.sha256((query or "").strip().encode("utf-8")).hexdigest()[:16],
        "n_results": n_results,
        "elapsed_ms": round(elapsed_ms, 1),
        "ok": ok,
        "reason": reason or "",
        "truncated": bool(truncated),
        "tool": "web_lookup_v2",
    }
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass  # 日志失败绝不影响检索


# --------------------------------------------------------------------------
# 对外 API
# --------------------------------------------------------------------------
def search(query: str, max_results: int = 4) -> list[dict]:
    """返回 [{title, url, snippet}]；失败/空结果/异常一律 []。"""
    q = str(query or "").strip()
    if not q:
        _log_query(q, n_results=0, elapsed_ms=0.0, ok=False, reason="empty_query")
        return []
    url = SEARCH_URL.format(q=urllib.parse.quote(q, safe=""))
    t0 = time.monotonic()
    truncated = False
    try:
        page, truncated = _fetch_html(url)
    except urllib.error.HTTPError as exc:
        _log_query(q, n_results=0, elapsed_ms=(time.monotonic() - t0) * 1000,
                   ok=False, reason=f"http_{getattr(exc, 'code', 'error')}")
        return []
    except urllib.error.URLError as exc:
        _log_query(q, n_results=0, elapsed_ms=(time.monotonic() - t0) * 1000,
                   ok=False, reason="timeout" if "timed out" in str(exc).lower() else "url_error")
        return []
    except TimeoutError:
        _log_query(q, n_results=0, elapsed_ms=(time.monotonic() - t0) * 1000,
                   ok=False, reason="timeout")
        return []
    except Exception as exc:  # noqa: BLE001
        _log_query(q, n_results=0, elapsed_ms=(time.monotonic() - t0) * 1000,
                   ok=False, reason=type(exc).__name__)
        return []
    rows = parse_results(page, max_results=max_results)
    elapsed_ms = (time.monotonic() - t0) * 1000
    if not rows:
        _log_query(q, n_results=0, elapsed_ms=elapsed_ms, ok=False,
                   reason="no_results", truncated=truncated)
        return []
    _log_query(q, n_results=len(rows), elapsed_ms=elapsed_ms, ok=True, truncated=truncated)
    return rows


def _is_time_sensitive(query: str) -> bool:
    return bool(TIME_SENSITIVE_RE.search(query or ""))


def _has_time_info(rows: list[dict]) -> bool:
    blob = " ".join((r.get("title", "") + " " + r.get("snippet", "") + " " + r.get("url", ""))
                    for r in rows)
    return bool(TIME_INFO_RE.search(blob))


_QUERY_PREFIX_RE = re.compile(
    r"^(?:请|麻烦|帮我|帮忙|请你|你能|可以|给我|我想|我要|能不能|可否)+")
_SEARCH_WORD_RE = re.compile(
    r"(?:查一?下|查查|搜一?下|搜索一下|搜一下|搜搜|上网查|网上查|网上搜|"
    r"检索|看一下|看看|帮我查|帮我搜|查|搜)")
_TRAIL_RE = re.compile(r"^(?:一下|下|个|点|吧|呢|啊|呀|嘛)\s*|\s*(?:一下|吧|呢|啊|呀|嘛)$")


def clean_query(text: str) -> str:
    """把"帮我查一下明天的新闻"清洗成"明天的新闻"这类可检索 query。

    只做措辞剥离（礼貌前缀 / 搜索动词 / 语气尾巴 / 标点），不改写词义；
    清洗后为空则退回原文本。
    """
    raw = str(text or "").strip()
    q = raw
    for _ in range(3):                      # 前缀可能叠加（请帮我查一下…）
        q = _QUERY_PREFIX_RE.sub("", q).strip()
    q = _SEARCH_WORD_RE.sub(" ", q)
    q = re.sub(r"[^\w\s]", " ", q)   # 去标点，保留中英文/数字
    q = re.sub(r"\s+", " ", q).strip()
    q = _TRAIL_RE.sub("", q).strip()
    q = _TRAIL_RE.sub("", q).strip()
    q = re.sub(r"(是多少|是啥|是什么|多少钱|怎么样|如何|吗|呢|啊|呀|吧)$", "", q).strip()
    return q or raw


def query_keywords(q: str, limit: int = 6) -> list[str]:
    """检索相关度用的短词：中文 2-gram（去掉纯虚词），最多 limit 个。"""
    words = re.findall(r"[\u4e00-\u9fff]{2,}", str(q or ""))
    stop = {"一下", "帮我", "请问", "什么", "怎么", "多少", "可以", "需要",
            "我们", "你们", "他们", "这个", "那个"}
    kws = []
    for w in words:
        for i in range(len(w) - 1):
            bg = w[i:i + 2]
            if bg in stop or bg in kws:
                continue
            kws.append(bg)
    # "新闻/天气"这类关键词本身也要保留（它们是主题词）
    for w in words:
        if len(w) <= 4 and w not in kws and w not in ("一下",):
            kws.append(w)
    return kws[:limit]


def lookup_text(query: str, max_results: int = 4, keywords=None) -> str:
    """格式化为给模型看的结果文本；无结果返回 ""；时效查询无日期时加过时标注。"""
    rows = search(query, max_results=max_results)
    if not rows:
        return ""
    if keywords:
        kws = [str(k).lower() for k in keywords if str(k or "").strip()]
        if kws:
            need = 2 if len(kws) >= 2 else 1     # 多关键词时至少命中 2 个，过滤"只沾一字"的噪声
            def _hits(r):
                blob = ("%s %s %s" % (r.get("title") or "", r.get("snippet") or "",
                                      r.get("url") or "")).lower()
                return sum(1 for k in kws if k in blob)
            kept = [r for r in rows if _hits(r) >= need]
            rows = kept[:max_results]
            if not rows:            # 结果与 query 无关：宁可"无资料"也不要跑偏
                return ""
    lines = []
    for i, r in enumerate(rows, 1):
        lines.append("%d) %s — %s（%s）" % (i, r["title"], r["snippet"], r["url"]))
    text = "\n".join(lines)
    if _is_time_sensitive(query) and not _has_time_info(rows):
        text = ("（注意：结果可能过时——未包含日期/时间信息；请自行核对时效，"
                "不要当作实时数据。）\n" + text)
    return text


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "北京 天气"
    print(lookup_text(q))