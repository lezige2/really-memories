# -*- coding: utf-8 -*-
"""memory_source.py -- the authoritative layer.

Three layers, and exactly one of them is allowed to be the truth:

    memory_source   source text          AUTHORITATIVE, immutable, never in the prompt
        |
        v
    memory_block    .kvmem state file    DERIVED -- a cache. may be deleted and rebuilt.
        |
        v
    (facet index)   pointers + facets    DERIVED -- never holds the text either

This exists because a KV block is *lossy and wear-limited*: it is a q8_0 snapshot, it
degrades after ~10 round trips of re-rotation (measured, see kv_audit.py drift), and it
is bound to one model/rope/kv-type combination. Treating the block file as the only copy
means a model upgrade or a worn block destroys the memory permanently. The block is a
cache of the source, and caches are disposable.

Guarantees this module enforces (not just documents):

  * memory_source.text is immutable -- a BEFORE UPDATE trigger aborts any attempt.
    A changed text is a NEW row (new id), so an old block keeps pointing at the text
    it was actually built from.
  * every block row records the model fingerprint, kv type and state format version
    it was built with. load_into() refuses a mismatch with an explicit error instead
    of letting the engine fail somewhere deep.
  * text is never returned to a caller that builds a prompt. Only `probe_text()` hands
    the text back, and it is explicitly named to keep it out of the ask path.

Usage:
  python tools/memory_source.py init
  python tools/memory_source.py put --name profile --label 档案 --text-file a.txt
  python tools/memory_source.py build
  python tools/memory_source.py list
  python tools/memory_source.py verify
  python tools/memory_source.py rebuild --name profile
"""
import argparse
import hashlib
import os
import re
import sqlite3
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

MODEL = r"D:\models\DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf"
DB = os.path.join(ROOT, "kvmem", "chat.db")
BLOCKS = os.path.join(ROOT, "kvmem", "blocks")

# bump when the .kvmem payload layout changes; blocks with another value are stale
STATE_VERSION = 1

SCRATCH_SEQ = 1        # sequence used to encode a block at position 0

SCHEMA = """
CREATE TABLE IF NOT EXISTS memory_source (
    id            INTEGER PRIMARY KEY,
    tenant        TEXT    NOT NULL DEFAULT 'default',
    scope         TEXT    NOT NULL DEFAULT 'private',
    mode          TEXT    NOT NULL DEFAULT 'chat',
    name          TEXT    NOT NULL,
    label         TEXT    NOT NULL,
    text          TEXT    NOT NULL,
    source_hash   TEXT    NOT NULL,
    created_at    TEXT    NOT NULL,
    -- I8: a DEFAULT is a silent decision. Both of these default to the REFUSAL state, so a
    -- row that forgets to declare what it is lands on the wrong side of the M5 gate rather
    -- than being silently admitted as human memory.
    text_kind            TEXT    NOT NULL DEFAULT 'conversation'
                         CHECK (text_kind IN ('human_memory', 'conversation')),
    contains_model_turns INTEGER NOT NULL DEFAULT 1
                         CHECK (contains_model_turns IN (0, 1)),
    is_excerpt           INTEGER NOT NULL DEFAULT 0
                         CHECK (is_excerpt IN (0, 1)),
    derived_from         TEXT,
    -- a human memory may not carry model turns; a conversation may (an all-user transcript
    -- is a conversation with 0 turns, which is safe and must stay expressible)
    CHECK (NOT (text_kind = 'human_memory' AND contains_model_turns = 1)),
    CHECK (is_excerpt = 0 OR derived_from IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS memory_source_lookup
    ON memory_source (tenant, scope, name);

CREATE TRIGGER IF NOT EXISTS memory_source_text_is_immutable
BEFORE UPDATE OF text, source_hash ON memory_source
BEGIN
    SELECT RAISE(ABORT,
        'memory_source.text is immutable: insert a new row instead of editing history');
END;

CREATE TABLE IF NOT EXISTS memory_block (
    source_id     INTEGER PRIMARY KEY REFERENCES memory_source(id) ON DELETE CASCADE,
    path          TEXT    NOT NULL,
    n_tokens      INTEGER NOT NULL,
    n_bytes       INTEGER NOT NULL,
    built_at      TEXT    NOT NULL,
    model_path    TEXT    NOT NULL,
    model_size    INTEGER NOT NULL,
    model_mtime   INTEGER NOT NULL,
    kv_type       TEXT    NOT NULL,
    state_version INTEGER NOT NULL
);
"""


