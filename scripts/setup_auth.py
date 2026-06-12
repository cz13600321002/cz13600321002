#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Drive OAuth2 一次性授权工具

使用方式：
  1. 从 Google Cloud Console 下载 credentials.json 放到 scripts/ 目录
  2. 运行本脚本：python3 scripts/setup_auth.py
  3. 浏览器中完成授权后，token.json 将自动保存
"""

import os
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
CREDENTIALS_FILE = SCRIPTS_DIR / "credentials.json"
TOKEN_FILE = SCRIPTS_DIR / "token.json"

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
]


def main():
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        print("错误：缺少依赖，请先运行：")
        print("  pip3 install -r scripts/requirements.txt")
        sys.exit(1)

    if not CREDENTIALS_FILE.exists():
        print("错误：未找到 credentials.json")
        print()
        print("请按以下步骤获取凭据文件：")
        print("  1. 访问 Google Cloud Console (console.cloud.google.com)")
        print("  2. 创建项目或选择已有项目")
        print("  3. 启用 Google Drive API")
        print("  4. 创建 OAuth2 凭据（类型选择"桌面应用"）")
        print("  5. 下载 credentials.json 并放到 scripts/ 目录")
        sys.exit(1)

    print("正在启动 OAuth2 授权流程...")
    print("浏览器将自动打开，请登录 Google 账号并授权 Drive 读取权限。")
    print()

    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
    creds = flow.run_local_server(port=0)

    TOKEN_FILE.write_text(creds.to_json())
    print(f"授权成功！Token 已保存至：{TOKEN_FILE}")
    print()

    service = build("drive", "v3", credentials=creds)
    about = service.about().get(fields="user").execute()
    user = about.get("user", {})
    print(f"已授权账号：{user.get('displayName', '未知')} <{user.get('emailAddress', '未知')}>")
    print()
    print("现在可以运行每日整理脚本：")
    print("  python3 scripts/daily_sync.py")


if __name__ == "__main__":
    main()
