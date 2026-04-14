"""
main.py — 守护进程入口
Watchdog 监听 01-Inbox，自动编排 parse → chunk → memory → llm → write 管道。
"""

import logging
import shutil
import signal
import sys
import threading
import time
from pathlib import Path

import chromadb
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver

from chunker import split_markdown
from config import AppConfig, load_config
from embeddings import BGEM3EmbeddingFunction
from llm_brain import create_llm_client, generate_note, generate_note_mapreduce
from memory import WIKI_COLLECTION_NAME, get_related_notes, get_wiki_index, index_wiki_notes
from parser import SUPPORTED_EXTENSIONS, parse_document
from writer import save_to_obsidian

# ── 日志配置 ────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("agent.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("main")


def create_observer(config: AppConfig):
    """Create a watchdog observer suitable for the current runtime."""
    if config.observer_backend == "polling":
        logger.info("使用 PollingObserver 监听文件变化")
        return PollingObserver()

    logger.info("使用原生 Observer 监听文件变化")
    return Observer()


def write_heartbeat(heartbeat_path: Path):
    """Write a heartbeat timestamp for container health checks."""
    heartbeat_path.parent.mkdir(parents=True, exist_ok=True)
    heartbeat_path.write_text(str(time.time()), encoding="utf-8")


def heartbeat_loop(
    heartbeat_path: Path,
    interval_seconds: int,
    shutdown_event: threading.Event,
):
    """Continuously refresh the heartbeat file while the agent is healthy."""
    while not shutdown_event.is_set():
        write_heartbeat(heartbeat_path)
        shutdown_event.wait(timeout=interval_seconds)


# ── InboxHandler ────────────────────────────────────────────────────────

class InboxHandler(FileSystemEventHandler):
    """监听 01-Inbox 文件夹变化，触发文档处理管道。"""

    DEBOUNCE_SECONDS = 3  # 等待文件拷贝完成

    def __init__(
        self,
        config: AppConfig,
        collection: chromadb.Collection,
        llm_client,
    ):
        super().__init__()
        self.config = config
        self.collection = collection
        self.llm_client = llm_client
        self._timers: dict[str, threading.Timer] = {}

    def on_created(self, event: FileSystemEvent):
        if event.is_directory:
            return
        self._schedule_process(event.src_path)

    def on_moved(self, event: FileSystemEvent):
        if event.is_directory:
            return
        self._schedule_process(event.dest_path)

    def _schedule_process(self, file_path: str):
        """防抖：等待文件拷贝完成后再处理。"""
        path = Path(file_path)

        # 忽略临时文件和隐藏文件
        if path.name.startswith((".", "~")):
            return

        # 只处理支持的格式
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            logger.debug("忽略不支持的文件格式: %s", path.name)
            return

        # 取消之前的定时器（防抖）
        key = str(path)
        if key in self._timers:
            self._timers[key].cancel()

        timer = threading.Timer(
            self.DEBOUNCE_SECONDS,
            self._process_file,
            args=[path],
        )
        self._timers[key] = timer
        timer.start()

    def _process_file(self, file_path: Path):
        """完整的文档处理管道。"""
        logger.info("=" * 60)
        logger.info("开始处理文件: %s", file_path.name)

        try:
            # 1. 解析文档
            logger.info("[1/6] 解析文档...")
            raw_md = parse_document(file_path)
            logger.info("  解析完成，共 %d 字符", len(raw_md))

            # 2. 分块（如果需要）
            logger.info("[2/6] 检查是否需要分块...")
            chunks = split_markdown(raw_md, self.config.max_chunk_tokens)
            logger.info("  分块结果: %d 块", len(chunks))

            # 3. 获取知识库目录
            logger.info("[3/6] 扫描知识库目录...")
            wiki_index = get_wiki_index(self.config.wiki_dir)

            # 4. 检索相关笔记
            logger.info("[4/6] 检索相关笔记...")
            related_context = get_related_notes(raw_md, self.collection)

            # 5. LLM 生成
            logger.info("[5/6] 调用 LLM 生成笔记...")
            if len(chunks) == 1:
                note = generate_note(
                    parsed_content=raw_md,
                    wiki_index=wiki_index,
                    related_context=related_context,
                    client=self.llm_client,
                    model=self.config.llm_model,
                )
            else:
                note = generate_note_mapreduce(
                    chunks=chunks,
                    wiki_index=wiki_index,
                    related_context=related_context,
                    client=self.llm_client,
                    model=self.config.llm_model,
                )

            # 6. 写入 03-Review
            logger.info("[6/6] 写入笔记...")
            output_path = save_to_obsidian(note, self.config.review_dir)
            logger.info("  笔记已保存: %s", output_path.name)

            # 7. 归档原始文件到 04-Archive
            archive_dest = self.config.archive_dir / file_path.name
            if archive_dest.exists():
                stem = file_path.stem
                suffix = file_path.suffix
                import datetime
                ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
                archive_dest = self.config.archive_dir / f"{stem}_{ts}{suffix}"
            shutil.move(str(file_path), str(archive_dest))
            logger.info("  原始文件已归档: %s", archive_dest.name)

            logger.info("处理完成: %s → %s", file_path.name, output_path.name)

        except Exception:
            logger.exception("处理文件失败: %s", file_path.name)

        logger.info("=" * 60)


