# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

This is a Chinese-language work document library (工作文库) — a template and document management repository for organizational work. It contains no code, build system, or tests. The repository stores document templates and is intended to hold work documents, project files, reference materials, and archives.

## Directory Structure (Intended)

The README defines the full intended layout. Only `模板/` currently exists with populated content:

```
工作文库/
├── 文档/          # Actual work documents (报告, 方案, 合同, 会议纪要)
├── 模板/          # Document templates — the only populated directory
├── 项目/          # Project folders organized by status (进行中, 待启动, 已完成)
├── 资料/          # Reference materials (行业资料, 规范标准, 参考文献)
└── 归档/          # Archived historical documents
```

When creating missing directories, follow this structure exactly as specified in README.md.

## Available Templates

All templates live in `模板/` and are Markdown files:

| Template | Path | Use for |
|---|---|---|
| 会议纪要 | `模板/会议纪要/会议纪要模板.md` | Meeting minutes |
| 周报 | `模板/周报/周报模板.md` | Weekly work reports |
| 月报 | `模板/月报/月报模板.md` | Monthly work reports |
| 项目计划 | `模板/项目计划/项目计划模板.md` | Project plans |
| 工作总结 | `模板/工作总结/工作总结模板.md` | Work summaries |
| 工作方案 | `模板/工作方案/工作方案模板.md` | Work proposals/plans |

## Naming Conventions

From README.md — these must be followed for all new files and folders:

- **Files**: `YYYYMMDD_文件名称.扩展名` (e.g. `20260412_Q1项目总结.md`)
- **Project folders**: `项目名称_YYYY` (e.g. `供应链优化_2026`)
- **Archive folders**: `YYYY年/月份/` (e.g. `2026年/04月/`)

## Workflow for Common Tasks

**Adding a new document**: Copy the relevant template from `模板/`, fill in the content, and save to the appropriate `文档/` subdirectory using the naming convention above.

**Adding a new template**: Create a new `.md` file in the relevant `模板/` subdirectory. If a new template category is needed, create a new subdirectory under `模板/` and update the README.md directory listing.

**Archiving**: Move completed or expired documents from `文档/` or `项目/已完成/` into `归档/YYYY年/月份/`.

**Moving a project**: Project folders in `项目/` should move between `待启动/`, `进行中/`, and `已完成/` as status changes.

## Language and Format

All document content should be in Chinese (Simplified). Templates are in Markdown format. Maintain Markdown formatting consistency with existing templates when creating or updating files.
