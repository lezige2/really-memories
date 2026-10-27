# T15 槽位接线片段（交接 rev7-impl；不重复定义，按需取用）

> 背景：`tools/memory_service.py` 的槽位数据层**完好**（sha16 `7dcc62a0bae75cfc` / 27,982 B），
> 只有 `tools/chat_daily.py` 因并发写事故丢失核心方法（见 `INCIDENT-CHATDAILY-T15.md`）。
> 本文只提供“数据层 API + chat_daily 接线参考代码”，供重建时复用；若 rev7-impl 已有
> `_canon_slots/_augment_slots/_canon_qslots` 设计，**以已有设计为准**，不要重复定义。

## 1 数据层 API（`tools/memory_service.py`，已就绪，勿改）

| API | 说明 |
|---|---|
| `SLOT_KEYS` | 12 键：time/person/event/place/action/object/cause/result/quantity/purpose/method/constraint |
| `UNVERIFIED_SLOT_KEYS` | cause/result/purpose/method/constraint（连接词类，抽不到=null）“未核实” |
| `extract_slots(text)` | 记忆原文 → 12 键 dict（缺省 None；不硬猜） |
| `unverified_slots(slots)` | 返回 null 的连接词类键（落库/日志用） |
| `query_slots(question)` | → `{want, slots:{time,event,place}, structured}`；`structured=False` 时**不得**做槽位过滤 |
| `slot_match(qslots, slots)` | time 硬过滤；event/place/person 冲突剔除（无值不拦）；want 槽位必须存在 |
| `slot_bonus(qslots, slots)` | event/place/person 加权 + quantity/cause/purpose/method 命中加分 |
| `filter_by_slots(rows, qslots, meta_fn)` | 批量过滤工具（可选） |

六个线上硬用例（`tools/test_slots_cpu.py` 已 43/0 覆盖语义）：
下周三→广州、下周五→成都、我叫什么→阿泽、组会在哪→B座302、养猫叫什么→豆豆、明天去哪→没提过。

## 2 落库（chat_daily：槽位放 `daily_memory_meta.slots`，原文 KV 块不动）

```python
def _ensure_meta(self):
    self.con.execute(
        "CREATE TABLE IF NOT EXISTS daily_memory_meta ("
        "source_id INTEGER PRIMARY KEY, tags TEXT, source TEXT, related_ids TEXT, "
        "slots TEXT)")
    cols = {r[1] for r in self.con.execute("PRAGMA table_info(daily_memory_meta)").fetchall()}
    if "slots" not in cols:                       # 旧库迁移（已有数据 slots=NULL）
        self.con.execute("ALTER TABLE daily_memory_meta ADD COLUMN slots TEXT")
    self.con.commit()

def _meta_get(self, sid):
    row = self.con.execute(
        "SELECT tags, source, related_ids, slots FROM daily_memory_meta "
        "WHERE source_id=?", (int(sid),)).fetchone()
    if not row:
        return {"tags": [], "source": "manual", "related_ids": [], "slots": {}}
    try:    slots = json.loads(row[3] or "{}")
    except (ValueError, IndexError): slots = {}
    return {"tags": [str(t) for t in json.loads(row[0] or "[]")],
            "source": row[1] or "manual",
            "related_ids": [int(x) for x in json.loads(row[2] or "[]")],
            "slots": slots if isinstance(slots, dict) else {}}

def _meta_set(self, sid, tags=None, source=None, related_ids=None, slots=None):
    cur = self._meta_get(sid)
    tags = cur["tags"] if tags is None else [str(t) for t in tags]
    source = cur["source"] if source is None else str(source)
    rel = cur["related_ids"] if related_ids is None else [int(x) for x in related_ids]
    sl = (cur.get("slots") or {}) if slots is None else dict(slots)
    self.con.execute(
        "INSERT INTO daily_memory_meta (source_id,tags,source,related_ids,slots) "
        "VALUES (?,?,?,?,?) ON CONFLICT(source_id) DO UPDATE SET tags=excluded.tags,"
        "source=excluded.source,related_ids=excluded.related_ids,slots=excluded.slots",
        (int(sid), json.dumps(tags, ensure_ascii=False), source,
         json.dumps(rel, ensure_ascii=False), json.dumps(sl, ensure_ascii=False)))
    self.con.commit()
    return {"tags": tags, "source": source, "related_ids": rel, "slots": sl}

def _slots_of(self, sid):
    meta = self._meta_get(sid)
    slots = meta.get("slots") or {}
    if not slots:                                # 兼容旧库：无 slots 时按原文现抽
        row = self._row_by_id(sid)
        if row is not None:
            slots = memo.extract_slots(row[3])
    return slots
```