class Incompatible(Exception):
    """The block on disk cannot be trusted for the current model / engine."""


class SourceConflict(Exception):
    """A name already has a different text. Revisions are explicit, never implicit.

    Silently appending a revision makes every block built from the old row point at text
    that get_source() no longer returns -- the copies drift apart with no error anywhere.
    Pass revise=True when a new revision is really intended.
    """

    def __init__(self, name, old_hash, new_hash):
        self.name, self.old_hash, self.new_hash = name, old_hash, new_hash
        Exception.__init__(
            self,
            "source %r already exists with sha256 %s; refusing to add sha256 %s. "
            "Revisions are explicit: pass revise=True (or --revise) to append a new row."
            % (name, old_hash[:16], new_hash[:16]))


class SourceHashMismatch(Exception):
    """Stored text and stored source_hash disagree: the row cannot be trusted."""

    def __init__(self, name, sid, stored, computed):
        self.name, self.id, self.stored, self.computed = name, sid, stored, computed
        Exception.__init__(
            self,
            "source %r (id=%r): stored source_hash %s != sha256(text) %s -- the text was "
            "changed behind the immutability trigger; refusing to hand it out."
            % (name, sid, stored[:16], computed[:16]))


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def model_fp(model_path):
    st = os.stat(model_path)
    return {"model_path": model_path, "model_size": st.st_size,
            "model_mtime": int(st.st_mtime)}


def connect(path=None):
    path = path or DB
    os.makedirs(os.path.dirname(path), exist_ok=True)
    con = sqlite3.connect(path)
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA)
    con.commit()
    return con


# ---------------------------------------------------------------------------
# write path: source first (authoritative), then the block (derived)
# ---------------------------------------------------------------------------
def put_source(con, name, label, text, tenant="default", scope="private",
               mode="chat", revise=False):
    """Insert the authoritative row. Idempotent on (tenant, scope, name, hash).

    Idempotent means same name + same text returns the existing id and writes nothing.
    A DIFFERENT text under an existing name raises SourceConflict unless revise=True:
    history is append-only, so a block always points at the exact text it was built
    from -- and an unannounced second revision is how two copies start drifting.
    """
    if not text or not text.strip():
        raise ValueError("source %r: refusing to store an empty text" % (name,))
    h = sha256_text(text)
    row = con.execute(
        "SELECT id FROM memory_source WHERE tenant=? AND scope=? AND name=? AND source_hash=?",
        (tenant, scope, name, h)).fetchone()
    if row:
        return row[0], False
    prev = con.execute(
        "SELECT id, source_hash FROM memory_source WHERE tenant=? AND scope=? AND name=? "
        "ORDER BY id DESC LIMIT 1", (tenant, scope, name)).fetchone()
    if prev and not revise:
        raise SourceConflict(name, prev[1], h)
    cur = con.execute(
        "INSERT INTO memory_source (tenant,scope,mode,name,label,text,source_hash,created_at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (tenant, scope, mode, name, label, text, h,
         datetime.now().isoformat(timespec="seconds")))
    con.commit()
    return cur.lastrowid, True


def get_source(con, name, tenant="default", scope="private", verify_hash=True):
    """Newest revision for a name, or None.

    The row is checked against its own hash before it is handed out. This is the read
    path every consumer uses, so a mutated row fails here instead of flowing on as
    plausible text; there is deliberately no try/except around it anywhere.
    """
    row = con.execute(
        "SELECT id,tenant,scope,mode,name,label,text,source_hash,created_at "
        "FROM memory_source WHERE tenant=? AND scope=? AND name=? "
        "ORDER BY id DESC LIMIT 1", (tenant, scope, name)).fetchone()
    if row and verify_hash:
        _verify_row(row)
    return row


