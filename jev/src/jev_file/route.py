"""Compose Jev answers into a filing action. Policy lives here, not in the model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from jev_file.catalog import ACTIONABLE, destination_path
from jev_file.questions import (
    AUTO_FILE_CONFIDENCE,
    OPEN_ACTIONS_YES,
    TEMPLATE_NO,
    TEMPLATE_YES,
)


@dataclass(frozen=True)
class FilingDecision:
    destination: str
    relative_path: str | None
    confidence: float
    probabilities: dict[str, float]
    template_noul: float
    urgency_score: float
    urgency_band: str
    open_actions_noul: float | None
    action: str
    reason: str
    model: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "destination": self.destination,
            "relative_path": self.relative_path,
            "confidence": self.confidence,
            "probabilities": self.probabilities,
            "template_noul": self.template_noul,
            "urgency_score": self.urgency_score,
            "urgency_band": self.urgency_band,
            "open_actions_noul": self.open_actions_noul,
            "action": self.action,
            "reason": self.reason,
            "model": self.model,
        }


def decide(response: Any) -> FilingDecision:
    destination = _answer(response, "destination")
    template = _answer(response, "unfilled_template")
    urgency = _answer(response, "urgency")
    actions = _answer(response, "open_actions")

    choice = str(_field(destination, "choice"))
    confidence = float(_field(destination, "confidence"))
    probabilities = {
        str(key): float(value)
        for key, value in _field(destination, "probabilities").items()
    }
    template_noul = float(_field(template, "noul"))
    urgency_score = float(_field(urgency, "score"))
    open_noul = float(_field(actions, "noul"))
    shown_actions = open_noul if choice in ACTIONABLE else None

    relative = destination_path(choice)
    action, reason = _action(choice, confidence, template_noul, relative)

    return FilingDecision(
        destination=choice,
        relative_path=relative,
        confidence=confidence,
        probabilities=probabilities,
        template_noul=template_noul,
        urgency_score=urgency_score,
        urgency_band=urgency_band(urgency_score),
        open_actions_noul=shown_actions,
        action=action,
        reason=reason,
        model=str(_field(response, "model")),
    )


def urgency_band(score: float) -> str:
    if score >= 1.5:
        return "今天"
    if score >= 0.5:
        return "本周"
    return "可稍后"


def review_sort_key(decision: FilingDecision) -> tuple[int, float]:
    pending = 0 if decision.action == "review" else 1
    return (pending, -decision.urgency_score)


def _action(
    choice: str,
    confidence: float,
    template_noul: float,
    relative: str | None,
) -> tuple[str, str]:
    if choice == "other" or relative is None:
        return "review", "没有对应目录，留给人工。"
    if template_noul >= TEMPLATE_YES:
        return "review", "更像未填写的模板，不自动入库。"
    if confidence < AUTO_FILE_CONFIDENCE:
        return "review", "目录判断不够集中，先人工确认。"
    if template_noul > TEMPLATE_NO:
        return "review", "分不清是成稿还是空白模板。"
    return "file", "目录明确，且正文不像空白模板。"


def _answer(response: Any, key: str) -> Any:
    answers = _field(response, "answers")
    try:
        return answers[key]
    except (KeyError, TypeError) as exc:
        raise KeyError(f"响应里没有问题 {key}") from exc


def _field(obj: Any, name: str) -> Any:
    if isinstance(obj, dict):
        return obj[name]
    return getattr(obj, name)
