# 历史实现归档（pre-docs-first）

本目录保存 **docs-first 切换前**（2026-06-15）的可运行实现，仅供对照参考。

**不以本目录代码为准。** 唯一真相源：

- [docs/PRD.md](../../docs/PRD.md)
- [docs/TECH-DESIGN.md](../../docs/TECH-DESIGN.md)

重新实现请从 **M1** 里程碑开始，按 PRD §6 验收清单逐项勾选。

## 归档内容概览

| 目录/文件 | 说明 |
|-----------|------|
| `run.py` | CLI 入口 |
| `api/`、`admin/` | Web 平台 |
| `prd-parser/`、`test-generator/`、`component-generator/` | 引擎 |
| `tests/` | 中间产物、生成物、fixtures |
| `design/` | TypeUI SKILL（M3 起需迁回 `design/`） |