def _verify_row(row):
    sid, _t, _s, _m, name, _lbl, text, sh, _ts = row
    computed = sha256_text(text)
    if computed != sh:
        raise SourceHashMismatch(name, sid, sh, computed)


class SourceNotAllowed(Exception):
    """A source that carries model turns may never become an M5 grounding source."""


def assert_m5_source_allowed(con, name):
    """R15: M5 sources accept human memory with no model turns -- nothing else.

    Both columns are checked: text_kind alone would pass a row that declares 'human_memory'
    but still carries turns, and that is exactly the pair-of-half-truths this gate exists to
    stop.
    """
    rows = list(con.execute("SELECT id, text_kind, contains_model_turns FROM memory_source "
                            "WHERE name=? ORDER BY id DESC", (name,)))
    if not rows:
        raise ValueError("no registry row named %r" % (name,))
    sid, kind, turns = rows[0]
    if kind != "human_memory" or turns != 0:
        raise SourceNotAllowed(
            "source %r (id=%r) is text_kind=%r, contains_model_turns=%r: it may serve as "
            "text_origin provenance, never as an M5 grounding source (a model turn would be "
            "treated as 'the source says so')." % (name, sid, kind, turns))
    return {"name": name, "registry_source_id": sid, "text_kind": kind,
            "contains_model_turns": turns}


def assert_unique_texts(con):
    """I1: one canonical row per text -- scoped by (text_kind, is_excerpt).

    An excerpt row repeats its container's bytes on purpose (it IS a span of it), so a flat
    "one row per text" rule would forbid the excerpt layer outright. The invariant is:

      * inside one (text_kind, is_excerpt) layer: exactly one row per text;
      * across layers: every excerpt must name a container whose text really contains it,
        otherwise "layered dedupe" would just be invisible duplication.

    Returns {"layers": {...}, "texts": {sha256: [names]}}.
    """
    cols = set(r[1] for r in con.execute("PRAGMA table_info(memory_source)"))
    layered = {"text_kind", "is_excerpt", "derived_from"} <= cols
    sql = ("SELECT id, name, text, source_hash, text_kind, is_excerpt, derived_from "
           "FROM memory_source ORDER BY id") if layered else \
          ("SELECT id, name, text, source_hash, 'human_memory', 0, NULL "
           "FROM memory_source ORDER BY id")
    seen, rows, flat = {}, {}, {}
    for sid, name, text, sh, kind, exc, derived in con.execute(sql):
        computed = sha256_text(text)
        if computed != sh:
            raise SourceHashMismatch(name, sid, sh, computed)
        seen.setdefault((kind, exc), {}).setdefault(computed, []).append("%s#%d" % (name, sid))
        flat.setdefault(computed, []).append("%s#%d" % (name, sid))
        rows[sid] = {"id": sid, "name": name, "text": text, "sha": computed,
                     "text_kind": kind, "is_excerpt": exc, "derived_from": derived}

    dupes = [("%s/is_excerpt=%s" % k, v) for k, layer in seen.items()
             for v in layer.values() if len(v) > 1]
    if dupes:
        raise AssertionError("the same text is stored more than once inside one layer: %r"
                             % (dupes,))

    for r in rows.values():
        if not r["is_excerpt"]:
            continue
        if not r["derived_from"]:
            raise AssertionError("excerpt %s#%d declares no derived_from container"
                                 % (r["name"], r["id"]))
        cname, _, csha16 = r["derived_from"].rpartition("@")
        cont = [c for c in rows.values() if c["name"] == cname and not c["is_excerpt"]]
        if len(cont) != 1:
            raise AssertionError("excerpt %s#%d names container %r, but that is not one "
                                 "non-excerpt row" % (r["name"], r["id"], cname))
        cont = cont[0]
        if not cont["sha"].startswith(csha16):
            raise AssertionError("excerpt %s#%d declares container sha %s but %s hashes %s"
                                 % (r["name"], r["id"], csha16, cname, cont["sha"][:16]))
        if r["text"] not in cont["text"]:
            raise AssertionError("excerpt %s#%d is not a verbatim substring of container %s"
                                 % (r["name"], r["id"], cname))
    return {"layers": dict(("%s/is_excerpt=%s" % k, v) for k, v in seen.items()),
            "texts": flat}


