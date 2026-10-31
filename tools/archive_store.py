# -*- coding: utf-8 -*-
"""P1：归档能力（local-only、默认 off、不自动搬、不写 daily 库）。

设计约束（B 定）：
  * 只做本地 zip + manifest + sha + sidecar index；**不 ALTER daily、不加列**；
  * 归档/恢复只对副本/sidecar 操作；源行不删，只在 sidecar 标 `is_archived`；
  * 无定时器/线程/admin 自动搬迁；启动 check 断言 local-only；
  * 恢复只认 sha；同 subject+predicate 若存在更新（live）行 → `superseded_by`，
    不复活成最新；同链整链归档或不动；归档/恢复幂等。

对外：
  startup_check() / assert_local_only(paths)
  archive_rows(rows, zip_path, sidecar_path) -> manifest dict
  load_archive(zip_path, sidecar_path) -> (manifest, entries)  # 校验 sha
  restore_plan(live_rows, zip_path, sidecar_path) -> plan dict
  apply_restore(live_rows, plan) -> new rows（纯函数，不写库）
"""

import hashlib
import json
import os
import zipfile

ARCHIVE_SCHEMA = "p1_archive_v1"
MANIFEST_NAME = "manifest.json"
LOCAL_ONLY = True
_NETWORK_ATTRS = ("socket", "urllib", "http", "requests", "ftplib", "smtplib")


class ArchiveError(Exception):
    pass


def _sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha_file(path):
    return _sha_bytes(open(path, "rb").read())


def assert_local_only(paths):
    """代码断言：归档/恢复目标必须是本地文件路径（拒绝 URL / 网络方案）。"""
    for p in paths:
        s = str(p or "")
        if not s or "://" in s or s.lower().startswith(("http", "ftp", "s3:")):
            raise ArchiveError("local-only：拒绝非本地路径 %r" % (p,))
    for attr in _NETWORK_ATTRS:
        if attr in globals():
            raise ArchiveError("local-only：模块不应持有网络对象 %r" % attr)
    if not LOCAL_ONLY:
        raise ArchiveError("local-only 断言失败")
    return True


def startup_check():
    """启动断言：无网络依赖、无定时/后台搬迁（模块不做任何扫描或自动搬）。"""
    assert_local_only([__file__])
    return {"local_only": True, "auto_move": False, "schema": ARCHIVE_SCHEMA}


def _row_key(row):
    return (str(row.get("subject") or ""), str(row.get("predicate") or ""))


