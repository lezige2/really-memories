"""命令行聊天界面与维护命令。"""
from __future__ import annotations

import argparse
import os
import sys
import threading
import time

from .agent import Agent
from .config import Settings
from .llm import LLMError
from .textutil import human_date, now

HELP = """可用命令：
  /help                     显示帮助
  /mode chat|work           切换聊天/工作模式
  /remember <文本>          手动写入一条长期记忆
  /recall <查询>            调试：查看多路召回结果
  /cards [n]                列出最近的记忆卡片（默认 12）
  /why                      解释上一轮为什么召回/为什么写入
  /forget <卡片ID>          软删除（归档）一张卡片
  /persona                  查看人格核心
  /persona set <键> <值>    修改人格字段
  /persona snapshot [说明]  人格快照
  /persona list             快照列表
  /persona rollback <ID>    回滚人格
  /stats                    资源与记忆统计
  /consolidate              立刻做一次巩固
  /decay [--dry]            执行/预览遗忘衰减
  /session new              开新会话（记忆仍在）
  /quit                     退出（退出前会巩固）"""


def _supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()


class UI:
    def __init__(self, color: bool = True) -> None:
        self.color = color and _supports_color()

    def paint(self, text: str, code: str) -> str:
        return f"\x1b[{code}m{text}\x1b[0m" if self.color else text

    def dim(self, t: str) -> str:
        return self.paint(t, "2")

    def accent(self, t: str) -> str:
        return self.paint(t, "36")

    def warn(self, t: str) -> str:
        return self.paint(t, "33")

    def err(self, t: str) -> str:
        return self.paint(t, "31")

    def ok(self, t: str) -> str:
        return self.paint(t, "32")


def _setup_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _print_cards(agent: Agent, ui: UI, limit: int = 12) -> None:
    cards = agent.store.list_cards(status="active", limit=limit, order="recent")
    if not cards:
        print(ui.dim("（还没有长期记忆卡片）"))
        return
    for c in cards:
        head = (f"#{c.id} [{c.kind}] {human_date(c.created_at)} "
                f"强度{c.strength:.2f} 热度{c.access_count} 情绪{c.emotion_weight:.2f}")
        print(ui.accent(head))
        body = (c.summary or c.text).replace("\n", " ")
        print("   " + (body[:120] + ("…" if len(body) > 120 else "")))


def _print_persona(agent: Agent, ui: UI) -> None:
    p = agent.persona.profile
    print(ui.accent("人格核心（程序记忆）"))
    for k in ("name", "role", "tone", "user_name", "reply_style"):
        if p.get(k):
            print(f"  {k}: {p[k]}")
    if p.get("boundaries"):
        print("  boundaries:")
        for b in p["boundaries"]:
            print(f"    - {b}")
    if p.get("memes"):
        print("  memes: " + "、".join(map(str, p["memes"])))


def _print_why(agent: Agent, ui: UI) -> None:
    trace = agent.last_trace
    gate = agent.last_gate
    if trace:
        print(ui.accent("上一轮召回"))
        print("  " + trace.summary())
        if trace.notes:
            print("  " + ui.dim("；".join(trace.notes)))
        for cid in trace.picked:
            card = agent.store.get_card(cid)
            if card:
                print(f"  #{cid} {ui.dim(card.summary or card.text[:60])}")
    else:
        print(ui.dim("上一轮没有触发检索"))
    if gate:
        print(ui.accent("上一轮写入判定"))
        print("  " + gate.explain())
        for c in gate.candidates:
            print(f"  - {c.meta.get('fact', c.text[:60])}（{c.rationale}）")
    else:
        print(ui.dim("上一轮没有写入判定"))


def _handle_command(agent: Agent, ui: UI, line: str) -> bool:
    """返回 False 表示退出。"""
    parts = line.strip().split(maxsplit=2)
    cmd = parts[0].lower()

    if cmd in ("/quit", "/exit", "/q"):
        return False
    if cmd == "/help":
        print(HELP)
        return True
    if cmd == "/mode":
        if len(parts) < 2 or parts[1] not in ("chat", "work"):
            print(ui.warn("用法：/mode chat 或 /mode work"))
            return True
        agent.set_mode(parts[1])
        print(ui.ok(f"已切换到{parts[1]}模式"))
        return True
    if cmd == "/remember":
        text = line[len("/remember"):].strip()
        if not text:
            print(ui.warn("用法：/remember 要记住的内容"))
            return True
        cid = agent.remember(text)
        print(ui.ok(f"已写入长期记忆 #{cid}"))
        return True
    if cmd == "/recall":
        q = line[len("/recall"):].strip()
        if not q:
            print(ui.warn("用法：/recall 查询内容"))
            return True
        cards, trace = agent.recall_debug(q)
        print(ui.accent(trace.summary()))
        for r in cards:
            print(f"  #{r.card.id} score={r.score:.3f} [{','.join(r.reasons)}]")
            print("    " + (r.card.summary or r.card.text).replace("\n", " ")[:100])
        return True
    if cmd == "/cards":
        n = 12
        if len(parts) > 1 and parts[1].isdigit():
            n = int(parts[1])
        _print_cards(agent, ui, n)
        return True
    if cmd == "/why":
        _print_why(agent, ui)
        return True
    if cmd == "/forget":
        if len(parts) < 2 or not parts[1].isdigit():
            print(ui.warn("用法：/forget 卡片ID"))
            return True
        ok = agent.forget(int(parts[1]))
        print(ui.ok("已归档") if ok else ui.warn("没找到这张卡片"))
        return True
    if cmd == "/persona":
        if len(parts) == 1:
            _print_persona(agent, ui)
            return True
        sub = parts[1]
        if sub == "set":
            rest = line[len("/persona set"):].strip()
            if " " not in rest:
                print(ui.warn("用法：/persona set 键 值"))
                return True
            key, value = rest.split(" ", 1)
            agent.persona.set(key, value.strip())
            print(ui.ok(f"已更新 {key}"))
        elif sub == "snapshot":
            note = line[len("/persona snapshot"):].strip()
            sid = agent.persona.snapshot(note)
            print(ui.ok(f"人格快照 #{sid}"))
        elif sub == "list":
            for s in agent.persona.list_snapshots():
                print(f"  #{s['snapshot_id']} {s['created_at']} {s['note'] or ''}")
        elif sub == "rollback":
            if len(parts) < 3 or not parts[2].isdigit():
                print(ui.warn("用法：/persona rollback 快照ID"))
                return True
            ok = agent.persona.rollback(int(parts[2]))
            print(ui.ok("已回滚") if ok else ui.warn("没找到快照"))
        else:
            print(ui.warn("未知子命令，见 /help"))
        return True
    if cmd == "/stats":
        for k, v in agent.stats().items():
            print(f"  {k}: {v}")
        return True
    if cmd == "/consolidate":
        rep = agent.consolidate(use_llm=False)
        print(ui.ok(rep.summary()))
        return True
    if cmd == "/decay":
        dry = "--dry" in line
        if dry:
            for cid, s, text in agent.forgetting.preview():
                print(f"  #{cid} 预计强度 {s:.3f}  {text}")
        else:
            rep = agent.decay()
            print(ui.ok(rep.summary()))
        return True
    if cmd == "/session":
        if len(parts) > 1 and parts[1] == "new":
            sid = agent.new_session()
            print(ui.ok(f"新会话 {sid}"))
        else:
            print(ui.warn("用法：/session new"))
        return True

    print(ui.warn("未知命令，/help 查看列表"))
    return True