def indexable_sources(con):
    """Source rows a block builder may index: human memory that is not a span.

    Stage 2: the registry is the authority, so the builder reads rows instead of a literal
    in the caller. A conversation transcript is excluded because it carries model turns,
    and an excerpt is excluded because it is already inside its container.
    """
    cols = set(r[1] for r in con.execute("PRAGMA table_info(memory_source)"))
    layered = {"text_kind", "is_excerpt", "derived_from"} <= cols
    sql = ("SELECT name, label, text FROM memory_source WHERE text_kind='human_memory' "
           "AND contains_model_turns=0 AND is_excerpt=0 ORDER BY id") if layered else \
          ("SELECT name, label, text FROM memory_source ORDER BY id")
    return [tuple(r) for r in con.execute(sql)]


def probe_text(con, source_id):
    """The text of a source row.

    Deliberately named so that nothing on the ask path calls it: this module is the
    only place allowed to hand the raw memory back, and it is used for rebuild and
    for grounding checks -- never to build a prompt.
    """
    r = con.execute(
        "SELECT id,tenant,scope,mode,name,label,text,source_hash,created_at "
        "FROM memory_source WHERE id=?", (source_id,)).fetchone()
    if not r:
        raise KeyError("no source row %r" % (source_id,))
    _verify_row(r)
    return r[6]


def build_block(eng, con, src_row, blocks_dir=None, kv_type="q8_0", model_path=MODEL,
                seq=None):
    """Encode the source at position 0 and save the state file. Returns a dict.

    `seq` exists because the caller may already be using SCRATCH_SEQ for a live block
    (a restore rebuilds while other blocks sit in their own sequences).
    """
    seq = SCRATCH_SEQ if seq is None else seq
    blocks_dir = blocks_dir or BLOCKS
    os.makedirs(blocks_dir, exist_ok=True)
    sid, _tenant, _scope, _mode, name, _label, text, _h, _ts = src_row

    eng.reset(seq)
    eng.write_at(seq, text, 0)
    n = eng.n_tokens(seq)
    path = os.path.join(blocks_dir, name + ".kvmem")
    nb = eng.save(seq, path)
    if nb <= 0:
        raise RuntimeError("save produced %r bytes for %s" % (nb, name))
    eng.reset(seq)

    fp = model_fp(model_path)
    con.execute(
        "INSERT INTO memory_block (source_id,path,n_tokens,n_bytes,built_at,"
        "model_path,model_size,model_mtime,kv_type,state_version) VALUES (?,?,?,?,?,?,?,?,?,?) "
        "ON CONFLICT(source_id) DO UPDATE SET path=excluded.path,n_tokens=excluded.n_tokens,"
        "n_bytes=excluded.n_bytes,built_at=excluded.built_at,model_path=excluded.model_path,"
        "model_size=excluded.model_size,model_mtime=excluded.model_mtime,"
        "kv_type=excluded.kv_type,state_version=excluded.state_version",
        (sid, path, n, nb, datetime.now().isoformat(timespec="seconds"),
         fp["model_path"], fp["model_size"], fp["model_mtime"], kv_type, STATE_VERSION))
    con.commit()
    return {"source_id": sid, "name": name, "path": path, "n_tokens": n, "n_bytes": nb}


# ---------------------------------------------------------------------------
# read path
# ---------------------------------------------------------------------------
def block_rows(con, tenant="default", scope="private"):
    return con.execute(
        "SELECT s.id,s.name,s.label,s.text,s.source_hash,"
        "       b.source_id,b.path,b.n_tokens,b.n_bytes,b.model_path,b.model_size,"
        "       b.model_mtime,b.kv_type,b.state_version "
        "FROM memory_source s LEFT JOIN memory_block b ON b.source_id = s.id "
        "WHERE s.tenant=? AND s.scope=? ORDER BY s.id", (tenant, scope)).fetchall()