def archive_rows(rows, zip_path, sidecar_path):
    """把行（副本）打成确定性 zip + sidecar；源行不变，只标 is_archived。"""
    assert_local_only([zip_path, sidecar_path])
    rows = sorted((dict(r) for r in rows), key=lambda r: int(r["id"]))
    os.makedirs(os.path.dirname(os.path.abspath(zip_path)) or ".", exist_ok=True)
    entries = []
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for r in rows:
            rid = int(r["id"])
            payload = (
                "id=%d\nname=%s\nsubject=%s\npredicate=%s\ncreated_at=%s\n"
                "block_sha=%s\nblock_bytes=%d\n\ntext:\n%s"
                % (rid, r.get("name", ""), r.get("subject", ""),
                   r.get("predicate", ""), r.get("created_at", ""),
                   r.get("block_sha", ""), int(r.get("block_bytes", 0)),
                   r.get("text", ""))
            ).encode("utf-8")
            member = "blocks/%06d.txt" % rid
            info = zipfile.ZipInfo(member, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, payload)
            entries.append({
                "id": rid, "name": str(r.get("name", "")),
                "subject": r.get("subject", ""), "predicate": r.get("predicate", ""),
                "created_at": str(r.get("created_at", "")),
                "event_date": str(r.get("event_date") or ""),
                "text_sha256": _sha_bytes(str(r.get("text", "")).encode("utf-8")),
                "block_sha256": str(r.get("block_sha", "")),
                "block_bytes": int(r.get("block_bytes", 0)),
                "member": member, "is_archived": True,
            })
    manifest = {"schema": ARCHIVE_SCHEMA, "kind": "archive",
                "zip_sha256": sha_file(zip_path),
                "n": len(entries), "entries": entries}
    sidecar = {"schema": ARCHIVE_SCHEMA, "kind": "sidecar",
               "zip": os.path.abspath(zip_path),
               "zip_sha256": manifest["zip_sha256"],
               "entries": entries, "created_at": None}
    with open(zip_path + ".manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2, sort_keys=True)
    with open(sidecar_path, "w", encoding="utf-8") as f:
        json.dump(sidecar, f, ensure_ascii=False, indent=2, sort_keys=True)
    return manifest


def load_archive(zip_path, sidecar_path):
    """恢复只认 sha：zip sha 与每个 member 的 text sha 都必须匹配。"""
    assert_local_only([zip_path, sidecar_path])
    if not os.path.exists(zip_path) or not os.path.exists(sidecar_path):
        raise ArchiveError("archive/sidecar 不存在")
    sidecar = json.load(open(sidecar_path, encoding="utf-8"))
    if sha_file(zip_path) != sidecar.get("zip_sha256"):
        raise ArchiveError("zip sha 不匹配（恢复拒绝）")
    manifest = json.load(open(zip_path + ".manifest.json", encoding="utf-8"))
    if manifest.get("zip_sha256") != sidecar.get("zip_sha256"):
        raise ArchiveError("manifest sha 与 sidecar 不一致")
    with zipfile.ZipFile(zip_path) as zf:
        for e in manifest["entries"]:
            data = zf.read(e["member"])
            body = data.split(b"text:\n", 1)[-1]
            if _sha_bytes(body) != e["text_sha256"]:
                raise ArchiveError("member sha 不匹配：id=%s" % e["id"])
    return manifest


def restore_plan(live_rows, zip_path, sidecar_path):
    """防覆盖恢复计划：只认 sha；有更新同 subject+predicate -> superseded_by；同链整链处理。"""
    manifest = load_archive(zip_path, sidecar_path)
    live = [dict(r) for r in live_rows]
    by_key = {}
    for r in live:
        by_key.setdefault(_row_key(r), []).append(r)
    chains = {}
    for e in manifest["entries"]:
        chains.setdefault((e.get("subject") or "", e.get("predicate") or ""),
                          []).append(e)
    plan = []
    for key, ents in sorted(chains.items()):
        newer = [r for r in by_key.get(key, [])
                 if int(r["id"]) > max(int(e["id"]) for e in ents)]
        if newer:
            sup = max(newer, key=lambda r: int(r["id"]))
            for e in ents:
                plan.append({"action": "skip_superseded", "id": e["id"],
                             "superseded_by": int(sup["id"]),
                             "subject": key[0], "predicate": key[1]})
        else:
            for e in ents:
                plan.append({"action": "restore", "id": e["id"],
                             "subject": key[0], "predicate": key[1],
                             "text_sha256": e["text_sha256"]})
    return {"schema": ARCHIVE_SCHEMA, "zip_sha256": manifest["zip_sha256"],
            "plan": plan}


def _entry_text(zip_path, entry_id):
    manifest_path = zip_path + ".manifest.json"
    manifest = json.load(open(manifest_path, encoding="utf-8"))
    e = next(x for x in manifest["entries"] if int(x["id"]) == int(entry_id))
    with zipfile.ZipFile(zip_path) as zf:
        return zf.read(e["member"]).split(b"text:\n", 1)[-1].decode("utf-8")


def apply_restore(live_rows, plan, zip_path):
    """纯函数：按计划把恢复行追加到副本；同 id 已存在则跳过（幂等）。"""
    rows = [dict(r) for r in live_rows]
    have = {int(r["id"]) for r in rows}
    for item in plan.get("plan") or []:
        if item["action"] != "restore" or int(item["id"]) in have:
            continue
        rows.append({"id": int(item["id"]), "name": "restored-%s" % item["id"],
                     "subject": item.get("subject"), "predicate": item.get("predicate"),
                     "text": _entry_text(zip_path, item["id"]),
                     "is_archived": False})
        have.add(int(item["id"]))
    rows.sort(key=lambda r: int(r["id"]))
    return rows


def content_hash(rows):
    """行内容哈希（不回写 DB；用于 round-trip/回滚校验）。"""
    h = hashlib.sha256()
    for r in sorted((dict(x) for x in rows), key=lambda x: int(x["id"])):
        h.update(("%d|%s|%s\n" % (int(r["id"]), r.get("name", ""), r.get("text", "")))
                 .encode("utf-8"))
    return h.hexdigest()

# ---------------------------------------------------------------------------
# P1 候选扫描 / 月份索引 / 低置信 fallback / 回热（纯函数；默认 off）
# ---------------------------------------------------------------------------
import re
from datetime import datetime

SCAN_DEFAULT_DAYS = 21
MONTH_INDEX_SCHEMA = "p1_month_index_v1"


def _parse_dt(s):
    try:
        return datetime.fromisoformat(str(s))
    except Exception:                                    # noqa: BLE001
        return None


def row_month(row):
    """月份：event_date 优先，其次 created_at（v1_local_naive）；无法解析返回 None。"""
    ed = str(row.get("event_date") or "")
    if len(ed) >= 7 and ed[4] == "-" and ed[:4].isdigit():
        return ed[:7]
    cd = str(row.get("created_at") or "")
    if len(cd) >= 7 and cd[4] == "-" and cd[:4].isdigit():
        return cd[:7]
    return None


def scan_candidates(rows, now_iso, days=SCAN_DEFAULT_DAYS, refs=None,
                    superseded=None, marks=None):
    """候选 = explicit_mark 或 superseded 或 (created_at 超期 且 无引用)。

    refs（sidecar 引用计数）只加 score/access_bonus，**不能单独触发**；
    不读 DB、不加列、不自动搬。
    """
    now = _parse_dt(now_iso) or datetime.now()
    refs = refs or {}
    superseded = superseded or {}
    marks = set(marks or [])
    out = []
    for r in rows:
        rid = int(r["id"])
        dt = _parse_dt(r.get("created_at"))
        age = (now - dt).days if dt else None
        expired = age is not None and age > int(days)
        ref = int(refs.get(rid, refs.get(str(rid), 0)) or 0)
        sup = superseded.get(rid, superseded.get(str(rid)))
        mark = rid in marks
        reasons = []
        if dt is None:
            reasons.append("created_at_unparsed")
        if expired:
            reasons.append("created_at_expired:%dd>%dd" % (age, int(days)))
        if sup is not None:
            reasons.append("superseded_by:%s" % sup)
        if mark:
            reasons.append("explicit_mark")
        if expired and ref == 0:
            reasons.append("no_refs")
        trigger = bool(mark or sup is not None or (expired and ref == 0))
        if not trigger:
            continue
        bonus = float(min(ref, 5))                 # access 只加分，不触发
        out.append({"id": rid, "reasons": reasons, "expired": expired,
                    "age_days": age, "refs": ref, "access_bonus": bonus,
                    "score": bonus, "month": row_month(r)})
    out.sort(key=lambda x: (-x["score"], x["id"]))
    return out


def month_index_from_archives(archives):
    """archives: [{zip, zip_sha256, entries:[{id,event_date,created_at}]}] -> index。"""
    months = {}
    for a in archives:
        zpath = a.get("zip")
        zsha = a.get("zip_sha256") or (sha_file(zpath) if zpath else None)
        for e in a.get("entries") or []:
            m = row_month({"event_date": e.get("event_date"),
                           "created_at": e.get("created_at")})
            if not m:
                continue
            slot = months.setdefault(m, {"zip": zpath, "zip_sha256": zsha,
                                         "ids": [], "has_event_date": False})
            slot["ids"].append(int(e["id"]))
            slot["has_event_date"] = bool(slot["has_event_date"] or e.get("event_date"))
    for v in months.values():
        v["ids"] = sorted(set(v["ids"]))
    return {"schema": MONTH_INDEX_SCHEMA, "months": dict(sorted(months.items()))}


def load_index(path):
    if not os.path.exists(path):
        return {"schema": MONTH_INDEX_SCHEMA, "months": {}}
    return json.load(open(path, encoding="utf-8"))


def save_index(index, path):
    assert_local_only([path])
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2, sort_keys=True)
    return path


