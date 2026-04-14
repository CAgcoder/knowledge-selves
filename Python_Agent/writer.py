"""
writer.py — 安全写入层
将结构化 WikiNote 组装为 Obsidian Markdown 格式并安全落地。
包含文件名安全过滤（防路径穿越）和原子写入（防数据损坏）。
"""

import logging
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import frontmatter

from llm_brain import WikiNote

logger = logging.getLogger(__name__)

# 文件名中禁止出现的字符（Windows + macOS + Linux 危险字符全集）
_UNSAFE_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
# 路径穿越模式
_PATH_TRAVERSAL = re.compile(r"\.\.")

MAX_FILENAME_LENGTH = 200


def sanitize_filename(name: str) -> str:
    """
    安全过滤文件名，防止 LLM 生成的 title 包含路径穿越或非法字符。

    Args:
        name: 原始文件名（不含扩展名）

    Returns:
        安全的文件名字符串

    Raises:
        ValueError: 过滤后文件名为空
    """
    # 1. 去除路径穿越
    name = _PATH_TRAVERSAL.sub("", name)

    # 2. 去除所有不安全字符
    name = _UNSAFE_CHARS.sub("", name)

    # 3. 去除首尾空格和点号（macOS/Windows 文件名陷阱）
    name = name.strip(" .")

    # 4. 合并连续空格
    name = re.sub(r"\s+", " ", name)

    # 5. 截断长度
    if len(name) > MAX_FILENAME_LENGTH:
        name = name[:MAX_FILENAME_LENGTH].rstrip()

    # 6. 最终检查
    if not name:
        name = f"untitled_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

    return name


def save_to_obsidian(note: WikiNote, output_dir: Path) -> Path:
    """
    将 WikiNote 组装为带 YAML frontmatter 的 Markdown 并原子写入文件。

    Args:
        note: 结构化的笔记对象
        output_dir: 输出目录路径（通常是 03-Review）

    Returns:
        写入的文件路径
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_title = sanitize_filename(note.title)

    # 组装 frontmatter
    post = frontmatter.Post(note.content)
    post["tags"] = note.tags
    post["aliases"] = []
    post["created"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    post["source"] = "AI Agent Auto-Generated"
    if note.related_notes:
        post["related"] = note.related_notes

    content = frontmatter.dumps(post)

    # 处理文件名冲突
    file_path = output_dir / f"{safe_title}.md"
    if file_path.exists():
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        file_path = output_dir / f"{safe_title}_{timestamp}.md"

    # 原子写入：先写临时文件，再 rename（防止写一半断电导致文件损坏）
    fd, tmp_path = tempfile.mkstemp(
        dir=str(output_dir), suffix=".md.tmp", prefix="."
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.rename(tmp_path, str(file_path))
    except Exception:
        # 清理临时文件
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    logger.info("笔记已写入: %s", file_path.name)
    return file_path
