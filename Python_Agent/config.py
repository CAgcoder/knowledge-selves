"""
config.py — 配置中心
从 .env 加载所有环境变量，提供 AppConfig dataclass 统一管理。
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


PROVIDER_DEFAULTS = {
    "deepseek": {
        "model": "deepseek-chat",
        "base_url": "https://api.deepseek.com/v1",
    },
    "openai": {
        "model": "gpt-4o-mini",
        "base_url": "https://api.openai.com/v1",
    },
    "openrouter": {
        "model": "openai/gpt-4o-mini",
        "base_url": "https://openrouter.ai/api/v1",
    },
    "siliconflow": {
        "model": "Qwen/Qwen2.5-72B-Instruct",
        "base_url": "https://api.siliconflow.cn/v1",
    },
    "gemini": {
        "model": "gemini-2.5-flash",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
    },
    "ollama": {
        "model": "qwen2.5:14b",
        "base_url": "http://localhost:11434/v1",
    },
}


@dataclass
class AppConfig:
    # LLM
    llm_provider: str = "deepseek"
    llm_model: str = "deepseek-chat"
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_api_key: str = ""

    # Paths
    vault_path: Path = field(default_factory=lambda: Path("../Obsidian_Vault"))
    chromadb_path: Path = field(default_factory=lambda: Path("data/chromadb"))

    # Embedding
    embedding_model: str = "BAAI/bge-m3"

    # Chunking
    max_chunk_tokens: int = 6000

    # Watchdog backend
    observer_backend: str = "native"

    # Healthcheck heartbeat
    heartbeat_path: Path = field(default_factory=lambda: Path("data/health/heartbeat"))
    heartbeat_interval_seconds: int = 15
    healthcheck_stale_seconds: int = 120

    @property
    def raw_dir(self) -> Path:
        return self.vault_path / "raw"

    @property
    def raw_image_dir(self) -> Path:
        return self.raw_dir / "image"

    @property
    def wiki_dir(self) -> Path:
        return self.vault_path / "wiki"

    @property
    def concepts_dir(self) -> Path:
        return self.wiki_dir / "concepts"

    @property
    def practices_dir(self) -> Path:
        return self.wiki_dir / "practices"

    @property
    def visual_dir(self) -> Path:
        return self.wiki_dir / "visual"

    @property
    def queries_dir(self) -> Path:
        return self.wiki_dir / "queries"

    @property
    def assets_dir(self) -> Path:
        return self.wiki_dir / "assets"

    @property
    def skills_dir(self) -> Path:
        return self.vault_path / "skills"


def load_config() -> AppConfig:
    """从 .env 文件加载配置，缺失项使用默认值。"""
    load_dotenv()
    llm_provider = os.getenv("LLM_PROVIDER", "deepseek").lower()
    provider_defaults = PROVIDER_DEFAULTS.get(
        llm_provider,
        PROVIDER_DEFAULTS["deepseek"],
    )

    vault = os.getenv("VAULT_PATH", "../Obsidian_Vault")
    # 如果是相对路径，基于 Python_Agent/ 目录解析
    vault_path = Path(vault)
    if not vault_path.is_absolute():
        vault_path = (Path(__file__).parent / vault_path).resolve()

    chromadb_path = (Path(__file__).parent / "data" / "chromadb").resolve()
    heartbeat_path = Path(os.getenv("HEARTBEAT_PATH", "data/health/heartbeat"))
    if not heartbeat_path.is_absolute():
        heartbeat_path = (Path(__file__).parent / heartbeat_path).resolve()

    return AppConfig(
        llm_provider=llm_provider,
        llm_model=os.getenv("LLM_MODEL", provider_defaults["model"]),
        llm_base_url=os.getenv("LLM_BASE_URL", provider_defaults["base_url"]),
        llm_api_key=os.getenv("LLM_API_KEY", ""),
        vault_path=vault_path,
        chromadb_path=chromadb_path,
        embedding_model=os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3"),
        max_chunk_tokens=int(os.getenv("MAX_CHUNK_TOKENS", "6000")),
        observer_backend=os.getenv("OBSERVER_BACKEND", "native").lower(),
        heartbeat_path=heartbeat_path,
        heartbeat_interval_seconds=int(
            os.getenv("HEARTBEAT_INTERVAL_SECONDS", "15")
        ),
        healthcheck_stale_seconds=int(
            os.getenv("HEALTHCHECK_STALE_SECONDS", "120")
        ),
    )