def check_compatible(row, model_path=MODEL, kv_type="q8_0"):
    """Raise Incompatible unless the artifact matches this model/engine."""
    (_sid, name, _label, _text, _sh,
     bid, path, n_tokens, n_bytes, m_path, m_size, m_mtime, b_kv, s_ver) = row
    if bid is None:
        raise Incompatible("%s: no block built yet (run build)" % name)
    if not os.path.exists(path):
        raise Incompatible("%s: block file missing (%s)" % (name, path))
    if os.stat(path).st_size != n_bytes:
        raise Incompatible("%s: block file truncated (%d != %d bytes)"
                           % (name, os.stat(path).st_size, n_bytes))
    if s_ver != STATE_VERSION:
        raise Incompatible("%s: state format v%r != v%r" % (name, s_ver, STATE_VERSION))
    if b_kv != kv_type:
        raise Incompatible("%s: built with kv=%s, engine is %s" % (name, b_kv, kv_type))
    fp = model_fp(model_path)
    if (m_path, m_size, m_mtime) != (fp["model_path"], fp["model_size"], fp["model_mtime"]):
        raise Incompatible("%s: built with a different model (%s, %d B, mtime %d)"
                           % (name, m_path, m_size, m_mtime))


def load_into(eng, row, seq, model_path=MODEL, kv_type="q8_0"):
    """Compat-check, then load, then insist the engine accepted it."""
    check_compatible(row, model_path, kv_type)
    n = eng.load(seq, row[6])
    if n < 0:
        raise Incompatible("%s: engine refused the state file (model/rope/n_rot_k/kv "
                           "type mismatch)" % row[1])
    return n


def classify(con, blocks_dir=None, model_path=MODEL, kv_type="q8_0"):
    """Three states, because "a warning" is not a state.

      managed  source + block, compatible, file present -- read/write, rebuildable
      legacy   a block exists with no source row -- READ ONLY. It can never be rebuilt
               (its text is gone), which is exactly the cost the source layer removes.
      orphan   an index entry whose file is missing -- FAIL CLOSED, never attach.

    A source that has not been built yet is reported separately as `unbuilt`: that is
    not a broken block, it is work not done yet.
    """
    blocks_dir = blocks_dir or BLOCKS
    managed, legacy, orphan, unbuilt, broken = [], [], [], [], []

    for r in block_rows(con):
        sid, name, _label, _text, _sh, bid, path, n_tokens = r[:8]
        if bid is None:
            unbuilt.append(name)
            continue
        if not os.path.exists(path):
            orphan.append("%s (index says %s, file is gone)" % (name, path))
            continue
        if os.stat(path).st_size != r[8]:
            broken.append("%s (size %d != recorded %d)" % (name, os.stat(path).st_size, r[8]))
            continue
        managed.append(name)

    # legacy = a block artifact that no source row owns: the old `memories` table, or a
    # .kvmem file dropped in by an earlier version of the demo.
    known = {r[1] for r in block_rows(con)}
    has_old = con.execute("SELECT name FROM sqlite_master WHERE type='table' "
                          "AND name='memories'").fetchone()
    if has_old:
        for name, path, n_tokens in con.execute(
                "SELECT name,path,n_tokens FROM memories"):
            if name not in known:
                legacy.append("%s (%d tok, no source -- read only, cannot rebuild)"
                              % (name, n_tokens))
    if os.path.isdir(blocks_dir):
        for f in sorted(os.listdir(blocks_dir)):
            stem = os.path.splitext(f)[0]
            if f.endswith(".kvmem") and stem not in known and \
               not any(stem in s for s in legacy):
                legacy.append("%s (untracked file -- read only, cannot rebuild)" % f)

    return {"managed": managed, "legacy": legacy, "orphan": orphan,
            "unbuilt": unbuilt, "broken": broken}