def merge_index(index, archives):
    add = month_index_from_archives(archives)
    base = dict(index or {"schema": MONTH_INDEX_SCHEMA, "months": {}})
    months = dict(base.get("months") or {})
    for m, slot in add["months"].items():
        cur = months.get(m)
        if cur and cur.get("zip_sha256") != slot.get("zip_sha256"):
            # 同月多包：保留列表，仍以 sha 为准
            cur.setdefault("variants", []).append(
                {"zip": cur.get("zip"), "zip_sha256": cur.get("zip_sha256"),
                 "ids": cur.get("ids")})
            cur.update({"zip": slot["zip"], "zip_sha256": slot["zip_sha256"],
                        "ids": slot["ids"], "has_event_date": slot.get("has_event_date")})
        elif cur:
            cur["ids"] = sorted(set(cur.get("ids") or []) | set(slot["ids"]))
            cur["has_event_date"] = bool(cur.get("has_event_date")
                                         or slot.get("has_event_date"))
        else:
            months[m] = slot
    base["schema"] = MONTH_INDEX_SCHEMA
    base["months"] = dict(sorted(months.items()))
    return base


def verify_index(index):
    """恢复只认 sha：逐月校验 zip 存在且 sha 与记录一致。"""
    problems = []
    for m, slot in sorted((index.get("months") or {}).items()):
        z = slot.get("zip")
        if not z or not os.path.exists(z):
            problems.append("%s: zip 不存在 %r" % (m, z))
        elif sha_file(z) != slot.get("zip_sha256"):
            problems.append("%s: zip sha 不匹配" % m)
    return {"ok": not problems, "problems": problems}


