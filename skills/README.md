# WikiLLM Skills

这里的技能不是仓库说明文档，而是从当前项目的实际工作流蒸馏出来的可执行约束，目的是让 Claude Cowork、OpenClaw 或其他能够读取技能目录的智能体，在这个 vault 里按照同一套方法工作。

## 可用技能

- `wiki-compiler`: 把 `raw/` 中的资料编译成 `wiki/` 正式笔记。
- `wiki-curator`: 维护索引、术语表、双链密度和分区边界。
- `query-archivist`: 把一次调研问答归档成 `wiki/queries/` 笔记。
- `visual-synthesizer`: 生成 Mermaid 图谱、表格和其他可视化说明。

## 使用建议

- 让智能体先阅读对应目录下的 `SKILL.md`。
- 明确告诉它当前要操作的目标分区。
- 在要求它处理网页 Markdown 时，强调图片只需要本地化，不需要分析内容。