def verify(con, blocks_dir=None, model_path=MODEL):
    """Everything that must hold for the derived layer to be trustworthy."""
    problems = []
    exc = "is_excerpt" in set(r[1] for r in con.execute("PRAGMA table_info(memory_source)"))
    rows = con.execute(
        "SELECT s.id,s.name,s.text,s.source_hash,"
        "       b.path,b.n_bytes,b.state_version,b.model_size,b.model_mtime,b.model_path"
        + (",s.is_excerpt" if exc else ",0") +
        " FROM memory_source s LEFT JOIN memory_block b ON b.source_id = s.id").fetchall()
    fp = model_fp(model_path)
    for sid, name, text, sh, path, n_bytes, sver, m_size, m_mtime, m_path, is_exc in rows:
        if is_exc and path is None:
            continue          # an excerpt is a span of its container, never a block source
        if sha256_text(text) != sh:
            problems.append("%s: source_hash mismatch (text was mutated behind the trigger)"
                            % name)
        if path is None:
            problems.append("%s: no block built (source is intact)" % name)
            continue
        if not os.path.exists(path):
            problems.append("%s: block file missing -- rebuild from source" % name)
            continue
        if os.stat(path).st_size != n_bytes:
            problems.append("%s: block file size %d != recorded %d"
                            % (name, os.stat(path).st_size, n_bytes))
        if sver != STATE_VERSION:
            problems.append("%s: stale state format v%r" % (name, sver))
        if (m_size, m_mtime) != (fp["model_size"], fp["model_mtime"]):
            problems.append("%s: built with a different model -- rebuild from source" % name)
    return problems


# ---------------------------------------------------------------------------
# rebuild: the whole point. the block is a cache; losing it must cost only time.
# ---------------------------------------------------------------------------
def rebuild(eng, con, name, tenant="default", scope="private", blocks_dir=None,
            kv_type="q8_0", model_path=MODEL, seq=None):
    src = get_source(con, name, tenant, scope)
    if not src:
        raise KeyError("no source row for %s" % name)
    old = con.execute("SELECT n_tokens FROM memory_block WHERE source_id=?", (src[0],)).fetchone()
    if old and os.path.exists(os.path.join(blocks_dir or BLOCKS, name + ".kvmem")):
        os.remove(os.path.join(blocks_dir or BLOCKS, name + ".kvmem"))
    rec = build_block(eng, con, src, blocks_dir, kv_type, model_path, seq=seq)
    if old and old[0] != rec["n_tokens"]:
        raise RuntimeError("%s: token count changed across rebuild (%d -> %d); the source "
                           "text or tokenizer is not stable" % (name, old[0], rec["n_tokens"]))
    return rec


# --- M5 origin strings for a text assembled from layer-1 human turns -------------
#
# One writer, one reader, one regex: a format built by hand in one place and parsed
# by a regex in another is the half-the-truth-in-each-place failure this codebase
# keeps closing. format_* and parse_* below share ORIGIN_RE.
ORIGIN_HUMAN_TURNS = "declared_human_turns"
ORIGIN_SYNTHETIC = "declared_synthetic"

ORIGIN_RE = re.compile(
    r"^declared_human_turns:(?P<name>[^@#]+)@(?P<csha16>[0-9a-f]{16})"
    r"#(?P<lines>L[1-9][0-9]*(?:,L[1-9][0-9]*)*)@(?P<jsha256>[0-9a-f]{64})$")
ORIGIN_LOOSE_RE = re.compile(
    r"^declared_human_turns:(?P<name>[^@#]+)@(?P<csha16>[0-9a-f]{16})"
    r"#(?P<lines>L[1-9][0-9]*(?:,L[1-9][0-9]*)*)@(?P<jsha>[0-9a-fA-F]+)$")


class OriginError(Exception):
    """Any failure to build, parse or verify an origin. Never warn -- always raise."""


class OriginBadLength(OriginError):
    pass


class OriginLinesChanged(OriginError):
    pass


class OriginContainerStale(OriginError):
    pass


class OriginJoinedMismatch(OriginError):
    pass


def origin_is_synthetic(origin):
    return isinstance(origin, str) and origin.startswith(ORIGIN_SYNTHETIC + ":")


def format_human_turns_origin(name, container_sha16, line_indexes, joined_text):
    """THE writer. Use this; never build the string anywhere else."""
    if not isinstance(container_sha16, str) or not re.fullmatch(r"[0-9a-f]{16}", container_sha16):
        raise OriginContainerStale("容器 sha16 必须是 16 位小写 hex, got %r" % (container_sha16,))
    idx = [int(i) for i in line_indexes]
    if not idx or idx != sorted(idx) or len(set(idx)) != len(idx):
        raise OriginLinesChanged("行集/顺序不符: indexes must be unique and ascending, got %r" % (idx,))
    return "%s:%s@%s#%s@%s" % (ORIGIN_HUMAN_TURNS, name, container_sha16,
                              ",".join("L%d" % i for i in idx),
                              sha256_text(joined_text))


