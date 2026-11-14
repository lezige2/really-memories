# -*- coding: utf-8 -*-
"""P1b：主体键 + 写时软覆盖（sidecar；不改 daily/块/原文）。

- sidecar：`<dir>/<db_sha16>.subjects.json`，键=块 id，含 text sha；由块文本+确定性规则重建；
  删 sidecar 即回现网行为，不成为第二真相源。
- 写时：同 (subject,predicate) 值变化 + cue/created_at 锚点 -> `supersedes`（不删块）；
  无 cue / 主体判不出 / 车号卡族“换成/换到”主体不一致 -> 追问（复用 confirm token）。
- 同秒冲突：created_at 相同取 id 大者；按 (tenant,subject,predicate) 串行化。
"""

import hashlib
import json
import os
import re
import threading
import time

SCHEMA = "p1b_subject_v1"
CUE_RE = re.compile(r"改成|换成|换到|改为|更新为|现在是|现在用|目前是|最新是|改到|已搬到")
NEG_CUE_RE = re.compile(r"已经不在|已离职|已退|搬走|搬离|送人|不养|退了|退掉|注销|不再用|不要了|取消")
# C02：新实体标记——绝不覆盖现有同族，必须追问
NEW_ENTITY_RE = re.compile(
    r"又买了一辆|又买了|新买|再买|第二辆|另一辆|又办了一张卡|又办一张卡|"
    r"再办一张|又开了一个号|又开一个号|新办|新增一辆|另外一个号")
FAMILIES = ("车牌", "手机", "银行卡", "车色", "车型", "公司", "老家", "会议",
            "健身", "工位", "猫", "狗", "邮箱", "过敏")
