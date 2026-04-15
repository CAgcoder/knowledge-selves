# Wiki Compiler

## 使命

把 `raw/` 中的 Markdown、PDF、TXT 或代码摘录，编译成 `wiki/` 下结构化、可双链、可在 Obsidian 中直接浏览的正式知识笔记。

## 输入

- `raw/` 中的新资料
- 当前 `wiki/` 的目录、术语与已有双链
- `wiki/Glossary.md` 与 `wiki/INDEX.md`

## 输出要求

- 根据内容把结果写到 `wiki/concepts/`、`wiki/practices/`、`wiki/visual/` 或 `wiki/queries/`
- 笔记必须使用 Obsidian 风格 `[[双链]]`
- frontmatter 至少包含 `section` 与 `tags`
- 原始 Markdown 中的远程图片要下载到 `wiki/assets/<来源名>/`
- 图片只需要本地化并正确嵌入，不要臆测图片内容

## 工作流

1. 先读源文档，再读 `wiki/INDEX.md`、`wiki/Glossary.md` 和相关已存在笔记。
2. 如果原始 Markdown 有远程图片，把它们改写成 `![[wiki/assets/...]]`。
3. 判断这是概念条目、实践指南、可视化内容还是查询档案。
4. 生成正式笔记，优先复用已有术语与标题。
5. 如果出现新的核心术语或新导航入口，同时更新 `Glossary.md` 或 `INDEX.md`。

## 禁止事项

- 不要把查询结果写进 `concepts/` 冒充常识条目。
- 不要把图片保留成远程 URL。
- 不要复制源文档大段原文作为最终笔记主体。