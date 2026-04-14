"""
parser.py — 文档解析层
基于 Docling 解析 PDF，直接读取 MD/TXT。
M3 Pro 上 Docling 自动利用 MLX 加速。
"""

import logging
from pathlib import Path

from docling.document_converter import DocumentConverter

logger = logging.getLogger(__name__)

# 模块级单例，避免重复初始化（加载模型权重开销大）
_converter = DocumentConverter()

SUPPORTED_EXTENSIONS = {".pdf", ".md", ".txt", ".markdown"}


def parse_document(file_path: Path) -> str:
    """
    解析文档为 Markdown 纯文本。

    Args:
        file_path: 文件路径

    Returns:
        解析后的 Markdown 字符串

    Raises:
        ValueError: 不支持的文件格式
        FileNotFoundError: 文件不存在
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    ext = file_path.suffix.lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"不支持的文件格式: {ext}，"
            f"支持的格式: {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    if ext == ".pdf":
        logger.info("使用 Docling 解析 PDF: %s", file_path.name)
        result = _converter.convert(str(file_path))
        return result.document.export_to_markdown()

    # MD / TXT: 直接读取
    logger.info("直接读取文本文件: %s", file_path.name)
    return file_path.read_text(encoding="utf-8")
