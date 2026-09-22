"""Closed destinations in the work library.

The Choice options are the folders the library already uses. `other` is the
escape hatch: a Choice must sum to 1, so an unlisted kind would otherwise
land on the least-wrong folder.
"""

from __future__ import annotations

DESTINATIONS: dict[str, dict[str, str | None]] = {
    "doc_report": {
        "path": "文档/报告",
        "description": (
            "A completed status report of work already done: a weekly report, "
            "a monthly report, or a work summary."
        ),
    },
    "doc_plan": {
        "path": "文档/方案",
        "description": (
            "A proposal or work scheme for how future work should be carried "
            "out, when it is a standalone document rather than a project folder."
        ),
    },
    "doc_contract": {
        "path": "文档/合同",
        "description": "A contract, agreement, or set of terms.",
    },
    "doc_minutes": {
        "path": "文档/会议纪要",
        "description": (
            "Minutes of a meeting that already happened, including topic, "
            "attendees, or decisions."
        ),
    },
    "project_active": {
        "path": "项目/进行中",
        "description": "Working material for a project that is already underway.",
    },
    "project_pending": {
        "path": "项目/待启动",
        "description": "Material for a project that is defined and has not started.",
    },
    "project_done": {
        "path": "项目/已完成",
        "description": "Material for a project that has finished.",
    },
    "ref_industry": {
        "path": "资料/行业资料",
        "description": "Industry or market background kept for reference.",
    },
    "ref_standard": {
        "path": "资料/规范标准",
        "description": "A norm, standard, specification, or compliance rule.",
    },
    "ref_bibliography": {
        "path": "资料/参考文献",
        "description": "A citation, paper note, book note, or bibliography entry.",
    },
    "archive": {
        "path": "归档",
        "description": "A document that is explicitly historical, expired, or superseded.",
    },
    "other": {
        "path": None,
        "description": (
            "None of the destinations fit, or the text is too thin to choose one."
        ),
    },
}

# Open follow-ups matter for operational documents. Reference and archive
# placements ignore that answer.
ACTIONABLE = frozenset(
    {
        "doc_report",
        "doc_plan",
        "doc_contract",
        "doc_minutes",
        "project_active",
        "project_pending",
        "project_done",
    }
)


def destination_path(choice: str) -> str | None:
    item = DESTINATIONS.get(choice)
    if item is None:
        return None
    return item["path"]
