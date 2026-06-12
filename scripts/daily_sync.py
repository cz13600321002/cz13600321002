#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Drive 每日工作内容整理脚本

功能：
  - 扫描 Google Drive 中最近修改的文件
  - 按文档类型自动分类
  - 检测疑似重复文件（MD5精确匹配 + 文件名相似度）
  - 生成 Markdown 格式工作日志，保存到 日志/ 目录
  - 自动 git commit 日志文件

使用方式：
  python3 scripts/daily_sync.py                # 扫描昨日至今
  python3 scripts/daily_sync.py --days-back 7  # 扫描过去7天
  python3 scripts/daily_sync.py --dry-run      # 仅输出，不写文件
"""

import argparse
import difflib
import json
import logging
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

SCRIPTS_DIR = Path(__file__).parent
REPO_ROOT = SCRIPTS_DIR.parent
CONFIG_FILE = SCRIPTS_DIR / "config.yaml"
CREDENTIALS_FILE = SCRIPTS_DIR / "credentials.json"
TOKEN_FILE = SCRIPTS_DIR / "token.json"

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
]

WEEKDAY_NAMES = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]


# ─── 数据类 ──────────────────────────────────────────────────────────────────

@dataclass
class DriveFile:
    file_id: str
    name: str
    mime_type: str
    modified_time: datetime
    created_time: datetime
    size: Optional[int]
    parents: List[str]
    md5_checksum: Optional[str]
    web_view_link: str


@dataclass
class ClassifiedFile:
    drive_file: DriveFile
    doc_type: str
    mime_category: str
    activity: str  # "新建" 或 "修改"


@dataclass
class DuplicateGroup:
    group_type: str  # "exact" 或 "similar"
    files: List[ClassifiedFile]
    similarity_score: float
    suggested_keep: Optional[ClassifiedFile] = None

    def __post_init__(self):
        if self.suggested_keep is None and self.files:
            self.suggested_keep = max(
                self.files, key=lambda f: f.drive_file.modified_time
            )


# ─── 认证 ────────────────────────────────────────────────────────────────────

class DriveAuthenticator:
    def authenticate(self):
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except ImportError:
            logging.error("缺少依赖，请运行：pip3 install -r scripts/requirements.txt")
            sys.exit(1)

        creds = None
        if TOKEN_FILE.exists():
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logging.info("刷新 OAuth2 Token...")
                creds.refresh(Request())
                TOKEN_FILE.write_text(creds.to_json())
            elif not sys.stdin.isatty():
                logging.error(
                    "Token 不存在或已失效，且当前非交互环境（cron）无法重新授权。\n"
                    "请手动运行：python3 scripts/setup_auth.py"
                )
                sys.exit(1)
            else:
                if not CREDENTIALS_FILE.exists():
                    logging.error(
                        "未找到 credentials.json，请先运行：python3 scripts/setup_auth.py"
                    )
                    sys.exit(1)
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(CREDENTIALS_FILE), SCOPES
                )
                creds = flow.run_local_server(port=0)
                TOKEN_FILE.write_text(creds.to_json())

        return build("drive", "v3", credentials=creds)


# ─── 扫描 ────────────────────────────────────────────────────────────────────

class DriveScanner:
    def __init__(self, service, scan_root: str = "root"):
        self.service = service
        self.scan_root = scan_root

    def scan_recent(self, days_back: int = 1) -> List[DriveFile]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
        cutoff_str = cutoff.strftime("%Y-%m-%dT%H:%M:%S")
        query = (
            f"modifiedTime > '{cutoff_str}' "
            f"and trashed = false "
            f"and mimeType != 'application/vnd.google-apps.folder'"
        )
        if self.scan_root != "root":
            query += f" and '{self.scan_root}' in parents"
        return self._execute_query(query)

    def scan_all(self) -> List[DriveFile]:
        query = "trashed = false and mimeType != 'application/vnd.google-apps.folder'"
        if self.scan_root != "root":
            query += f" and '{self.scan_root}' in parents"
        return self._execute_query(query)

    def _execute_query(self, query: str) -> List[DriveFile]:
        files = []
        page_token = None
        fields = (
            "nextPageToken, files("
            "id, name, mimeType, modifiedTime, createdTime, "
            "size, parents, md5Checksum, webViewLink)"
        )
        while True:
            kwargs = {"q": query, "fields": fields, "pageSize": 100}
            if page_token:
                kwargs["pageToken"] = page_token
            result = self.service.files().list(**kwargs).execute()
            for f in result.get("files", []):
                files.append(self._parse_file(f))
            page_token = result.get("nextPageToken")
            if not page_token:
                break
        return files

    @staticmethod
    def _parse_file(raw: dict) -> DriveFile:
        def parse_dt(s: str) -> datetime:
            return datetime.fromisoformat(s.replace("Z", "+00:00"))

        return DriveFile(
            file_id=raw["id"],
            name=raw.get("name", ""),
            mime_type=raw.get("mimeType", ""),
            modified_time=parse_dt(raw.get("modifiedTime", "1970-01-01T00:00:00Z")),
            created_time=parse_dt(raw.get("createdTime", "1970-01-01T00:00:00Z")),
            size=int(raw["size"]) if raw.get("size") else None,
            parents=raw.get("parents", []),
            md5_checksum=raw.get("md5Checksum"),
            web_view_link=raw.get("webViewLink", ""),
        )


# ─── 分类 ────────────────────────────────────────────────────────────────────

MIME_NAMES: Dict[str, str] = {
    "application/vnd.google-apps.document": "Google 文档",
    "application/vnd.google-apps.spreadsheet": "Google 表格",
    "application/vnd.google-apps.presentation": "Google 幻灯片",
    "application/vnd.google-apps.form": "Google 表单",
    "application/pdf": "PDF 文件",
    "application/msword": "Word 文档",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "Word 文档",
    "application/vnd.ms-excel": "Excel 表格",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "Excel 表格",
    "application/vnd.ms-powerpoint": "PPT 演示",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "PPT 演示",
    "text/plain": "文本文件",
    "text/markdown": "Markdown 文件",
    "image/jpeg": "图片",
    "image/png": "图片",
    "image/gif": "图片",
}


class FileOrganizer:
    def __init__(self, config: dict):
        self.categories = config.get("categories", [])
        self.mime_names = config.get("mime_type_names", MIME_NAMES)

    def classify(self, file: DriveFile) -> ClassifiedFile:
        mime_cat = self.mime_names.get(file.mime_type, "其他文件")
        doc_type = self._match_doc_type(file.name, file.mime_type)

        now = datetime.now(timezone.utc)
        created_today = (now - file.created_time).total_seconds() < 86400
        activity = "新建" if created_today else "修改"

        return ClassifiedFile(
            drive_file=file,
            doc_type=doc_type,
            mime_category=mime_cat,
            activity=activity,
        )

    def _match_doc_type(self, name: str, mime_type: str) -> str:
        name_lower = name.lower()
        for cat in self.categories:
            if mime_type in cat.get("mime_types", []):
                return cat["name"]
            for kw in cat.get("keywords", []):
                if kw.lower() in name_lower:
                    return cat["name"]
        return "其他文档"

    def suggest_path(self, cf: ClassifiedFile) -> str:
        for cat in self.categories:
            if cf.doc_type == cat["name"]:
                return cat.get("target_dir", "文档")
        return "文档"


# ─── 重复检测 ─────────────────────────────────────────────────────────────────

class DuplicateDetector:
    def __init__(self, threshold: float = 0.85):
        self.threshold = threshold

    def detect(
        self, files: List[ClassifiedFile]
    ) -> Tuple[List[DuplicateGroup], List[DuplicateGroup]]:
        exact_groups = self._find_exact(files)
        exact_ids = {f.drive_file.file_id for g in exact_groups for f in g.files}
        remaining = [f for f in files if f.drive_file.file_id not in exact_ids]
        similar_groups = self._find_similar(remaining)
        return exact_groups, similar_groups

    def _find_exact(self, files: List[ClassifiedFile]) -> List[DuplicateGroup]:
        by_md5: Dict[str, List[ClassifiedFile]] = {}
        for cf in files:
            md5 = cf.drive_file.md5_checksum
            if md5:
                by_md5.setdefault(md5, []).append(cf)
        groups = []
        for md5, group in by_md5.items():
            if len(group) >= 2:
                groups.append(DuplicateGroup("exact", group, 1.0))
        return groups

    def _find_similar(self, files: List[ClassifiedFile]) -> List[DuplicateGroup]:
        by_mime: Dict[str, List[ClassifiedFile]] = {}
        for cf in files:
            by_mime.setdefault(cf.mime_category, []).append(cf)

        groups: List[DuplicateGroup] = []
        for bucket in by_mime.values():
            if len(bucket) < 2:
                continue
            merged = self._union_find_groups(bucket)
            for group in merged:
                if len(group) >= 2:
                    ratio = self._avg_similarity(group)
                    groups.append(DuplicateGroup("similar", group, ratio))
        return groups

    def _union_find_groups(
        self, files: List[ClassifiedFile]
    ) -> List[List[ClassifiedFile]]:
        parent = list(range(len(files)))
        norms = [self._normalize(f.drive_file.name) for f in files]

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x, y):
            parent[find(x)] = find(y)

        for i in range(len(files)):
            for j in range(i + 1, len(files)):
                ratio = difflib.SequenceMatcher(None, norms[i], norms[j]).ratio()
                if ratio >= self.threshold:
                    union(i, j)

        groups_map: Dict[int, List[ClassifiedFile]] = {}
        for i, f in enumerate(files):
            root = find(i)
            groups_map.setdefault(root, []).append(f)
        return list(groups_map.values())

    @staticmethod
    def _normalize(name: str) -> str:
        name = re.sub(r"\.[^.]{1,5}$", "", name)
        name = re.sub(r"\d{4}[-/]?\d{2}[-/]?\d{2}", "", name)
        name = re.sub(
            r"[_\-\s]*(副本|copy|备份|final|v\d+|\(\d+\)|（\d+）)",
            "",
            name,
            flags=re.IGNORECASE,
        )
        return re.sub(r"\s+", "", name).lower()

    @staticmethod
    def _avg_similarity(files: List[ClassifiedFile]) -> float:
        norms = [DuplicateDetector._normalize(f.drive_file.name) for f in files]
        if len(norms) < 2:
            return 1.0
        scores = []
        for i in range(len(norms)):
            for j in range(i + 1, len(norms)):
                scores.append(
                    difflib.SequenceMatcher(None, norms[i], norms[j]).ratio()
                )
        return sum(scores) / len(scores) if scores else 0.0


# ─── 日志生成 ─────────────────────────────────────────────────────────────────

class LogGenerator:
    def __init__(self, repo_root: Path, log_dir: str = "日志"):
        self.repo_root = repo_root
        self.log_dir = repo_root / log_dir

    def generate(
        self,
        classified: List[ClassifiedFile],
        exact_groups: List[DuplicateGroup],
        similar_groups: List[DuplicateGroup],
        scan_date: datetime,
        days_back: int,
    ) -> str:
        lines = []
        weekday = WEEKDAY_NAMES[scan_date.weekday()]
        title_date = scan_date.strftime(f"%Y年%m月%d日（{weekday}）")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        lines.append(f"# 工作日志 {title_date}")
        lines.append("")
        lines.append(
            f"> 自动生成于 {now_str} | 扫描范围：过去 {days_back} 天 | 文件总数：{len(classified)}"
        )
        lines.append("")
        lines.append("---")

        new_files = [f for f in classified if f.activity == "新建"]
        mod_files = [f for f in classified if f.activity == "修改"]
        dup_count = len(exact_groups) + len(similar_groups)
        wasted = self._wasted_space(exact_groups)

        lines.append("")
        lines.append("## 一、今日文件活动汇总")
        lines.append("")
        lines.append("| 统计项 | 数量 |")
        lines.append("|--------|------|")
        lines.append(f"| 新建文件 | {len(new_files)} |")
        lines.append(f"| 修改文件 | {len(mod_files)} |")
        lines.append(f"| 疑似重复文件组 | {dup_count} |")
        lines.append(f"| 可释放空间估算 | {self._fmt_size(wasted)} |")

        lines.extend(self._section_files("## 二、新建文件", new_files))
        lines.extend(self._section_files("## 三、修改文件", mod_files))
        lines.extend(self._section_type_stats("## 四、文档类型统计", classified))
        lines.extend(self._section_duplicates(exact_groups, similar_groups))
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("*此日志由 `scripts/daily_sync.py` 自动生成，请勿手动编辑*")
        lines.append("")

        return "\n".join(lines)

    def save(
        self,
        content: str,
        scan_date: datetime,
        dry_run: bool = False,
    ) -> Optional[Path]:
        log_path = (
            self.log_dir
            / scan_date.strftime("%Y年")
            / scan_date.strftime("%m月")
            / scan_date.strftime("%Y%m%d_工作日志.md")
        )
        if dry_run:
            print(content)
            return None

        log_path.parent.mkdir(parents=True, exist_ok=True)

        if log_path.exists():
            existing = log_path.read_text(encoding="utf-8")
            run_time = datetime.now().strftime("%H:%M:%S")
            append_section = (
                f"\n---\n\n"
                f"## 更新记录 - {run_time}\n\n"
                f"> 当日第二次运行，以下内容为本次增量扫描\n\n"
            )
            log_path.write_text(existing + append_section + content, encoding="utf-8")
        else:
            tmp = log_path.with_suffix(".tmp")
            tmp.write_text(content, encoding="utf-8")
            tmp.rename(log_path)

        return log_path

    def git_commit(self, log_path: Path) -> bool:
        try:
            rel = log_path.relative_to(self.repo_root)
            subprocess.run(
                ["git", "-C", str(self.repo_root), "add", str(rel)],
                check=True, capture_output=True,
            )
            date_str = log_path.stem.split("_")[0]
            msg = f"自动生成 {date_str} 工作日志"
            subprocess.run(
                ["git", "-C", str(self.repo_root), "commit", "-m", msg],
                check=True, capture_output=True,
            )
            logging.info(f"已提交日志：{rel}")
            return True
        except subprocess.CalledProcessError as e:
            logging.warning(f"git commit 失败：{e.stderr.decode()}")
            return False

    # ── 辅助方法 ──────────────────────────────────────────────────────────────

    def _section_files(self, heading: str, files: List[ClassifiedFile]) -> List[str]:
        lines = ["", heading, ""]
        if not files:
            lines.append("*（无）*")
            return lines
        lines.append("| 文件名 | 类型 | 分类 | 修改时间 | 链接 |")
        lines.append("|--------|------|------|---------|------|")
        for cf in sorted(files, key=lambda f: f.drive_file.modified_time, reverse=True):
            df = cf.drive_file
            t = df.modified_time.astimezone().strftime("%m-%d %H:%M")
            link = f"[查看]({df.web_view_link})" if df.web_view_link else "—"
            name = df.name[:40] + "…" if len(df.name) > 40 else df.name
            lines.append(
                f"| {name} | {cf.mime_category} | {cf.doc_type} | {t} | {link} |"
            )
        return lines

    def _section_type_stats(
        self, heading: str, files: List[ClassifiedFile]
    ) -> List[str]:
        lines = ["", heading, ""]
        if not files:
            lines.append("*（无文件）*")
            return lines
        stats: Dict[str, Dict[str, int]] = {}
        for cf in files:
            stats.setdefault(cf.doc_type, {"新建": 0, "修改": 0})
            stats[cf.doc_type][cf.activity] += 1
        lines.append("| 文档类型 | 新建 | 修改 | 合计 |")
        lines.append("|---------|------|------|------|")
        for dtype, cnt in sorted(stats.items(), key=lambda x: -(x[1]["新建"] + x[1]["修改"])):
            total = cnt["新建"] + cnt["修改"]
            lines.append(f"| {dtype} | {cnt['新建']} | {cnt['修改']} | {total} |")
        return lines

    def _section_duplicates(
        self,
        exact_groups: List[DuplicateGroup],
        similar_groups: List[DuplicateGroup],
    ) -> List[str]:
        lines = ["", "## 五、疑似重复文件"]
        if not exact_groups and not similar_groups:
            lines.append("")
            lines.append("*（未发现重复文件）*")
            return lines

        if exact_groups:
            lines.append("")
            lines.append("### 精确重复（MD5 相同）")
            for i, g in enumerate(exact_groups, 1):
                wasted = self._wasted_space([g])
                lines.append("")
                lines.append(f"#### 重复组 {i}（{len(g.files)} 个文件，可释放 {self._fmt_size(wasted)}）")
                lines.append("")
                lines.append("| 文件名 | 大小 | 修改时间 | 建议操作 |")
                lines.append("|--------|------|---------|---------|")
                for cf in g.files:
                    keep = cf is g.suggested_keep
                    t = cf.drive_file.modified_time.astimezone().strftime("%Y-%m-%d")
                    sz = self._fmt_size(cf.drive_file.size or 0)
                    action = "**保留**" if keep else "删除"
                    lines.append(f"| {cf.drive_file.name} | {sz} | {t} | {action} |")

        if similar_groups:
            lines.append("")
            lines.append("### 相似文件名")
            for i, g in enumerate(similar_groups, 1):
                lines.append("")
                lines.append(f"#### 相似组 {i}（相似度：{g.similarity_score:.0%}）")
                lines.append("")
                lines.append("| 文件名 | 大小 | 修改时间 | 建议操作 |")
                lines.append("|--------|------|---------|---------|")
                for cf in g.files:
                    keep = cf is g.suggested_keep
                    t = cf.drive_file.modified_time.astimezone().strftime("%Y-%m-%d")
                    sz = self._fmt_size(cf.drive_file.size or 0)
                    action = "**保留**" if keep else "请确认"
                    lines.append(f"| {cf.drive_file.name} | {sz} | {t} | {action} |")

        lines.append("")
        lines.append("> 注意：以上仅为建议，删除操作需手动在 Google Drive 中执行。")
        return lines

    @staticmethod
    def _wasted_space(groups: List[DuplicateGroup]) -> int:
        total = 0
        for g in groups:
            sizes = [f.drive_file.size or 0 for f in g.files]
            if sizes:
                total += sum(sizes) - max(sizes)
        return total

    @staticmethod
    def _fmt_size(size: int) -> str:
        if size < 1024:
            return f"{size} B"
        if size < 1024 ** 2:
            return f"{size / 1024:.1f} KB"
        if size < 1024 ** 3:
            return f"{size / 1024 ** 2:.1f} MB"
        return f"{size / 1024 ** 3:.1f} GB"


# ─── 主流程 ───────────────────────────────────────────────────────────────────

def load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    with open(CONFIG_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def main():
    parser = argparse.ArgumentParser(description="Google Drive 每日工作内容整理")
    parser.add_argument("--days-back", type=int, default=None, help="扫描过去 N 天（默认读取配置）")
    parser.add_argument("--dry-run", action="store_true", help="仅输出日志，不写文件不提交")
    parser.add_argument("--no-commit", action="store_true", help="写文件但不 git commit")
    parser.add_argument("--verbose", action="store_true", help="显示详细日志")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    config = load_config()
    days_back = args.days_back or config.get("recent_days", 1)
    scan_root = config.get("scan_root", "root")
    dup_threshold = config.get("duplicate_threshold", 0.85)
    auto_commit = config.get("auto_git_commit", True) and not args.no_commit
    log_dir = config.get("log_dir", "日志")

    logging.info(f"开始扫描 Google Drive（过去 {days_back} 天）...")
    service = DriveAuthenticator().authenticate()

    scanner = DriveScanner(service, scan_root)
    recent_files = scanner.scan_recent(days_back)
    logging.info(f"找到 {len(recent_files)} 个最近修改的文件")

    organizer = FileOrganizer(config)
    classified = [organizer.classify(f) for f in recent_files]

    logging.info("检测重复文件...")
    if config.get("full_scan_for_duplicates", True):
        all_files = scanner.scan_all()
        all_classified = [organizer.classify(f) for f in all_files]
        logging.info(f"全量扫描：共 {len(all_classified)} 个文件")
    else:
        all_classified = classified

    detector = DuplicateDetector(dup_threshold)
    exact_groups, similar_groups = detector.detect(all_classified)
    logging.info(f"发现精确重复组：{len(exact_groups)}，相似文件组：{len(similar_groups)}")

    scan_date = datetime.now()
    generator = LogGenerator(REPO_ROOT, log_dir)
    content = generator.generate(classified, exact_groups, similar_groups, scan_date, days_back)

    log_path = generator.save(content, scan_date, dry_run=args.dry_run)

    if log_path and auto_commit:
        generator.git_commit(log_path)

    if log_path:
        logging.info(f"日志已保存：{log_path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
