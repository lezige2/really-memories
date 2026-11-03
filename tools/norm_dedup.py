# -*- coding: utf-8 -*-
"""norm_hash 轻量去重（纯代码；不删数据、不改 schema）。

归一化：NFKC → 去空白/标点/符号 → casefold。
key = (tenant, scope, norm_hash)；跨 scope 不吞；语义相近但不完全归一不吞。
"""

import hashlib
import unicodedata

# 标点/空白/符号类别：P* Z* S*
_SKIP_CATS = ("P", "Z", "S")


def norm_text(text):
    s = unicodedata.normalize("NFKC", str(text or ""))
    out = []
    for ch in s:
        cat = unicodedata.category(ch)
        if cat[0] in _SKIP_CATS:
            continue
        out.append(ch)
    return "".join(out).casefold().strip()


def norm_hash(text):
    norm = norm_text(text)
    if not norm:
        return None
    h = hashlib.sha256(norm.encode("utf-8")).hexdigest()
    return {"norm": norm, "norm_hash": h, "key": (h,)}


def find_duplicate(con, text, tenant="default", scope="private"):
    """同 tenant+scope 下按 norm_hash 找已有行；命中返回 (id, name)；否则 None。"""
    import sqlite3
    if isinstance(con, sqlite3.Connection) is False:      # 防御：需 sqlite 连接
        return None
    info = norm_hash(text)
    if not info:
        return None
    target = info["norm_hash"]
    try:
        rows = con.execute(
            "SELECT id,name,text FROM memory_source WHERE tenant=? AND scope=?",
            (str(tenant), str(scope))).fetchall()
    except Exception:                                     # noqa: BLE001
        return None
    for rid, name, old in rows:
        old_info = norm_hash(old)
        if old_info and old_info["norm_hash"] == target:
            return {"id": int(rid), "name": str(name),
                    "norm_hash": target, "tenant": str(tenant),
                    "scope": str(scope)}
    return None