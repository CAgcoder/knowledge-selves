# WikiLLM Vault

这个 vault 按 WikiLLM 的工作方式组织，而不是传统的“收件箱/审核/归档”三段式笔记流。`raw/` 存源材料，`wiki/` 存 LLM 编译后的正式知识库，`skills/` 存给外部智能体复用的技能约束。

## 目录

```text
Obsidian_Vault/
├── raw/
│   └── image/
├── wiki/
│   ├── concepts/
│   ├── practices/
│   ├── visual/
│   ├── queries/
│   ├── assets/
│   ├── INDEX.md
│   └── Glossary.md
├── skills/
└── README.md
```

## 使用方式

1. 把网页剪藏、PDF、TXT、代码摘录放进 `raw/`。
2. 让 Agent 监听 `raw/`，自动编译到 `wiki/`。
3. 从 `wiki/INDEX.md` 开始浏览，再配合 Graph View、反向链接和 Mermaid 预览查看结构。
4. 如果原始 Markdown 带远程图片，Agent 会把图片下载到 `wiki/assets/` 并改写引用。
5. 如果要让 Claude Cowork 或 OpenClaw 协作，直接读取 `skills/` 下的技能目录。

## 约束

- 图片只做本地化，不做语义识别。
- `wiki/` 里的内容默认视为正式知识资产，优先保留双链与术语一致性。
- 查询结果建议进入 `wiki/queries/`，不要散落在 `concepts/` 或 `practices/`。