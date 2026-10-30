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