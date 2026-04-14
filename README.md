# Knowledge Selves — Obsidian LLM-Wiki Agent

基于 WikiLLM 设计理念的个人知识库自动化系统。监听 Obsidian Inbox，自动解析文档、检索上下文、生成结构化 Wiki 笔记。

## 架构概览

```
Obsidian_Vault/
├── 01-Inbox/      ← 拖入 PDF/MD/TXT 原始素材
├── 02-Wiki/       ← 你的核心知识节点（Agent 只读）
├── 03-Review/     ← Agent 生成的笔记（待你审核）
└── 04-Archive/    ← 处理完的原始文件自动归档

Python_Agent/
├── main.py        ← 守护进程入口（Watchdog 监听）
├── config.py      ← 配置中心（.env 加载）
├── parser.py      ← Docling 文档解析（PDF → Markdown）
├── chunker.py     ← Map-Reduce 长文档分块
├── embeddings.py  ← BGE-M3 向量嵌入
├── memory.py      ← ChromaDB 知识库检索
├── llm_brain.py   ← LLM 结构化输出（instructor）
└── writer.py      ← Frontmatter 组装 + 安全写入
```

## 环境要求

- macOS (Apple Silicon M3 Pro 推荐) / Linux
- Python 3.12+
- LLM API Key（推荐使用 DeepSeek / OpenAI / OpenRouter / SiliconFlow / Gemini 等 OpenAI-compatible 云 API）

## 快速开始

```bash
# 1. 进入项目目录
cd Python_Agent

# 2. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 API Key 和模型配置

# 5. 启动 Agent
python main.py
```

## 启动方式

推荐先完成依赖安装和 `.env` 配置，再按下面的方式启动。

### 1. 前台启动（开发调试推荐）

```bash
cd Python_Agent
source .venv/bin/activate
python main.py
```

启动成功后会看到类似日志：

```text
Obsidian LLM-Wiki Agent 启动中...
开始监听 Inbox: .../Obsidian_Vault/01-Inbox
开始监听 Wiki 变化: .../Obsidian_Vault/02-Wiki
Agent 已进入守护模式，等待新文件...
```

停止方式：在当前终端按 `Ctrl+C`。

### 2. 后台启动（长期守护推荐）

```bash
cd Python_Agent
source .venv/bin/activate
nohup python main.py > agent.log 2>&1 &
```

查看日志：

```bash
tail -f agent.log
```

停止后台进程：

```bash
ps aux | grep "python main.py"
kill <PID>
```

### 3. Docker Compose 启动（推荐生产常驻）

先准备环境变量文件：

```bash
cp Python_Agent/.env.example Python_Agent/.env
```

然后启动容器：

```bash
docker compose up -d --build
```

查看运行状态：

```bash
docker compose ps
docker compose logs -f
```

停止容器：

```bash
docker compose down
```

说明：

- `./Obsidian_Vault` 会挂载到容器内 `/app/Obsidian_Vault`
- `./Python_Agent/data` 会持久化 ChromaDB 和模型缓存
- Compose 默认把 `OBSERVER_BACKEND` 设为 `polling`，更适合 macOS 宿主目录挂载
- 镜像内已带 `HEALTHCHECK`，启动后可用 `docker ps` 或 `docker inspect` 查看 `healthy` 状态

### 4. 云端 API 启动（推荐）

如果你不想在本地跑大模型，直接在 `.env` 里配置云端 API 即可。当前代码走的是 `OpenAI SDK + base_url`，所以最稳的是 OpenAI-compatible 接口。

示例：

```bash
# DeepSeek（通常成本较低）
LLM_PROVIDER=deepseek
LLM_MODEL=deepseek-chat
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_API_KEY=your_key

# OpenAI（标准付费 API）
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your_key

# OpenRouter（按平台实时策略，可能有免费模型或试用额度）
LLM_PROVIDER=openrouter
LLM_MODEL=openai/gpt-4o-mini
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=your_key

# Gemini（Google AI Studio / Gemini OpenAI 兼容网关）
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.5-flash
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
LLM_API_KEY=AIza...
```

配置完成后，直接启动：

```bash
docker compose up -d --build
```

### 5. 使用 Ollama 启动（可选）

如果 `.env` 中配置的是本地 Ollama，先确保 Ollama 服务和模型已经可用：

```bash
ollama serve
ollama pull qwen2.5:14b
```

如果 Agent 跑在 Docker 里，而 Ollama 跑在宿主机，请把 `.env` 中的地址改成：

```bash
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5:14b
LLM_BASE_URL=http://host.docker.internal:11434/v1
LLM_API_KEY=ollama
```

然后按上面的本地方式或 Docker Compose 方式启动 Agent：

```bash
cd Python_Agent
source .venv/bin/activate
python main.py
```

### 6. 首次启动的正常现象

- `sentence-transformers` 会首次下载 `BAAI/bge-m3` 模型
- `Docling` 可能会首次下载相关解析模型
- 首次建立 ChromaDB 索引会比后续启动慢

如果第一次启动耗时较长，属于正常现象

## 工作流程

1. 往 `01-Inbox/` 拖入一篇 PDF / Markdown / TXT 文件
2. Agent 自动检测并解析文档（Docling 在 M3 Pro 上利用 MLX 加速）
3. 扫描 `02-Wiki/` 目录，检索相关已有笔记（ChromaDB + BGE-M3）
4. 调用 LLM 生成结构化 Wiki 笔记（带 `[[双链]]` 和标签）
5. 笔记写入 `03-Review/`，原始文件归档到 `04-Archive/`
6. 你在 Obsidian 中审核笔记，满意后拖入 `02-Wiki/`

## 多 Provider 支持

在 `.env` 中切换 LLM 提供商。当前代码推荐使用 OpenAI-compatible 云 API：

```bash
# DeepSeek
LLM_PROVIDER=deepseek
LLM_MODEL=deepseek-chat
LLM_BASE_URL=https://api.deepseek.com/v1

# OpenAI
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
LLM_BASE_URL=https://api.openai.com/v1

# OpenRouter
LLM_PROVIDER=openrouter
LLM_MODEL=openai/gpt-4o-mini
LLM_BASE_URL=https://openrouter.ai/api/v1

# Gemini
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.5-flash
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/

# 本地 Ollama
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5:14b
LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=ollama
```

说明：

- 付费 API：OpenAI、DeepSeek 等
- 免费额度或免费模型通道：取决于平台实时政策，例如部分 OpenRouter 路由
- Gemini 可以直接复用当前的 `OpenAI SDK + base_url` 调用方式，无需单独改写 client 层
- 当前实现不是 Anthropic 原生 SDK 适配层，如果要直连 Anthropic 原生接口，需要单独加 provider adapter

## 长文档处理

超过 token 上限的文档自动使用 Map-Reduce 策略：
- **Map**: 按 Markdown heading 分块，每块独立生成部分笔记
- **Reduce**: LLM 将所有部分笔记整合为一篇完整、连贯的笔记

可在 `.env` 中调整分块大小: `MAX_CHUNK_TOKENS=6000`