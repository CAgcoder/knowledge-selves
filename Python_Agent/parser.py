"""
parser.py — 文档解析层
基于 Docling 解析 PDF，直接读取 MD/TXT。
M3 Pro 上 Docling 自动利用 MLX 加速。
"""

import hashlib
import logging
import mimetypes
import re
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen
from pathlib import Path

from docling.document_converter import DocumentConverter

logger = logging.getLogger(__name__)

# 模块级单例，避免重复初始化（加载模型权重开销大）
_converter = DocumentConverter()

SUPPORTED_EXTENSIONS = {".pdf", ".md", ".txt", ".markdown"}
MARKDOWN_IMAGE_PATTERN = re.compile(
    r'!\[(?P<alt>[^\]]*)\]\((?P<url>https?://[^\s)]+)(?:\s+"[^"]*")?\)'
)
HTML_IMAGE_PATTERN = re.compile(
    r'<img\b(?P<attrs>[^>]*?)src=["\'](?P<url>https?://[^"\']+)["\'](?P<tail>[^>]*)>',
    re.IGNORECASE,
)
OBSIDIAN_IMAGE_EMBED_PATTERN = re.compile(r'!\[\[(?P<target>[^\]]+)\]\]')
UNSAFE_PATH_CHARS = re.compile(r'[^A-Za-z0-9._-]+')


def _sanitize_path_component(value: str, fallback: str) -> str:
    candidate = UNSAFE_PATH_CHARS.sub("-", value).strip("-._")
    return candidate or fallback


def _guess_suffix(url: str, content_type: str | None = None) -> str:
    parsed = urlparse(url)
    suffix = Path(parsed.path).suffix.lower()
    if suffix:
        return suffix

    format_hint = parse_qs(parsed.query).get("format", [""])[0].lower()
    if format_hint:
        return f".{format_hint}"

    if content_type:
        guessed = mimetypes.guess_extension(content_type.split(";", 1)[0].strip())
        if guessed:
            return guessed

    return ".bin"


def _download_image(url: str, source_file: Path, assets_dir: Path) -> Path | None:
    source_key = _sanitize_path_component(source_file.stem, "source")
    asset_dir = assets_dir / source_key
    asset_dir.mkdir(parents=True, exist_ok=True)

    parsed = urlparse(url)
    raw_name = Path(parsed.path).stem or "image"
    base_name = _sanitize_path_component(raw_name, "image")
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]

    request = Request(
        url,
        headers={
            "User-Agent": "WikiLLM-Agent/1.0 (+https://obsidian.md)",
        },
    )

    try:
        with urlopen(request, timeout=20) as response:
            content = response.read()
            content_type = response.headers.get("Content-Type")
    except Exception as exc:
        logger.warning("下载图片失败 %s: %s", url, exc)
        return None

    suffix = _guess_suffix(url, content_type)
    file_path = asset_dir / f"{base_name}-{digest}{suffix}"
    if not file_path.exists():
        file_path.write_bytes(content)
        logger.info("已下载图片资源: %s", file_path)

    return file_path


def _build_obsidian_embed(asset_path: Path, assets_dir: Path) -> str:
    vault_root = assets_dir.parent.parent
    asset_ref = asset_path.relative_to(vault_root).as_posix()
    return f"![[{asset_ref}]]"


def _replace_remote_images(markdown: str, source_file: Path, assets_dir: Path) -> str:
    cache: dict[str, str] = {}

    def replace_markdown(match: re.Match[str]) -> str:
        url = match.group("url")
        if url not in cache:
            asset_path = _download_image(url, source_file, assets_dir)
            cache[url] = (
                _build_obsidian_embed(asset_path, assets_dir)
                if asset_path
                else match.group(0)
            )
        return cache[url]

    def replace_html(match: re.Match[str]) -> str:
        url = match.group("url")
        if url not in cache:
            asset_path = _download_image(url, source_file, assets_dir)
            cache[url] = (
                _build_obsidian_embed(asset_path, assets_dir)
                if asset_path
                else match.group(0)
            )
        return cache[url]

    localized = MARKDOWN_IMAGE_PATTERN.sub(replace_markdown, markdown)
    return HTML_IMAGE_PATTERN.sub(replace_html, localized)


def extract_local_image_embeds(markdown: str) -> list[str]:
    embeds: list[str] = []
    seen: set[str] = set()

    for match in OBSIDIAN_IMAGE_EMBED_PATTERN.finditer(markdown):
        target = match.group("target")
        normalized = target.split("|", 1)[0]
        if not normalized.startswith("wiki/assets/"):
            continue
        embed = match.group(0)
        if embed in seen:
            continue
        seen.add(embed)
        embeds.append(embed)

    return embeds


def parse_document(file_path: Path, assets_dir: Path | None = None) -> str:
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
    content = file_path.read_text(encoding="utf-8")

    if ext in {".md", ".markdown"} and assets_dir is not None:
        localized = _replace_remote_images(content, file_path, assets_dir)
        if localized != content:
            file_path.write_text(localized, encoding="utf-8")
            content = localized

    return content
