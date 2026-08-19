# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

This is a Chinese-language work document library (**工作文库**) — a personal/organizational knowledge base of Markdown document templates and, eventually, the filled-in documents produced from them.

There is **no build system, no test suite, no CI, and no application code** on the default branch. Deliverables here are documents. "Correctness" means: right template, right directory, right filename, consistent Markdown, content in Simplified Chinese.

## Repository Layout

### What actually exists (default branch)

```
.
├── README.md                          # Library charter: layout, usage rules, naming conventions
└── 模板/                              # Templates — the only populated directory
    ├── 会议纪要/会议纪要模板.md
    ├── 周报/周报模板.md
    ├── 月报/月报模板.md
    ├── 工作总结/工作总结模板.md
    ├── 工作方案/工作方案模板.md
    └── 项目计划/项目计划模板.md
```

### What README.md declares (target layout)

`README.md` documents a larger tree that is **not yet materialized** — git does not track empty directories, so `文档/`, `项目/`, `资料/`, and `归档/` exist only as intent until a real file lands in them:

```
├── 文档/          # Finished work documents
│   ├── 报告/      # Reports
│   ├── 方案/      # Proposals and plans
│   ├── 合同/      # Contracts and agreements
│   └── 会议纪要/  # Meeting minutes
├── 模板/          # Templates (see above)
├── 项目/          # Project folders by status
│   ├── 进行中/    # In progress
│   ├── 待启动/    # Not yet started
│   └── 已完成/    # Completed
├── 资料/          # Reference material
│   ├── 行业资料/  # Industry material
│   ├── 规范标准/  # Standards and specifications
│   └── 参考文献/  # Bibliography
└── 归档/          # Archived historical documents
```

Create these directories on demand, exactly as named above — do not invent alternative names, English equivalents, or a flatter structure. If a genuinely new top-level category is needed, add it to the README tree in the same commit.

## Template Inventory

| Template | Path | Use for |
|---|---|---|
| 会议纪要 | `模板/会议纪要/会议纪要模板.md` | Meeting minutes — agenda, per-topic notes, resolutions table, signatures |
| 周报 | `模板/周报/周报模板.md` | Weekly report — work done, next week's plan, blockers |
| 月报 | `模板/月报/月报模板.md` | Monthly report — completion table with 完成率, highlights, gaps, next month |
| 工作总结 | `模板/工作总结/工作总结模板.md` | Period work summary — overview, results, shortcomings, lessons, next phase |
| 工作方案 | `模板/工作方案/工作方案模板.md` | Work proposal — background, scope, phased plan, staffing, budget, risk, 变更记录 |
| 项目计划 | `模板/项目计划/项目计划模板.md` | Project plan — team, milestones, WBS, risk, resources, 变更记录 |

## Document Conventions

These are derived from the existing templates. Match them when authoring or editing anything here.

- **Language**: Simplified Chinese for all content, headings, and table columns. Section numbering uses Chinese numerals (`## 一、`, `## 二、`), subsections use decimals (`### 1.1`).
- **Header block**: templates open with an `# 标题` followed by bold field labels — `**姓名：**`, `**部门：**`, `**编制日期：**` — each line ending in **two trailing spaces** so Markdown renders a hard line break. Preserve those trailing spaces; a reformatter that strips them breaks the header block.
- **Separators**: `---` horizontal rules between major sections.
- **Tables**: pipe tables with a `序号` column where rows are enumerated, and 3–5 blank rows pre-seeded so the template is fillable by hand. Keep the blank rows in templates; delete unused ones only in filled-in documents.
- **Blank fields**: templates leave values empty rather than using placeholder text. Parenthetical guidance — `（简要描述本周期内的总体工作情况）` — is the one exception and belongs on its own line under the heading.
- **Versioned documents**: `工作方案` and `项目计划` carry `**文档版本：** V1.0` in the header and a 变更记录 table at the end. When editing such a document, bump the version and append a 变更记录 row — do not edit silently.
- **Risk tables** use the fixed vocabulary `高/中/低` for 可能性 and 影响程度.

## Naming Conventions

From `README.md` — these are mandatory for every new file and folder:

- **Files**: `YYYYMMDD_文件名称.扩展名` — e.g. `20260819_Q3项目总结.md`
- **Project folders**: `项目名称_YYYY` — e.g. `供应链优化_2026`
- **Archive folders**: `归档/YYYY年/月份/` — e.g. `归档/2026年/08月/`

Templates themselves are the exception: they are named `<类型>模板.md` inside `模板/<类型>/` and carry no date prefix.

## Common Workflows

**Create a work document**: copy the matching file out of `模板/` into the right `文档/` subdirectory under a `YYYYMMDD_` name, then fill it in. Do not edit the template in place, and do not author a document from scratch when a template covers it.

**Add a new template**: create `模板/<新类型>/<新类型>模板.md`, mirroring the header-block / `---` / numbered-section style of the existing six, then add the new subdirectory to the README tree in the same commit.

**Change status of a project**: move the whole `项目名称_YYYY` folder between `项目/待启动/`, `项目/进行中/`, and `项目/已完成/`. Use `git mv` so history follows the folder.

**Archive**: move completed or expired material from `文档/` or `项目/已完成/` into `归档/YYYY年/月份/`, again with `git mv`.

**Touching README.md**: it ends with a `*最后更新：YYYY-MM-DD*` line. Update that date whenever you change the README's substance.

## Git Workflow

- **The default branch is `claude/create-work-repository-m6DRs`** — there is no `main` or `master`. Always branch from and compare against that ref; a local `master` in a fresh clone will be empty and unrelated.
- Feature branches follow `claude/<topic>-<suffix>`.
- **Commit messages are in Chinese**: a verb-first subject with no type prefix and no trailing period (`添加工作总结与工作方案模板，更新 README 目录结构`), optionally followed by a blank line and a `- ` bullet body naming each file added or changed and what it contains.
- Push with `git push -u origin <branch>`; open a PR only when asked.

## Parallel Branch Work (not on the default branch)

Two branches carry work that has not been merged. Check them before duplicating effort:

- **`claude/organize-work-content-ccZYo`** — a Python automation suite under `scripts/` that scans Google Drive, classifies files by keyword/MIME rules, detects duplicates (MD5 exact match plus filename similarity via `difflib`), writes a daily Markdown log to `日志/`, and optionally git-commits it. Entry points: `python3 scripts/setup_auth.py` (one-time OAuth2, needs `credentials.json` from Google Cloud Console) then `python3 scripts/daily_sync.py [--days-back N] [--dry-run] [--no-commit] [--verbose]`. Behavior is driven by `scripts/config.yaml`; deps are in `scripts/requirements.txt`. That branch's `.gitignore` excludes `scripts/token.json` and `scripts/credentials.json` — **never commit either**, and never commit OAuth tokens or client secrets to this repo on any branch.
- **`claude/implement-set-xJh8a`** — the pre-merge state of PR #1; superseded by the default branch.

If asked to work on the Drive automation, branch from `claude/organize-work-content-ccZYo` rather than the default branch, and note that this file's "no code" framing does not apply there.

## Things to Avoid

- Renaming or translating the Chinese directory names — external tooling and the README both depend on them.
- Introducing a build system, package manifest, or CI for what is a document repository.
- Filling templates with invented sample data. Blank fields are intentional; if illustrative content is genuinely wanted, put it in a separate example document under `文档/`, not in `模板/`.
- Committing anything real and confidential (signed contracts, personal contact details, credentials) without the user asking for it explicitly.