# ── Wiki 目录监听（增量索引） ──────────────────────────────────────────────

class WikiSyncHandler(FileSystemEventHandler):
    """监听 02-Wiki 文件夹变化，增量更新 ChromaDB 索引。"""

    DEBOUNCE_SECONDS = 5

    def __init__(self, config: AppConfig, collection: chromadb.Collection):
        super().__init__()
        self.config = config
        self.collection = collection
        self._timer: threading.Timer | None = None

    def on_any_event(self, event: FileSystemEvent):
        if event.is_directory:
            return
        src = getattr(event, "src_path", "")
        if not src.endswith(".md"):
            return
        self._schedule_reindex()

    def _schedule_reindex(self):
        if self._timer:
            self._timer.cancel()
        self._timer = threading.Timer(
            self.DEBOUNCE_SECONDS,
            self._reindex,
        )
        self._timer.start()

    def _reindex(self):
        logger.info("检测到 Wiki 变化，重新索引...")
        try:
            count = index_wiki_notes(self.config.wiki_dir, self.collection)
            logger.info("Wiki 索引更新完成，共 %d 篇笔记", count)
        except Exception:
            logger.exception("Wiki 索引更新失败")


# ── 主入口 ──────────────────────────────────────────────────────────────

def main():
    logger.info("Obsidian LLM-Wiki Agent 启动中...")

    # 1. 加载配置
    config = load_config()
    logger.info("配置加载完成:")
    logger.info("  LLM Provider: %s (%s)", config.llm_provider, config.llm_model)
    logger.info("  Vault: %s", config.vault_path)
    logger.info("  Embedding: %s", config.embedding_model)
    logger.info("  Observer Backend: %s", config.observer_backend)
    logger.info("  Heartbeat Path: %s", config.heartbeat_path)

    if not config.llm_api_key and config.llm_provider != "ollama":
        logger.error("LLM_API_KEY 未设置！请在 .env 中配置。")
        sys.exit(1)

    # 确保所有目录存在
    for d in [config.inbox_dir, config.wiki_dir, config.review_dir, config.archive_dir]:
        d.mkdir(parents=True, exist_ok=True)
    config.heartbeat_path.parent.mkdir(parents=True, exist_ok=True)

    # 2. 初始化 ChromaDB + Embedding
    logger.info("初始化 ChromaDB (path=%s)...", config.chromadb_path)
    embedding_fn = BGEM3EmbeddingFunction(config.embedding_model)
    chroma_client = chromadb.PersistentClient(path=str(config.chromadb_path))
    collection = chroma_client.get_or_create_collection(
        name=WIKI_COLLECTION_NAME,
        embedding_function=embedding_fn,
    )

    # 3. 首次全量索引 02-Wiki
    logger.info("首次全量索引 Wiki 笔记...")
    count = index_wiki_notes(config.wiki_dir, collection)
    logger.info("索引完成，共 %d 篇笔记", count)

    # 4. 创建 LLM 客户端
    llm_client = create_llm_client(config)

    # 5. 启动 Watchdog Observer
    observer = create_observer(config)

    # 监听 01-Inbox
    inbox_handler = InboxHandler(config, collection, llm_client)
    observer.schedule(inbox_handler, str(config.inbox_dir), recursive=False)
    logger.info("开始监听 Inbox: %s", config.inbox_dir)

    # 监听 02-Wiki（增量索引）
    wiki_handler = WikiSyncHandler(config, collection)
    observer.schedule(wiki_handler, str(config.wiki_dir), recursive=True)
    logger.info("开始监听 Wiki 变化: %s", config.wiki_dir)

    observer.start()

    shutdown_event = threading.Event()
    write_heartbeat(config.heartbeat_path)
    heartbeat_thread = threading.Thread(
        target=heartbeat_loop,
        args=(
            config.heartbeat_path,
            config.heartbeat_interval_seconds,
            shutdown_event,
        ),
        name="heartbeat",
        daemon=True,
    )
    heartbeat_thread.start()

    logger.info("Agent 已进入守护模式，等待新文件...")
    logger.info("按 Ctrl+C 退出")

    # 6. 优雅退出
    def _signal_handler(signum, frame):
        logger.info("收到退出信号 (%s)，正在关闭...", signal.Signals(signum).name)
        shutdown_event.set()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    try:
        while not shutdown_event.is_set():
            shutdown_event.wait(timeout=1)
    finally:
        shutdown_event.set()
        observer.stop()
        observer.join()
        heartbeat_thread.join(timeout=2)
        logger.info("Agent 已安全退出。")


if __name__ == "__main__":
    main()
