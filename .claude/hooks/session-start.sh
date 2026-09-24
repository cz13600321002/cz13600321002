#!/bin/bash
# SessionStart hook for Claude Code on the web.
# 本文库以 Markdown 文档为主：安装 markdownlint-cli2 用于文档格式检查；
# 若日后加入 Python 脚本（配方计算、数据清理等）及依赖清单，则自动安装其依赖。
set -euo pipefail

# 仅在远程（Web）环境执行
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(pwd)}"

# 1. Markdown linter（幂等：已安装则跳过）
if ! command -v markdownlint-cli2 >/dev/null 2>&1; then
  npm install -g markdownlint-cli2 --no-audit --no-fund --loglevel=error
fi

# 2. Python 依赖（仅在存在依赖清单时安装）
if [ -f requirements.txt ]; then
  pip3 install --quiet -r requirements.txt
fi
if [ -f pyproject.toml ]; then
  pip3 install --quiet -e .
fi
