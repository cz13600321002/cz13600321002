"""Turn a file into state. Dates and titles are exact, so code extracts them."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from jev_file.questions import BODY_CHAR_LIMIT

_HEADING = re.compile(r"^#\s+(.+?)\s*$")
_FILENAME_DATE = re.compile(r"^(20\d{6})(?:[_-]|\.)")
_COMPACT_DATE = re.compile(r"(20\d{2})(\d{2})(\d{2})")
_SPLIT_DATE = re.compile(
    r"(20\d{2})\s*[-/.年]\s*(\d{1,2})\s*[-/.月]\s*(\d{1,2})"
)
_ILLEGAL = re.compile(r'[\\/:*?"<>|\x00-\x1f]+')


@dataclass(frozen=True)
class DocumentState:
    path: Path
    filename: str
    title: str
    body: str
    body_truncated: bool
    stamp: str

    def as_state(self) -> dict[str, object]:
        return {
            "filename": self.filename,
            "title": self.title,
            "body": self.body,
            "body_truncated": self.body_truncated,
        }


def load_document(path: Path) -> DocumentState:
    text = path.read_text(encoding="utf-8")
    body, truncated = _clip(text)
    return DocumentState(
        path=path,
        filename=path.name,
        title=extract_title(text),
        body=body,
        body_truncated=truncated,
        stamp=filing_stamp(path, text),
    )


def extract_title(text: str) -> str:
    for line in text.splitlines():
        match = _HEADING.match(line)
        if match:
            return match.group(1).strip()
    return ""


def filing_stamp(path: Path, text: str) -> str:
    from_name = _FILENAME_DATE.match(path.name)
    if from_name and _valid_day(from_name.group(1)):
        return from_name.group(1)
    found = _first_valid_date(text)
    if found:
        return found
    modified = datetime.fromtimestamp(path.stat().st_mtime)
    return modified.strftime("%Y%m%d")


def filing_filename(path: Path, title: str, stamp: str) -> str:
    if _FILENAME_DATE.match(path.stem):
        base = _sanitize(path.stem)
    else:
        label = _sanitize(title) or _sanitize(path.stem) or "未命名"
        if label.startswith(stamp):
            base = label
        else:
            base = f"{stamp}_{label}"
    suffix = path.suffix if path.suffix else ".md"
    return f"{base}{suffix}"


def _clip(text: str) -> tuple[str, bool]:
    if len(text) <= BODY_CHAR_LIMIT:
        return text, False
    return text[:BODY_CHAR_LIMIT], True


def _first_valid_date(text: str) -> str | None:
    candidates: list[tuple[int, str]] = []
    for match in _SPLIT_DATE.finditer(text):
        stamp = _pack(match.group(1), match.group(2), match.group(3))
        if stamp:
            candidates.append((match.start(), stamp))
    for match in _COMPACT_DATE.finditer(text):
        stamp = match.group(0)
        if _valid_day(stamp):
            candidates.append((match.start(), stamp))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def _pack(year: str, month: str, day: str) -> str | None:
    stamp = f"{year}{int(month):02d}{int(day):02d}"
    if _valid_day(stamp):
        return stamp
    return None


def _valid_day(stamp: str) -> bool:
    try:
        datetime.strptime(stamp, "%Y%m%d")
    except ValueError:
        return False
    return True


def _sanitize(value: str) -> str:
    cleaned = _ILLEGAL.sub(" ", value)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    return cleaned[:80]
