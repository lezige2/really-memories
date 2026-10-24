"""集中配置：路径、预算、阈值、模型端点。

所有参数都有保守默认值，16GB 内存 / 10GB 显存机器上直接可用。
可通过 data/config.json 覆盖，或用环境变量 BIOMEM_* 覆盖。
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = Path(os.environ.get("BIOMEM_DATA", ROOT / "data"))


@dataclass
class Settings:
    # ---- 存储 ----
    data_dir: Path = DEFAULT_DATA_DIR
    db_name: str = "memory.sqlite3"

    # ---- 推理端点（llama.cpp / 任意 OpenAI 兼容服务） ----
    base_url: str = os.environ.get("BIOMEM_BASE_URL", "http://127.0.0.1:8080/v1")
    model: str = os.environ.get("BIOMEM_MODEL", "deepseek-r1-distill-qwen-7b")
    api_key: str = os.environ.get("BIOMEM_API_KEY", "local")
    request_timeout: float = 180.0
    max_tokens: int = 1024
    chat_max_tokens: int = 420          # 聊天模式强制短回复，避免 R1 展开长篇分析
    chat_stop: tuple[str, ...] = ("\n1.", "\n2.", "\n3.", "\n4.",
                                  "\n一、", "\n二、", "\n- ")
    temperature_chat: float = 0.75
    temperature_work: float = 0.25

    # ---- 工作记忆预算 ----
    context_budget_tokens: int = 3000      # 提示词总量（不含生成）
    recent_turns: int = 8                  # 感觉缓冲/工作记忆保留的最近轮数
    max_recalled_cards: int = 3            # 每轮注入的卡片上限
    card_char_limit: int = 420             # 单张卡片进入上下文的字符上限

    # ---- 元记忆 / 检索 ----
    recall_threshold: float = 2.0
    recall_candidates: int = 24            # 每个通道候选数
    rrf_k: int = 60

    # ---- 写入门控 ----
    write_threshold: float = 1.4
    auto_fact_confidence: float = 0.9
    emotion_event_threshold: float = 0.62

    # ---- 巩固 ----
    consolidate_every_turns: int = 8
    consolidate_window: int = 6            # 每个情景窗口的最大发言数
    dedupe_jaccard: float = 0.82
    idle_consolidate_seconds: float = 90.0  # 超过这个空闲时间才做后台巩固

    # ---- 遗忘 ----
    forgetting_half_life_days: float = 14.0
    archive_strength: float = 0.12
    archive_grace_days: float = 21.0
    access_reinforce: float = 0.12

    # ---- 索引 ----
    vector_dim: int = 512
    vector_shards: int = 8
    vector_cache_shards: int = 3

    # ---- 界面 ----
    color: bool = True
    debug: bool = False

    # ---- 运行时（不落盘） ----
    mock: bool = field(default=False, compare=False)
    db_path: Path = field(init=False, compare=False)

    def __post_init__(self) -> None:
        self.data_dir = Path(self.data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / self.db_name

    # ------------------------------------------------------------------
    @classmethod
    def load(cls, path: Path | None = None, **overrides) -> "Settings":
        """从 data/config.json 读取并叠加环境变量/显式参数。"""
        path = path or DEFAULT_DATA_DIR / "config.json"
        known = {f for f in cls.__dataclass_fields__}
        data: dict = {}
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                data = {}
            # 只接受已知字段，避免配置里写错键时静默失败
            data = {k: v for k, v in data.items() if k in known and k != "db_path"}
            if "data_dir" in data:
                data["data_dir"] = Path(data["data_dir"])

        explicit_db = overrides.pop("db_path", None)
        for k, v in overrides.items():
            if v is None or k not in known or k == "db_path":
                continue
            data[k] = Path(v) if k == "data_dir" else v

        s = cls(**data)
        if explicit_db:
            s.db_path = Path(explicit_db)
        return s

    def to_public_dict(self) -> dict:
        d = asdict(self)
        d["data_dir"] = str(self.data_dir)
        d["db_path"] = str(self.db_path)
        return d