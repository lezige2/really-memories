#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""qq_login_capture.py — NapCat 首次启动 + 登录取证（Windows / CPU-only，不装包）。

用法（由 LEAD 说 GO 后运行）：
    python -X utf8 tmp/qq_login_capture.py
    python -X utf8 tmp/qq_login_capture.py --timeout 300

行为：
  1. 以 `cmd /c napcat.bat` 启动 NapCat（cwd = NapCat.52230.Shell），stdout+stderr 捕获；
  2. 逐行解码（UTF-8 优先，失败回退 GB18030/GBK），脱敏 token 后写入
     `kvmem/qq_logs/napcat_boot.log`；
  3. 识别登录二维码：
       - webui/日志里的二维码 URL      -> `kvmem/qq_logs/qr_info.txt`
       - PNG 路径（存在则复制）         -> `kvmem/qq_logs/qr_login.png`
       - base64 PNG（data URI / iVBOR） -> 同上
       - 仅 ANSI/方块字符二维码         -> 原始片段 `kvmem/qq_logs/qr_ansi.txt`
  4. 识别 webui 地址与 token：地址回显（token 打码）；
     **token 只写入 `third_party/napcat_webui_token.txt`，绝不回显/写日志**；
  5. 等待登录成功关键字（登录成功 / 已上线 / 账号 xxx / login success / online），
     最多 timeout 秒；超时保存日志与状态后退出（默认不杀 NapCat）。

退出码：0 = 已捕获登录成功；3 = 超时；4 = NapCat 进程提前退出；2 = 启动/环境错误。
注意：本脚本**不代扫二维码**，二维码/token 由用户使用；脚本退出后 NapCat 默认继续运行。
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_SHELL = REPO / "third_party" / "_napcat_onekey" / "NapCat.52230.Shell"
LOG_DIR = REPO / "kvmem" / "qq_logs"
TOKEN_FILE = REPO / "third_party" / "napcat_webui_token.txt"

TOKEN_RE = re.compile(r"(?i)\b(?:access_token|token)\s*[=:]\s*([^\s&\"'<>]+)")
WEBUI_RE = re.compile(r"(?i)https?://[0-9a-zA-Z_.\-:\[\]]+/(?:webui|web)[^\s\"'<>]*")
QR_URL_RE = re.compile(r"(?i)https?://[^\s\"'<>]*(?:qrcode|qr|login)[^\s\"'<>]*")
PNG_RE = re.compile(r"(?i)((?:[A-Za-z]:\\|\.{0,2}[/\\])[^\s\"'<>|?*]+?\.png)")
B64_PNG_RE = re.compile(r"(?i)(?:data:image/png;base64,)?(iVBOR[A-Za-z0-9+/=\r\n]{40,})")
ANSI_CHARS = "█▄▀▌▐░▒▓■□◆◇"
LOGIN_PATTERNS = [
    re.compile(r"登录成功"),
    re.compile(r"已上线"),
    re.compile(r"上线成功"),
    re.compile(r"(?i)login\s*(?:success|ok)"),
    re.compile(r"(?i)\bonline\b"),
    re.compile(r"账号\s*[:：]?\s*(\d{5,12})"),
    re.compile(r"QQ\s*[:：]?\s*(\d{5,12})"),
]