def parse_human_turns_origin(text):
    """THE reader. Structure out, never a comparison against a rendered string."""
    if not isinstance(text, str):
        raise OriginError("origin must be a string, got %r" % (type(text).__name__,))
    m = ORIGIN_RE.match(text)
    if m:
        return {"shape": "human_turns", "name": m.group("name"),
                "container_sha16": m.group("csha16"),
                "line_indexes": [int(x[1:]) for x in m.group("lines").split(",")],
                "joined_sha256": m.group("jsha256")}
    loose = ORIGIN_LOOSE_RE.match(text)
    if loose:
        got = loose.group("jsha")
        raise OriginBadLength(
            "需要 64 hex, 收到 %d hex: 短 hex 一律拒收, 因为它把校验从『全内容指纹』"
            '降级成『任意前缀相同即过』的前缀比对' % len(got))
    if origin_is_synthetic(text):
        return {"shape": "synthetic", "raw": text}
    raise OriginError("origin is neither declared_human_turns nor declared_synthetic: %r"
                      % (text[:120],))


def verify_human_turns_origin(con, origin, source_text=None):
    """Parse, then recompute three things independently. Any miss raises; none warns.

    Check order matters: the line set is compared BEFORE any hash, so a changed
    declaration reports line-set/order mismatch instead of a misleading hash mismatch.
    """
    p = parse_human_turns_origin(origin)
    if p["shape"] != "human_turns":
        raise OriginError("not a declared_human_turns origin: %r" % (origin[:60],))
    row = con.execute(
        "SELECT id, text, text_kind, is_excerpt, source_hash FROM memory_source "
        "WHERE name=? AND is_excerpt=0", (p["name"],)).fetchone()
    if not row:
        raise OriginContainerStale("容器不存在: %r" % (p["name"],))
    cid, ctext, kind, is_exc, chash = row
    if not chash.startswith(p["container_sha16"]):
        raise OriginContainerStale("容器版本不符: origin declares %s, registry has %s"
                                   % (p["container_sha16"], chash[:16]))
    ex = list(con.execute(
        "SELECT line_index, excerpt_source_id, line_sha256 FROM memory_source_excerpt "
        "WHERE container_id=? ORDER BY line_index", (cid,)))
    declared = [r[0] for r in ex]
    if p["line_indexes"] != declared:
        raise OriginLinesChanged("行集/顺序不符: origin declares %s, registry declares %s"
                                 % (p["line_indexes"], declared))
    clines = ctext.split(chr(10))
    texts = []
    for li, esid, lsha in ex:
        t = con.execute("SELECT text FROM memory_source WHERE id=?",
                        (esid,)).fetchone()[0]
        if t != clines[li - 1]:
            raise OriginError("第 %d 行不是容器的逐字子串: %r" % (li, t[:40]))
        if sha256_text(t) != lsha:
            raise OriginJoinedMismatch("第 %d 行 sha256 与 line_sha256 不符: %s != %s"
                                       % (li, sha256_text(t)[:16], lsha[:16]))
        texts.append(t)
    joined = chr(10).join(texts)
    if sha256_text(joined) != p["joined_sha256"]:
        raise OriginJoinedMismatch("joined 段与重组文本不符: origin=%s recomputed=%s"
                                   % (p["joined_sha256"][:16], sha256_text(joined)[:16]))
    if source_text is not None and sha256_text(source_text) != p["joined_sha256"]:
        raise OriginJoinedMismatch(
            "joined 段与块 source_text 不符: origin=%s source_text=%s"
            % (p["joined_sha256"][:16], sha256_text(source_text)[:16]))
    return {"name": p["name"], "container_sha16": p["container_sha16"],
            "line_indexes": p["line_indexes"], "joined_sha256": p["joined_sha256"],
            "joined_text": joined, "container_text": ctext, "text_kind": kind}