写入（`_insert_memory_block` 内，原文块/归档块/摘要块同一条路径）：
```python
slots = memo.extract_slots(text)
put = self._put_memory_source(text, label=label, mode=mode)
...
meta = self._meta_set(sid, tags=(tags or []), source=src_kind,
                      related_ids=(related_ids or []), slots=slots)
# 返回值附： "slots": meta["slots"], "slots_unverified": memo.unverified_slots(meta["slots"])
```

## 3 检索叠加（`_retrieval_select`，重建时可直接重放这段）

叠加顺序：**time 硬过滤 → event/place/person 加权/冲突剔除 → quantity/cause/purpose/method 加分
→ 同时间（structured）取最新 id → 挂原文块**。

```python
def _retrieval_select(self, text):
    rows = self._rows()
    self._last_candidate_count = 0
    self._last_related_count = 0
    self._last_qslots = memo.query_slots(text)          # 先解析问句槽位
    if not rows:
        return []
    toks = memo.tokens(text)
    if not toks:
        return []
    structured = bool(self._last_qslots.get("structured"))
    cand = self.topk * 3 if structured else self.topk   # 结构化时放大候选池，避免正确块被 topk 截掉
    base, stats = memo.retrieve(text, rows, topk=cand, meta_fn=self._meta_get, return_stats=True)
    self._last_candidate_count = int(stats.get("candidates") or 0)
    if not base:
        fb = self._retrieval_keyword_fallback(text)
        if fb:
            self._last_candidate_count = max(self._last_candidate_count, len(fb))
        return fb
    by_id = {int(r[0]): r for r in rows}
    scored = []
    for b in base:
        sid = int(b["id"]); r = by_id.get(sid)
        if r is None:
            continue
        slots = self._slots_of(sid)
        if not memo.slot_match(self._last_qslots, slots):   # time 硬过滤/want 必须/事件冲突剔除
            continue
        bonus = memo.slot_bonus(self._last_qslots, slots)   # 事件/地点/人物加权
        scored.append((bonus, float(b["score"]), sid, r, b, slots))
    # structured（有 time/事件/姓名）同分取最新 id；否则保持 id 升序（不破坏旧排序）
    scored.sort(key=lambda x: (-x[0], -x[1], -x[2] if structured else x[2]))
    out, chosen = [], set()
    for bonus, bscore, sid, r, b, slots in scored[:self.topk]:
        out.append({"name": r[1], "score": float(bscore), "source_id": sid,
                    "signals": {"hits": b["hits"][:6], "tags": b["tag_hits"][:4],
                                "related": False, "library": len(rows),
                                "slot_bonus": bonus,
                                "slots": {k: v for k, v in slots.items() if v}}})
        chosen.add(sid)
    # 1 跳关联扩展（related_ids/同标签）保持旧实现；每条同样用 _slots_of 过滤/加分即可
    ...
```

`_retrieval_keyword_fallback`（词面兜底）同样叠加；另外去掉“必须含‘我’”的旧限制，
让“养猫叫什么/组会在哪”这类结构化问句也能走兜底：

```python
q = str(text or "")
qslots0 = memo.query_slots(q)
if "我" not in q and not qslots0.get("structured"):
    return []
...
# 命中后：
qslots = qslots0
if qslots.get("structured"):
    kept = []
    for sc, r, matched in hits:
        slots = self._slots_of(int(r[0]))
        if memo.slot_match(qslots, slots):
            kept.append((sc + memo.slot_bonus(qslots, slots), r, matched))
    hits = kept
if qslots.get("structured"):
    hits.sort(key=lambda x: (-x[0], -int(x[1][0])))   # 同时间取最新 id
else:
    hits.sort(key=lambda x: (-x[0], int(x[1][0])))
```

`ask`/`_ask_natural` 的 retrieval 调试字段可选加：`retrieval["slots"] = self._last_qslots`。

## 4 重建后自检（建议原样跑）

```bat
python -X utf8 -c "import sys;sys.path.insert(0,'tools');import chat_daily"
python -X utf8 -c "import sys;sys.path.insert(0,'tools');import chat_daily as D;ms=['_rows','_row_by_id','_rows_for_selection','_fit_budget','_sync_mounts','_unmount_all','_select','_retrieval_select','_product_fact_question','_history_text','_total_tokens','_put_memory_source','_rollback_source','_local_time_reply','_web_answer','_explicit_search'];print([m for m in ms if not hasattr(D.DailyApp,m)])"
python -X utf8 tools/test_slots_cpu.py        # 期望 43/0
python -X utf8 tools/test_chat_daily_cpu.py   # 期望 93/0（若测试随重建更新则以新值为准）
python -X utf8 tools/test_retrieval_cpu.py
python -X utf8 tools/test_refusal_cpu.py
python -X utf8 tools/test_rollover_cpu.py
```
冒烟（fake engine）：`ask("你好")`、`ask("我下周三去哪开会？")`、`/status`；服务 `/health` 由 LEAD 重启后验。