FAMILY_PATTERNS = {
    "车牌": (r"车牌", r"车号", r"牌子", r"挂的牌", r"牌照", r"牌是"),
    "手机": (r"手机", r"电话", r"号码", r"工作号", r"私人号", r"备用号", r"常用号"),
    "银行卡": (r"银行卡", r"卡号", r"尾号", r"工资卡", r"储蓄卡", r"信用卡", r"会员卡", r"会员"),
    "车色": (r"颜色", r"车漆", r"色"),
    "车型": (r"车型", r"两厢", r"三厢", r"suv", r"mpv", r"轿车", r"越野"),
    "公司": (r"公司", r"单位", r"上班", r"跳槽", r"离职", r"辞职", r"入职"),
    "老家": (r"老家", r"故乡"),
    "会议": (r"会议", r"开会", r"组会", r"例会", r"那个会", r"个会", r"会定在", r"会安排"),
    "健身": (r"健身",),
    "工位": (r"工位", r"座位", r"办公位", r"搬到", r"调到", r"搬走", r"搬离"),
    "猫": (r"猫",),
    "狗": (r"狗",),
    "邮箱": (r"邮箱", r"@"),
    "过敏": (r"过敏",),
}
_VALUE_PATTERNS = {
    "车牌": (r"[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼]"
             r"[A-HJ-NP-Z][A-HJ-NP-Z0-9]{5}",),
    "手机": (r"1[3-9]\d(?:[-\s]?\d){8}",),
    "银行卡": (r"(?<!\d)\d{4,6}(?!\d)",),
    "车色": (r"(白|黑|蓝|红|灰|银|香槟|绿|黄|紫)色?",),
    "车型": (r"(两厢|三厢|SUV|MPV|轿车|越野)",),
    "公司": (r"(?:是|在|叫)(?:在)?([\u4e00-\u9fff]{2,24}?(?:股份有限公司|有限责任公司|有限公司|集团|银行|学校))",
             r"(?:在|是|去|到)([\u4e00-\u9fff]{2,6})(?:上班|公司|工作|了)",
             r"(?:公司|单位)(?:是|在|叫)([\u4e00-\u9fff]{2,6})",
             r"从([\u4e00-\u9fff]{2,6})(?:离职|辞职|毕业)"),
    "老家": (r"(?:老家|故乡)(?:其实)?(?:在|是)([\u4e00-\u9fff]{2,4})",),
    "工位": (r"[A-Za-z]座\s*\d+", r"\d+层\s*\d+号", r"[A-Za-z]-\d+",
             r"[A-Za-z]区\s*\d+号?", r"\d+排\s*\d+号?"),
    "猫": (r"(?:叫|名叫|名字是|改名成|改名叫|又改叫)([\u4e00-\u9fff]{2,4})",),
    "狗": (r"(?:叫|名叫|名字是|改名成|改名叫|又改叫)([\u4e00-\u9fff]{2,4})",),
    "邮箱": (r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+",),
    "过敏": (r"(?:对)?([\u4e00-\u9fff]{2,4})过敏",),
    "会议": (r"(\d+楼|[A-Za-z]座\s*\d+|\d+层|晚上\s*[\d一二三四五六七八九十]+点)",
             r"(\d{4}-\d{1,2}-\d{1,2}(?:\s*\d{1,2}:\d{2})?)"),
    "健身": (r"(周[一二三四五六日天]|\d+点)",),
}
_OWNER_TERMS = (("特斯拉", ("特斯拉",)), ("比亚迪", ("比亚迪",)),
                ("工作", ("工作号", "工作邮箱", "工作手机", "工作")),
                ("私人", ("私人号", "私人")), ("父亲", ("父亲", "爸爸")),
                ("母亲", ("母亲", "妈妈")), ("爱人", ("爱人", "老婆")))
_NAME_RE = re.compile(r"([\u4e00-\u9fff]{2,3})(?:的|家|养的|养)")
_SURNAMES = set("王李张刘陈杨黄赵吴周徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯邓曹彭曾肖田董袁潘于蒋蔡余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方白邹孟熊秦邱江尹薛闫段雷侯龙史陶黎贺顾毛郝龚邵万钱严覃武戴莫孔向汤")

_LOCK = threading.RLock()
_KEY_LOCKS = {}


def sha_text(t):
    return hashlib.sha256(str(t or "").encode("utf-8")).hexdigest()


def db_sha16(db_path):
    try:
        h = hashlib.sha256(open(db_path, "rb").read()).hexdigest()
        return h[:16]
    except OSError:
        return "nodb"


def sidecar_path(db_path, root=None):
    root = root or os.environ.get("P1B_SIDECAR_DIR") or os.path.join("out", "p1b", "sidecar")
    return os.path.join(root, "%s.subjects.json" % db_sha16(db_path))


def _norm(v):
    return re.sub(r"[\s,，。．.、:：;；!！?？\-—_·]+", "", str(v or "")).lower()


def extract(text):
    """确定性抽 (subject, predicate, value, subject_source)。"""
    t = str(text or "")
    low = t.lower()
    family, value = None, ""
    for fam in FAMILIES:
        if any(re.search(p, low) for p in FAMILY_PATTERNS[fam]):
            family = fam
            break
    if not family:
        return None
    blob = re.sub(r"[\s,，。．.、:：;；!！?？\-—_·]+", "", t)
    if family == "银行卡":
        m = re.search(r"\d{12,19}", blob)          # 长卡号优先取尾 4
        if m:
            value = m.group(0)[-4:]
    for pat in (_VALUE_PATTERNS.get(family, ()) if not value else ()):
        m = re.search(pat, blob, re.I) or re.search(pat, t, re.I)
        if m:
            value = m.group(1) if m.groups() else m.group(0)
            break
    if not value and family == "银行卡":
        m = re.search(r"\d{12,19}", blob)          # 长卡号 -> 尾 4
        if m:
            value = m.group(0)[-4:]
    if not value and NEG_CUE_RE.search(t):
        value = "__removed__"                      # 移除/离开：值哨兵，只许追问
    subject, source = None, "none"
    for name, terms in _OWNER_TERMS:
        if any(x in t for x in terms):
            subject, source = name, "lexicon"
            break
    if subject is None and re.match(r"^(我|俺|本人)", t.strip()):
        subject, source = "self", "self"
    if subject is None:
        m = _NAME_RE.search(t)
        if m and m.group(1)[0] in _SURNAMES:
            subject, source = "name:" + m.group(1), "possessive"
    return {"subject": subject, "predicate": family, "value": value,
            "subject_source": source}


def _key(rec):
    return (str(rec.get("subject") or ""), str(rec.get("predicate") or ""))


class Sidecar:
    def __init__(self, path):
        self.path = path
        self.data = {"schema": SCHEMA, "entries": {}, "stats": {
            "same_second_conflict": 0, "serial_conflict": 0}}

    def load(self):
        try:
            d = json.load(open(self.path, encoding="utf-8"))
            if d.get("schema") == SCHEMA:
                self.data = d
        except (OSError, ValueError):
            pass
        return self

    def save(self):
        os.makedirs(os.path.dirname(os.path.abspath(self.path)) or ".", exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2, sort_keys=True)
        os.replace(tmp, self.path)

    def entries(self):
        return {int(k): v for k, v in (self.data.get("entries") or {}).items()}

    def rebuild(self, rows):
        """从块文本重建；text sha 不匹配的条目作废（键=块 id）。"""
        entries = {}
        for r in rows:
            rid, text = int(r[0]), str(r[3])
            info = extract(text)
            if not info or not info.get("value"):
                continue
            entries[str(rid)] = {"block_id": rid, "text_sha256": sha_text(text),
                                 "created_at": str(r[8]) if len(r) > 8 else "",
                                 "subject": info["subject"],
                                 "predicate": info["predicate"],
                                 "value": info["value"],
                                 "subject_source": info["subject_source"],
                                 "supersedes": None, "superseded_by": None,
                                 "ambiguous": False}
        old = self.entries()
        for rid, ent in entries.items():                 # 保留已有 supersedes 链
            if rid in old and old[rid].get("text_sha256") == ent["text_sha256"]:
                ent["supersedes"] = old[rid].get("supersedes")
                ent["superseded_by"] = old[rid].get("superseded_by")
                ent["ambiguous"] = old[rid].get("ambiguous", False)
        self.data["entries"] = {str(k): v for k, v in sorted(entries.items())}
        return self

    def latest(self, subject, predicate):
        cands = [e for e in self.entries().values()
                 if e.get("subject") == subject and e.get("predicate") == predicate
                 and not e.get("ambiguous")]
        return max(cands, key=lambda e: (str(e.get("created_at") or ""),
                                         int(e["block_id"]))) if cands else None

    def mark(self, new_id, text, created_at, supersedes=None, ambiguous=False):
        rid = int(new_id)
        cur = self.entries().get(rid) or {}
        self.data["entries"][str(rid)] = {
            **cur, "block_id": rid, "text_sha256": sha_text(text),
            "created_at": created_at, "supersedes": supersedes,
            "ambiguous": bool(ambiguous),
            "value": (extract(text) or {}).get("value", cur.get("value")),
            "subject": (extract(text) or {}).get("subject", cur.get("subject")),
            "predicate": (extract(text) or {}).get("predicate", cur.get("predicate")),
        }
        if supersedes is not None:
            old = self.data["entries"].get(str(int(supersedes)))
            if old is not None:
                old["superseded_by"] = rid
        self.save()
        return self


def decide(text, created_at, side, tenant="default"):
    """-> {action: write|same_value|supersede|ask, ...}；不确定一律 ask。"""
    info = extract(text)
    if not info or not info.get("value") or not info.get("predicate"):
        return {"action": "write"}
    key = _key(info)
    if NEW_ENTITY_RE.search(text):
        same_pred = [e for e in side.entries().values()
                     if e.get("predicate") == info["predicate"]]
        if same_pred:
            return {"action": "ask", "reason": "new_entity",
                    "candidates": len(same_pred), "info": info}
    latest = side.latest(*key)
    if NEG_CUE_RE.search(text):
        return {"action": "ask", "reason": "negative_cue",
                "candidates": 1, "info": info}
    if not info.get("subject"):
        same_pred = [e for e in side.entries().values()
                     if e.get("predicate") == info["predicate"]]
        if same_pred:
            return {"action": "ask", "reason": "ambiguous_subject",
                    "candidates": len(same_pred), "info": info}
    if info.get("value") == "__removed__":
        return {"action": "ask", "reason": "negative_cue",
                "candidates": 1, "info": info}
    if latest is None:
        return {"action": "write", "info": info}
    if _norm(latest.get("value")) == _norm(info["value"]):
        return {"action": "same_value", "target": latest["block_id"]}
    if not info.get("subject"):
        return {"action": "ask", "reason": "ambiguous_subject",
                "candidates": 1, "info": info}
    fam = info["predicate"]
    if fam in ("车牌", "手机", "银行卡") and CUE_RE.search(text) \
            and info["subject_source"] not in ("lexicon", "self", "possessive"):
        return {"action": "ask", "reason": "subject_conflict",
                "candidates": 1, "info": info}
    if CUE_RE.search(text):
        target = latest["block_id"]
        if str(latest.get("created_at") or "") == str(created_at):
            side.data["stats"]["same_second_conflict"] += 1
        return {"action": "supersede", "target": target, "info": info,
                "reason": "cue"}
    if str(created_at) > str(latest.get("created_at") or ""):
        return {"action": "supersede", "target": latest["block_id"],
                "info": info, "reason": "anchor"}
    return {"action": "ask", "reason": "no_cue", "candidates": 1, "info": info}


def key_lock(tenant, subject, predicate):
    k = (tenant, subject, predicate)
    with _LOCK:
        return _KEY_LOCKS.setdefault(k, threading.RLock())


def latest_ids(side):
    """每个 (subject,predicate) 只留最新的块 id（读侧过滤用）。"""
    groups = {}
    for e in side.entries().values():
        if e.get("ambiguous"):
            continue
        groups.setdefault(_key(e), []).append(e)
    keep = set()
    for ents in groups.values():
        keep.add(max(ents, key=lambda e: (str(e.get("created_at") or ""),
                                          int(e["block_id"])))["block_id"])
    return keep


def superseded_ids(side):
    return {int(e["block_id"]) for e in side.entries().values()
            if e.get("superseded_by") is not None}