def assert_origin_roundtrip(origin, joined_text):
    """format(parse(x)) == x -- a write/read mismatch must explode here, not stay silent."""
    p = parse_human_turns_origin(origin)
    if p["shape"] != "human_turns":
        return True
    again = format_human_turns_origin(p["name"], p["container_sha16"], p["line_indexes"],
                                      joined_text)
    if again != origin:
        raise OriginError("round-trip mismatch: %r -> %r" % (origin, again))
    return True

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["init", "put", "build", "rebuild", "list", "verify"])
    ap.add_argument("--db", default=DB)
    ap.add_argument("--name")
    ap.add_argument("--label", default="")
    ap.add_argument("--text-file")
    ap.add_argument("--tenant", default="default")
    ap.add_argument("--scope", default="private")
    ap.add_argument("--mode", default="chat")
    ap.add_argument("--revise", action="store_true",
                    help="append a new revision when the text differs from the stored one")
    ap.add_argument("--kv", default="q8_0")
    a = ap.parse_args()
    con = connect(a.db)

    if a.cmd == "init":
        print("schema ready: %s" % a.db)
        print("  memory_source  (authoritative, immutable)")
        print("  memory_block   (derived, rebuildable)")

    elif a.cmd == "put":
        text = open(a.text_file, encoding="utf-8").read()
        sid, created = put_source(con, a.name, a.label or a.name, text,
                                  a.tenant, a.scope, a.mode, revise=a.revise)
        print("%s %s (id=%d, %d chars, sha256 %s...)"
              % ("inserted" if created else "already present:", a.name, sid,
                 len(text), sha256_text(text)[:12]))

    elif a.cmd in ("build", "rebuild"):
        from kvslots import KVEngine
        eng = KVEngine(MODEL, gpu=99, kv=a.kv)
        try:
            names = [a.name] if a.name else [r[0] for r in con.execute(
                "SELECT DISTINCT name FROM memory_source ORDER BY id")]
            for nm in names:
                rec = (rebuild if a.cmd == "rebuild" else
                       (lambda e, c, n, **kw: build_block(e, c, get_source(c, n), **kw)))(eng, con, nm)
                print("  %-10s %4d tokens  %7.1f KiB  %s"
                      % (rec["name"], rec["n_tokens"], rec["n_bytes"] / 1024.0, rec["path"]))
        finally:
            eng.close()

    elif a.cmd == "list":
        for r in block_rows(con, a.tenant, a.scope):
            sid, name, label, text, sh, bid, path, ntok, nby = r[:9]
            print("  id=%-3d %-10s %-8s %s  %s"
                  % (sid, name, label, ("%d tok" % ntok) if ntok else "no block",
                     os.path.basename(path) if path else "-"))

    elif a.cmd == "verify":
        try:
            uniq = assert_unique_texts(con)
            print("uniqueness: OK (%d distinct texts, one row each)" % len(uniq))
        except (AssertionError, SourceHashMismatch) as e:
            print("uniqueness: FAIL %s" % e)
            return 1
        c = classify(con)
        probs = verify(con)
        print("managed  %d: %s" % (len(c["managed"]), ", ".join(c["managed"]) or "-"))
        print("unbuilt  %d: %s" % (len(c["unbuilt"]), ", ".join(c["unbuilt"]) or "-"))
        print("legacy   %d: %s" % (len(c["legacy"]), "; ".join(c["legacy"]) or "-"))
        print("orphan   %d: %s" % (len(c["orphan"]), "; ".join(c["orphan"]) or "-"))
        print("broken   %d: %s" % (len(c["broken"]), "; ".join(c["broken"]) or "-"))
        if not probs and not c["orphan"] and not c["broken"]:
            print("verify: OK (every source hashes out, every block matches its source)")
            return 0 if not c["legacy"] else 0
        for p in probs:
            print("  - %s" % p)
        if c["orphan"]:
            print("  ! orphan artifacts are FAIL CLOSED: do not attach them")
        return 1 if (probs or c["orphan"] or c["broken"]) else 0
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())