EXPLICIT_MONTH_RE = re.compile(r"(20\d{2})[-/年](\d{1,2})")
RELATIVE_RE = re.compile(r"(去年|前年|上个月|上月)")


def fallback_months(query, index, max_months=2):
    """按时间词选月；相对时间且无 event_date -> unlocated + 只倒序盲搜。"""
    q = str(query or "")
    months = sorted((index.get("months") or {}).keys())
    sel, located, unlocated, strategy = [], False, False, "none"
    m = EXPLICIT_MONTH_RE.search(q)
    key = None
    if m:
        key = "%s-%02d" % (m.group(1), int(m.group(2)))
        if key in (index.get("months") or {}):
            sel, located, strategy = [key], True, "located_month"
        else:
            unlocated, strategy = True, "month_not_in_index"
    elif RELATIVE_RE.search(q):
        unlocated, strategy = True, "reverse_blind"
    else:
        unlocated, strategy = True, "blind_no_time"
    if not sel:
        sel = months[-max_months:][::-1]        # 倒序盲搜，最多 max_months
    out = []
    for mo in sel:
        slot = (index.get("months") or {}).get(mo) or {}
        z = slot.get("zip")
        sha_ok = bool(z and os.path.exists(z) and sha_file(z) == slot.get("zip_sha256"))
        out.append({"month": mo, "zip": z, "zip_sha256": slot.get("zip_sha256"),
                    "ids": slot.get("ids") or [], "sha_ok": sha_ok})
        if not sha_ok:
            located = False
    return {"query": q, "located": bool(located), "unlocated": bool(unlocated or not located),
            "strategy": strategy, "max_months": max_months, "months": out}


def reheat_plan(live_rows, zip_path, sidecar_path):
    """回热计划：同 subject+predicate 有更新 -> superseded_by；整链、只出 plan。"""
    plan = restore_plan(live_rows, zip_path, sidecar_path)
    summary = {"restore": sum(1 for x in plan["plan"] if x["action"] == "restore"),
               "superseded": sum(1 for x in plan["plan"]
                                 if x["action"] == "skip_superseded")}
    return {"schema": "p1_reheat_v1", "whole_chain": True,
            "zip_sha256": plan["zip_sha256"], "summary": summary,
            "plan": plan["plan"]}
