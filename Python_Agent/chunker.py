"""
chunker.py — Map-Reduce 长文档分块与合并
按 Markdown heading 做语义切分，支持超长文档的分块处理。
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from llm_brain import WikiNote


def estimate_tokens(text: str) -> int:
    """粗估 token 数：中文约 1 字 ≈ 1.5 token，英文约 4 字符 ≈ 1 token，取混合估值。"""
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    other_chars = len(text) - chinese_chars
    return int(chinese_chars * 1.5 + other_chars / 4)


def split_markdown(text: str, max_tokens: int = 6000) -> list[str]:
    """
    按 Markdown heading 做语义切分。

    如果全文不超过 max_tokens，返回单元素列表（不分块）。
    切分策略：按 ## 或 ### heading 分段，贪心合并相邻段直到逼近 max_tokens。

    Args:
        text: 原始 Markdown 文本
        max_tokens: 每块的最大粗估 token 数

    Returns:
        切分后的文本块列表
    """
    if estimate_tokens(text) <= max_tokens:
        return [text]

    # 按 heading 分段（保留 heading 行作为段的开头）
    segments = re.split(r"(?=^#{1,3} )", text, flags=re.MULTILINE)
    segments = [s for s in segments if s.strip()]

    if not segments:
        return [text]

    # 贪心合并：把相邻小段合并到一块，直到超过阈值
    chunks: list[str] = []
    current_chunk = ""

    for seg in segments:
        combined = current_chunk + "\n\n" + seg if current_chunk else seg
        if estimate_tokens(combined) > max_tokens and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = seg
        else:
            current_chunk = combined

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks if chunks else [text]


def merge_notes(notes: list[WikiNote]) -> WikiNote:
    """
    合并多个部分笔记为一篇完整笔记（Map 阶段输出 → Reduce 输入）。

    - tags 去重合并
    - content 按顺序拼接（用分割线分隔）
    - related_notes 去重合并
    - title 取第一个

    Args:
        notes: 部分笔记列表

    Returns:
        合并后的 WikiNote
    """
    from llm_brain import WikiNote

    if not notes:
        raise ValueError("无法合并空的笔记列表")

    if len(notes) == 1:
        return notes[0]

    all_tags: list[str] = []
    all_content: list[str] = []
    all_related: list[str] = []

    for note in notes:
        all_tags.extend(note.tags)
        all_content.append(note.content)
        all_related.extend(note.related_notes)

    # 去重并保持顺序
    seen_tags: set[str] = set()
    unique_tags = [t for t in all_tags if not (t in seen_tags or seen_tags.add(t))]

    seen_related: set[str] = set()
    unique_related = [
        r for r in all_related if not (r in seen_related or seen_related.add(r))
    ]

    return WikiNote(
        title=notes[0].title,
        tags=unique_tags,
        content="\n\n---\n\n".join(all_content),
        related_notes=unique_related,
    )
