# Knowledge Selves — WikiLLM for Obsidian

这个仓库把 `Obsidian_Vault` 调整成贴近 WikiLLM 精神的工作区：原始素材进入 `raw/`，LLM 编译后的知识库进入 `wiki/`，面向 Claude Cowork / OpenClaw 的技能说明进入 `skills/`。

当前 Agent 会监听 `Obsidian_Vault/raw/`，自动解析 PDF / Markdown / TXT，检索已有 Wiki，上下文化生成正式笔记，并把网页 Markdown 里的远程图片下载到 `wiki/assets/` 后改写成 Obsidian 可直接显示的本地嵌入。

## Vault 结构

```text
Obsidian_Vault/
├── raw/                    # 源文档与未处理数据
│   └── image/              # 手动保存的原始图片
├── wiki/
│   ├── concepts/           # 概念条目
│   ├── practices/          # 方法与操作流程
│   ├── visual/             # Mermaid/图谱/表格等可视化内容
│   ├── queries/            # 研究问答归档
│   ├── assets/             # Markdown 本地化后的图片资源
│   ├── INDEX.md            # Vault 导航入口
│   └── Glossary.md         # 术语表
├── skills/                 # 可移植给 Claude Cowork / OpenClaw 的技能
└── README.md               # Vault 说明
```

## Agent 结构

```text
Python_Agent/
├── main.py                 # 守护进程入口，监听 raw/
├── config.py               # vault 路径与目录分区定义
├── parser.py               # 文档解析与远程图片本地化
├── chunker.py              # 长文档 Map-Reduce 分块
├── embeddings.py           # BGE-M3 向量嵌入
├── memory.py               # ChromaDB 索引与检索
├── llm_brain.py            # 结构化输出，选择 wiki 分区
└── writer.py               # Frontmatter + 原子写入
```

## 快速开始

```bash
cd Python_Agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py
```

如果你更喜欢常驻方式：

```bash
docker compose up -d --build
docker compose logs -f
```

## 工作流

1. 用 Obsidian Web Clipper 或手动保存，把 Markdown / PDF / TXT 放进 `Obsidian_Vault/raw/`。
2. 如果是网页 Markdown，Agent 会尝试把远程图片下载到 `Obsidian_Vault/wiki/assets/<来源名>/`，并把原始 Markdown 改写成 `![[wiki/assets/...]]` 形式。
3. Agent 会检索整个 `wiki/`，并把生成结果直接写入 `concepts/`、`practices/`、`visual/` 或 `queries/`。
4. 在 Obsidian 里从 `wiki/INDEX.md` 开始浏览，再结合 Graph View、反向链接、Mermaid 预览查看结构。
5. 当你需要让 Claude Cowork 或 OpenClaw 协作时，直接复用 `Obsidian_Vault/skills/` 里的技能目录。

## 设计原则

- `raw/` 保留原始来源，不再使用单独的 `Inbox/Review/Archive` 流程。
- `wiki/` 里的 Markdown 是正式知识库，适合版本化和长期维护。
- 图片不做语义分析，只做本地化和正确引用，优先保证 Obsidian 内可视化稳定。
- `wiki/visual/` 允许用 Mermaid、对照表和导航图补强结构可读性。
- `skills/` 不是仓库说明的副本，而是从当前项目工作流蒸馏出来的可执行约束。

## 运行提示

- 默认 `VAULT_PATH=../Obsidian_Vault`，不需要改仓库目录名。
- 首次运行会下载 `BAAI/bge-m3`、Docling 相关模型并初始化 ChromaDB。
- Docker Compose 已经把宿主机的 `Obsidian_Vault/` 映射到容器 `/app/Obsidian_Vault`。
- 如果你使用云端 OpenAI-compatible API，直接在 `Python_Agent/.env` 填好 `LLM_PROVIDER`、`LLM_MODEL`、`LLM_BASE_URL`、`LLM_API_KEY` 即可。