def now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def decode_line(raw: bytes) -> str:
    for enc in ("utf-8", "gb18030", "gbk"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def redact(text: str) -> str:
    return TOKEN_RE.sub(lambda m: m.group(0)[: m.start(1) - m.start(0)] + "<redacted>", text)


def mask_account(text: str) -> str:
    def _m(m: re.Match) -> str:
        s = m.group(0)
        digits = m.group(1)
        return s.replace(digits, digits[:3] + "****" + digits[-2:] if len(digits) > 6 else "***")
    return re.sub(r"(?:账号|QQ)\s*[:：]?\s*(\d{5,12})", _m, text, flags=re.IGNORECASE)


def save_token(token: str) -> None:
    """token 只落盘到 TOKEN_FILE，绝不回显。"""
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(token, encoding="utf-8")
    print(f"[capture] webui token 已写入 {TOKEN_FILE}（不回显）", flush=True)


class Capture:
    def __init__(self, shell: Path, log_path: Path, timeout_s: float, kill_on_timeout: bool):
        self.shell = shell
        self.log_path = log_path
        self.timeout_s = timeout_s
        self.kill_on_timeout = kill_on_timeout
        self.q = queue.Queue()
        self.lines = 0
        self.login = False
        self.account = ""
        self.webui = ""
        self.token = ""
        self.qr_url = ""
        self.qr_png = ""
        self.qr_ansi = []
        self.status = "starting"
        self.log_fh = None

    # ---------- IO ----------
    def _reader(self, proc: subprocess.Popen) -> None:
        assert proc.stdout is not None
        for raw in iter(proc.stdout.readline, b""):
            text = decode_line(raw)
            safe = redact(text)
            if self.log_fh:
                try:
                    self.log_fh.write(safe)
                    self.log_fh.flush()
                except (ValueError, OSError):
                    pass
            self.q.put((text, safe))

    def _scan_qr_png(self) -> None:
        """兜底：在 NapCat 目录里找最近生成的二维码 PNG。"""
        candidates = []
        for base in (self.shell, self.shell / "versions", REPO / "third_party" / "_napcat_onekey"):
            if not base.exists():
                continue
            for p in base.rglob("*.png"):
                low = p.name.lower()
                if any(k in low for k in ("qr", "qrcode", "login")):
                    try:
                        candidates.append((p.stat().st_mtime, p))
                    except OSError:
                        pass
        if not candidates:
            return
        mtime, newest = max(candidates)
        if time.time() - mtime > 600:  # 只认最近 10 分钟
            return
        target = LOG_DIR / "qr_login.png"
        try:
            shutil.copyfile(newest, target)
            self.qr_png = str(target)
            print(f"[capture] 二维码图片已复制: {target}（源: {newest.name}）", flush=True)
        except OSError as exc:
            print(f"[capture] 复制二维码失败: {exc}", flush=True)

    def _handle(self, text: str, safe: str) -> None:
        self.lines += 1
        low = text.lower()
        # webui + token
        m = WEBUI_RE.search(text)
        if m:
            url = m.group(0).rstrip(".,;)")
            tok = TOKEN_RE.search(url)
            if tok:
                self.token = tok.group(1)
                if not TOKEN_FILE.exists() or TOKEN_FILE.read_text(encoding="utf-8", errors="replace").strip() != self.token:
                    save_token(self.token)
                url = TOKEN_RE.sub(lambda mm: mm.group(0)[: mm.start(1) - mm.start(0)] + "<redacted>", url)
            self.webui = url
            print(f"[capture] webui: {url}", flush=True)
        if not self.token:
            tm = TOKEN_RE.search(text)
            if tm and ("webui" in low or "token" in low or "web" in low):
                self.token = tm.group(1)
                save_token(self.token)
        # QR: URL
        qm = QR_URL_RE.search(text)
        if qm and not self.qr_url:
            self.qr_url = qm.group(0).rstrip(".,;)")
            with (LOG_DIR / "qr_info.txt").open("a", encoding="utf-8") as fh:
                fh.write(f"{now()} QR_URL {self.qr_url}\n")
            print(f"[capture] 二维码 URL 已记录（{LOG_DIR / 'qr_info.txt'}）", flush=True)
        # QR: PNG path
        pm = PNG_RE.search(text)
        if pm and not self.qr_png:
            cand = Path(pm.group(1))
            if not cand.is_absolute():
                cand = (self.shell / cand).resolve()
            if cand.exists():
                target = LOG_DIR / "qr_login.png"
                try:
                    shutil.copyfile(cand, target)
                    self.qr_png = str(target)
                    print(f"[capture] 二维码图片已复制: {target}", flush=True)
                except OSError as exc:
                    print(f"[capture] 复制二维码失败: {exc}", flush=True)
            else:
                with (LOG_DIR / "qr_info.txt").open("a", encoding="utf-8") as fh:
                    fh.write(f"{now()} QR_PNG_MISSING {cand}\n")
        # QR: base64 png
        bm = B64_PNG_RE.search(text)
        if bm and not self.qr_png:
            try:
                raw = base64.b64decode(re.sub(r"\s+", "", bm.group(1)) + "===", validate=False)
                if raw.startswith(b"\x89PNG"):
                    target = LOG_DIR / "qr_login.png"
                    target.write_bytes(raw)
                    self.qr_png = str(target)
                    print(f"[capture] 二维码 base64 图片已保存: {target}", flush=True)
            except Exception:
                pass
        # QR: ANSI blocks
        if sum(ch in ANSI_CHARS for ch in text) >= 10 and len(text) >= 40:
            self.qr_ansi.append(safe.rstrip("\r\n"))
            with (LOG_DIR / "qr_ansi.txt").open("a", encoding="utf-8") as fh:
                fh.write(safe if safe.endswith("\n") else safe + "\n")
        # login success
        if not self.login:
            for pat in LOGIN_PATTERNS:
                mm = pat.search(text)
                if mm:
                    self.login = True
                    self.status = "logged_in"
                    self.account = mm.group(1) if mm.groups() else ""
                    if not self.account:
                        am = re.search(r"(?:账号|QQ)\s*[:：]?\s*(\d{5,12})", text)
                        self.account = am.group(1) if am else ""
                    print(f"[capture] 检测到登录成功: {mask_account(redact(text.strip()))}", flush=True)
                    break

    def _write_status(self, elapsed: float) -> None:
        payload = {
            "status": self.status,
            "at": now(),
            "elapsed_s": round(elapsed, 1),
            "lines": self.lines,
            "log": str(self.log_path),
            "webui": self.webui,
            "token_saved_to": str(TOKEN_FILE) if TOKEN_FILE.exists() else None,
            "qr_png": self.qr_png or None,
            "qr_url": self.qr_url or None,
            "qr_ansi_lines": len(self.qr_ansi),
            "account_masked": self.account[:3] + "****" + self.account[-2:] if len(self.account) > 6 else ("***" if self.account else ""),
            "napcat_left_running": True,
        }
        p = LOG_DIR / "login_capture_status.json"
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"[capture] 状态已写: {p}", flush=True)

    # ---------- main ----------
    def run(self) -> int:
        if not self.shell.exists():
            print(f"[capture] ERROR: NapCat 目录不存在: {self.shell}", flush=True)
            return 2
        bat = self.shell / "napcat.bat"
        if not bat.exists():
            print(f"[capture] ERROR: 找不到 {bat}", flush=True)
            return 2
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.log_fh = self.log_path.open("a", encoding="utf-8", buffering=1)
        print(f"[capture] 启动: cmd /c napcat.bat  (cwd={self.shell})", flush=True)
        print(f"[capture] 日志: {self.log_path}  (timeout={self.timeout_s:.0f}s)", flush=True)
        t0 = time.time()
        self.log_fh.write(f"\n===== {now()} launch: {bat} =====\n")
        self.log_fh.flush()
        try:
            proc = subprocess.Popen(
                ["cmd", "/c", "napcat.bat"],
                cwd=str(self.shell),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=False,
                creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
            )
        except OSError as exc:
            print(f"[capture] ERROR: 启动失败: {exc}", flush=True)
            return 2
        th = threading.Thread(target=self._reader, args=(proc,), daemon=True)
        th.start()
        deadline = t0 + self.timeout_s
        last_scan = 0.0
        while time.time() < deadline:
            try:
                text, safe = self.q.get(timeout=0.5)
                self._handle(text, safe)
            except queue.Empty:
                pass
            if self.login:
                break
            if proc.poll() is not None and not self.login and time.time() - t0 > 5:
                self.status = "napcat_exited"
                print(f"[capture] NapCat 进程已退出 (rc={proc.returncode})，未见登录成功", flush=True)
                break
            if time.time() - last_scan > 5:
                last_scan = time.time()
                if not self.qr_png:
                    self._scan_qr_png()
        elapsed = time.time() - t0
        if self.login:
            self.status = "logged_in"
            print("[capture] STATUS=logged_in（二维码/登录信息已落盘；NapCat 继续运行）", flush=True)
        elif self.status != "napcat_exited":
            self.status = "timeout_no_login"
            print(f"[capture] STATUS=timeout_no_login（{elapsed:.0f}s 内未见登录成功；日志已保存，NapCat 继续运行）", flush=True)
            if self.kill_on_timeout:
                try:
                    proc.terminate()
                    print("[capture] 已按要求终止 NapCat（--kill-on-timeout）", flush=True)
                except OSError:
                    pass
        self._write_status(elapsed)
        if self.log_fh:
            self.log_fh.write(f"===== {now()} capture end: {self.status} ({elapsed:.1f}s) =====\n")
            self.log_fh.flush()
            self.log_fh.close()
        if self.status == "logged_in":
            return 0
        if self.status == "napcat_exited":
            return 4
        return 3


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="NapCat 首次启动 + 登录取证")
    ap.add_argument("--shell-dir", default=str(DEFAULT_SHELL), help="NapCat.52230.Shell 目录")
    ap.add_argument("--timeout", type=float, default=300.0, help="等待登录成功的秒数（默认 300）")
    ap.add_argument("--kill-on-timeout", action="store_true", help="超时后终止 NapCat（默认不终止）")
    args = ap.parse_args(argv)
    return Capture(Path(args.shell_dir), LOG_DIR / "napcat_boot.log", args.timeout, args.kill_on_timeout).run()


if __name__ == "__main__":
    sys.exit(main())