from datetime import datetime
from pathlib import Path

from jev_file.document import extract_title, filing_filename, filing_stamp, load_document


def test_title_and_chinese_date(tmp_path: Path):
    path = tmp_path / "笔记.md"
    path.write_text("# 周例会纪要\n\n会议时间：2026年4月9日\n", encoding="utf-8")
    state = load_document(path)
    assert state.title == "周例会纪要"
    assert state.stamp == "20260409"
    assert state.body_truncated is False
    assert filing_filename(path, state.title, state.stamp) == "20260409_周例会纪要.md"


def test_existing_date_prefix_is_kept(tmp_path: Path):
    path = tmp_path / "20260409_周例会.md"
    path.write_text("正文", encoding="utf-8")
    assert filing_stamp(path, "正文") == "20260409"
    assert filing_filename(path, "别的标题", "20260409") == "20260409_周例会.md"


def test_invalid_calendar_date_falls_through_to_mtime(tmp_path: Path):
    path = tmp_path / "草稿.md"
    path.write_text("截止 2026年13月40日", encoding="utf-8")
    stamp = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y%m%d")
    assert filing_stamp(path, path.read_text(encoding="utf-8")) == stamp


def test_long_body_is_marked_truncated(tmp_path: Path):
    path = tmp_path / "长文.md"
    path.write_text("甲" * 12_001, encoding="utf-8")
    state = load_document(path)
    assert state.body_truncated is True
    assert len(state.body) == 12_000
    assert extract_title("没有标题\n") == ""