def _chat_once(agent: Agent, ui: UI, text: str, *, show_debug: bool) -> None:
    print(ui.accent("你：") + text)
    print(ui.accent(f"{agent.persona.get('name')}："), end="", flush=True)
    try:
        result = agent.turn(text, stream_cb=lambda chunk: print(chunk, end="", flush=True))
        print()
        if show_debug:
            print(ui.dim(f"  [召回] {result.trace.summary() if result.trace else '未触发'}"))
            print(ui.dim(f"  [写入] {result.gate.explain() if result.gate else '无'}"))
            print(ui.dim(f"  [延迟] {result.latency_ms:.0f} ms"))
        agent.schedule_idle_consolidation()
    except LLMError as e:
        print()
        print(ui.err(str(e)))
        print(ui.dim("提示：先启动 llama-server（scripts\\run_llama.ps1），"
                     "或用 --mock 离线试跑记忆回路。"))


def main(argv: list[str] | None = None) -> int:
    _setup_console()
    parser = argparse.ArgumentParser(prog="biomem", description="本地仿生记忆聊天智能体")
    parser.add_argument("--data-dir", default=None, help="数据目录（默认 ./data）")
    parser.add_argument("--db", default=None, help="数据库文件路径")
    parser.add_argument("--base-url", default=None, help="OpenAI 兼容端点")
    parser.add_argument("--model", default=None, help="模型名")
    parser.add_argument("--mock", action="store_true", help="离线 Mock 后端")
    parser.add_argument("--mode", choices=["chat", "work"], default="chat")
    parser.add_argument("--once", default=None, help="只处理一句话后退出")
    parser.add_argument("--session", default=None, help="沿用指定会话 ID")
    parser.add_argument("--no-color", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--no-consolidate", action="store_true", help="退出时不做巩固")
    parser.add_argument("--health", action="store_true", help="只检查推理端点")
    args = parser.parse_args(argv)

    overrides: dict = {"color": not args.no_color, "debug": args.debug}
    if args.data_dir:
        overrides["data_dir"] = args.data_dir
    if args.base_url:
        overrides["base_url"] = args.base_url
    if args.model:
        overrides["model"] = args.model
    if args.db:
        overrides["db_path"] = args.db
    settings = Settings.load(**overrides)
    settings.mock = args.mock or settings.mock
    if args.db:
        settings.db_path = __import__("pathlib").Path(args.db)

    ui = UI(settings.color)
    if args.health:
        from .llm import build_llm
        llm = build_llm(settings)
        ok, msg = llm.health()
        print((ui.ok if ok else ui.err)(msg))
        return 0 if ok else 2

    agent = Agent(settings, session_id=args.session)
    agent.set_mode(args.mode)

    tag = "离线 Mock" if settings.mock else settings.base_url
    print(ui.accent(f"小忆 · 本地仿生记忆智能体"))
    print(ui.dim(f"  后端：{tag}  数据库：{settings.db_path}"))
    print(ui.dim("  输入 /help 看命令，/quit 退出。"))
    print()

    try:
        if args.once:
            _chat_once(agent, ui, args.once, show_debug=True)
            return 0

        while True:
            try:
                line = input(ui.accent("你："))
            except EOFError:
                print()
                break
            if not line.strip():
                continue
            if line.startswith("/"):
                if not _handle_command(agent, ui, line):
                    break
                continue
            _chat_once(agent, ui, line, show_debug=settings.debug)
    except KeyboardInterrupt:
        print()
    finally:
        if not args.no_consolidate:
            try:
                rep = agent.consolidate(use_llm=False)
                if rep.created or rep.merged:
                    print(ui.dim(f"  [退出前] {rep.summary()}"))
            except Exception:
                pass
        agent.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())