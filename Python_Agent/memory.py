"""
memory.py — 知识库上下文组装层
扫描 Wiki 目录树 + ChromaDB 向量检索，为 LLM 提供完整上下文。
"""

import logging
from pathlib import Path

import chromadb
import frontmatter

logger = logging.getLogger(__name__)

WIKI_COLLECTION_NAME = "wiki_notes"


def get_wiki_index(wiki_dir: Path) -> str:
    """
    遍历 wiki/ 下所有 .md 文件，提取相对路径和 tags 生成目录树字符串。

    Args:
        wiki_dir: Wiki 目录路径

    Returns:
        格式化的目录字符串，例如:
        - 大语言模型 [tags: AI, NLP]
        - 强化学习 [tags: AI, RL]
    """
    wiki_dir = Path(wiki_dir)
    if not wiki_dir.exists():
        return "(知识库为空)"

    entries: list[str] = []
    for md_file in sorted(wiki_dir.rglob("*.md")):
        name = md_file.relative_to(wiki_dir).with_suffix("").as_posix()
        try:
            post = frontmatter.load(str(md_file))
            tags = post.get("tags", [])
            if tags:
                entries.append(f"- {name} [tags: {', '.join(tags)}]")
            else:
                entries.append(f"- {name}")
        except Exception:
            entries.append(f"- {name}")

    if not entries:
        return "(知识库为空)"

    return f"当前知识库共 {len(entries)} 个节点:\n" + "\n".join(entries)


def index_wiki_notes(
    wiki_dir: Path,
    collection: chromadb.Collection,
) -> int:
    """
    全量/增量将 wiki/ 中的笔记索引到 ChromaDB。
    用文件相对路径作为 document ID，支持增量更新。

    Args:
        wiki_dir: Wiki 目录路径
        collection: ChromaDB collection

    Returns:
        索引的笔记数量
    """
    wiki_dir = Path(wiki_dir)
    if not wiki_dir.exists():
        return 0

    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict] = []

    for md_file in wiki_dir.rglob("*.md"):
        doc_id = str(md_file.relative_to(wiki_dir))
        try:
            post = frontmatter.load(str(md_file))
            content = post.content
            if not content.strip():
                continue
            tags = post.get("tags", [])
        except Exception:
            content = md_file.read_text(encoding="utf-8")
            tags = []

        ids.append(doc_id)
        documents.append(content[:2000])  # 限制长度避免 embedding 过长
        metadatas.append({"title": md_file.stem, "tags": ",".join(tags)})

    if not ids:
        return 0

    # upsert 支持增量更新（ID 相同则覆盖）
    collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
    logger.info("已索引 %d 篇 Wiki 笔记到 ChromaDB", len(ids))
    return len(ids)


def get_related_notes(
    text: str,
    collection: chromadb.Collection,
    n: int = 5,
) -> str:
    """
    通过 ChromaDB 向量检索最相关的 n 篇已有笔记。

    Args:
        text: 新文档的内容（用于查询）
        collection: ChromaDB collection
        n: 返回的最大相关笔记数

    Returns:
        格式化的相关笔记摘要字符串
    """
    try:
        count = collection.count()
        if count == 0:
            return "(暂无已有笔记可参考)"
    except Exception:
        return "(暂无已有笔记可参考)"

    n = min(n, count)
    results = collection.query(
        query_texts=[text[:1000]],  # 限制查询文本长度
        n_results=n,
    )

    if not results["documents"] or not results["documents"][0]:
        return "(未找到相关笔记)"

    parts: list[str] = []
    for i, (doc, meta) in enumerate(
        zip(results["documents"][0], results["metadatas"][0]), 1
    ):
        title = meta.get("title", "未知")
        snippet = doc[:500]  # 每篇只取前 500 字符作为摘要
        parts.append(f"### 相关笔记 {i}: {title}\n{snippet}")

    return "\n\n".join(parts)
