"""
llm_brain.py — LLM 思考与生成层
使用 instructor + OpenAI SDK 强制结构化输出，支持多 Provider 切换。
支持单次生成和 Map-Reduce 长文档生成。
"""

import logging
from typing import List

import instructor
from openai import OpenAI
from pydantic import BaseModel, Field

from config import AppConfig

logger = logging.getLogger(__name__)


# ── Pydantic 结构化输出模型 ──────────────────────────────────────────────

class WikiNote(BaseModel):
    """LLM 生成的结构化 Wiki 笔记。"""
    title: str = Field(description="笔记标题，尽量复用已有知识库中的概念词汇")
    tags: List[str] = Field(description="Obsidian 标签，例如 ['AI/Agent', '论文笔记']")
    content: str = Field(
        description="正文内容，必须使用 [[双链]] 引用已有的相关笔记，"
        "格式为标准 Markdown"
    )
    related_notes: List[str] = Field(
        default_factory=list,
        description="与本笔记相关的已有笔记标题列表",
    )


# ── LLM 客户端工厂 ──────────────────────────────────────────────────────

def create_llm_client(config: AppConfig) -> instructor.Instructor:
    """
    根据配置创建 instructor-wrapped OpenAI 客户端。
    当前实现支持 OpenAI-compatible provider，通过 base_url 切换。
    """
    raw_client = OpenAI(
        api_key=config.llm_api_key,
        base_url=config.llm_base_url,
    )
    client = instructor.from_openai(raw_client)
    logger.info(
        "LLM 客户端已初始化: provider=%s, model=%s",
        config.llm_provider,
        config.llm_model,
    )
    return client


# ── System Prompt 模板 ──────────────────────────────────────────────────

SYSTEM_PROMPT = """\
你是一位严谨的个人知识库管理员。你的职责是将用户提供的原始素材，提炼为结构化的 Wiki 笔记。

## 规则
1. **标题**: 用简洁的概念名或术语命名，尽量复用已有知识库中的词汇。
2. **标签**: 使用 Obsidian 层级标签格式，例如 `AI/Agent`、`论文笔记`。
3. **正文**:
   - 使用清晰的 Markdown 格式（标题层级、列表、代码块）。
   - 必须使用 `[[双链]]` 引用已有知识库中相关的笔记。
   - 提取核心概念、关键论点、重要公式或数据。
   - 用自己的语言重新组织，而非简单复制粘贴。
4. **相关笔记**: 列出与本笔记内容相关的已有笔记标题。

## 当前知识库目录
{wiki_index}

## 相关已有笔记内容
{related_context}
"""

USER_PROMPT = """\
请根据以下素材，提取核心概念并生成一篇结构化的 Wiki 笔记：

---
{content}
---
"""

REDUCE_PROMPT = """\
以下是对同一篇长文档分块生成的多个笔记片段。请将它们整合为一篇完整、连贯的 Wiki 笔记。
要求：
- 去除重复内容
- 统一标签和双链引用
- 保持逻辑连贯性
- 生成一个综合性的标题

## 各片段内容：
{chunks_content}
"""


# ── 核心生成函数 ────────────────────────────────────────────────────────

def generate_note(
    parsed_content: str,
    wiki_index: str,
    related_context: str,
    client: instructor.Instructor,
    model: str,
) -> WikiNote:
    """
    单次调用 LLM 生成结构化 Wiki 笔记。

    Args:
        parsed_content: 解析后的文档 Markdown 内容
        wiki_index: 知识库目录字符串
        related_context: 相关已有笔记的摘要
        client: instructor-wrapped 客户端
        model: 模型名称

    Returns:
        结构化的 WikiNote 对象
    """
    system_msg = SYSTEM_PROMPT.format(
        wiki_index=wiki_index,
        related_context=related_context,
    )
    user_msg = USER_PROMPT.format(content=parsed_content)

    logger.info("调用 LLM 生成笔记 (model=%s)", model)
    return client.chat.completions.create(
        model=model,
        response_model=WikiNote,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
    )


def generate_note_mapreduce(
    chunks: list[str],
    wiki_index: str,
    related_context: str,
    client: instructor.Instructor,
    model: str,
) -> WikiNote:
    """
    Map-Reduce 方式处理超长文档：
    1. Map: 对每个 chunk 独立生成部分笔记
    2. Reduce: 将所有部分笔记整合为一篇完整笔记

    Args:
        chunks: 分块后的文本列表
        wiki_index: 知识库目录字符串
        related_context: 相关已有笔记的摘要
        client: instructor-wrapped 客户端
        model: 模型名称

    Returns:
        整合后的 WikiNote 对象
    """
    # ── Map 阶段 ─────────────────────
    logger.info("Map-Reduce: 开始 Map 阶段，共 %d 个分块", len(chunks))
    partial_notes: list[WikiNote] = []

    for i, chunk in enumerate(chunks, 1):
        logger.info("  Map 分块 %d/%d ...", i, len(chunks))
        note = generate_note(
            parsed_content=chunk,
            wiki_index=wiki_index,
            related_context=related_context,
            client=client,
            model=model,
        )
        partial_notes.append(note)

    if len(partial_notes) == 1:
        return partial_notes[0]

    # ── Reduce 阶段 ──────────────────
    logger.info("Map-Reduce: 开始 Reduce 阶段，合并 %d 个部分笔记", len(partial_notes))

    chunks_summary = ""
    for i, note in enumerate(partial_notes, 1):
        chunks_summary += (
            f"\n### 片段 {i}: {note.title}\n"
            f"标签: {', '.join(note.tags)}\n\n"
            f"{note.content}\n\n---\n"
        )

    system_msg = SYSTEM_PROMPT.format(
        wiki_index=wiki_index,
        related_context=related_context,
    )
    user_msg = REDUCE_PROMPT.format(chunks_content=chunks_summary)

    return client.chat.completions.create(
        model=model,
        response_model=WikiNote,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
    )
