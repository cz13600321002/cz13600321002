import os
from pathlib import Path

import pytest

from jev_file.cli import _target_path, judge_paths, main
from jev_file.route import FilingDecision


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def system_one(self, *, state, questions, model):
        self.calls.append({"state": state, "questions": questions, "model": model})
        return self.response


def _response():
    return {
        "model": "jev-1.13.0",
        "answers": {
            "destination": {
                "choice": "doc_minutes",
                "confidence": 0.92,
                "probabilities": {"doc_minutes": 0.95, "doc_report": 0.05},
            },
            "unfilled_template": {"noul": 0.04},
            "urgency": {"score": 1.7},
            "open_actions": {"noul": 0.8},
        },
    }


def test_one_call_carries_every_question_and_apply_moves(tmp_path: Path):
    source = tmp_path / "收件" / "纪要.md"
    source.parent.mkdir()
    source.write_text("# 周例会纪要\n\n会议时间：2026年4月9日\n李强周五前交报价。\n", encoding="utf-8")
    library = tmp_path
    client = FakeClient(_response())

    rows = judge_paths([source], library, apply=True, client=client)

    assert len(client.calls) == 1
    assert set(client.calls[0]["questions"]) == {
        "destination",
        "unfilled_template",
        "urgency",
        "open_actions",
    }
    assert client.calls[0]["model"] == "jev-latest"
    assert client.calls[0]["state"]["title"] == "周例会纪要"
    assert rows[0]["moved"] is True
    assert rows[0]["urgency_band"] == "今天"
    target = library / "文档" / "会议纪要" / "20260409_周例会纪要.md"
    assert target.is_file()
    assert not source.exists()


def test_existing_target_is_not_overwritten(tmp_path: Path):
    source = tmp_path / "纪要.md"
    source.write_text("# 周例会纪要\n\n2026年4月9日\n", encoding="utf-8")
    target = tmp_path / "文档" / "会议纪要" / "20260409_周例会纪要.md"
    target.parent.mkdir(parents=True)
    target.write_text("已有", encoding="utf-8")

    rows = judge_paths([source], tmp_path, apply=True, client=FakeClient(_response()))

    assert rows[0]["moved"] is False
    assert rows[0]["action"] == "review"
    assert target.read_text(encoding="utf-8") == "已有"
    assert source.is_file()


def test_destination_cannot_leave_the_library(tmp_path: Path):
    decision = FilingDecision(
        destination="doc_minutes",
        relative_path="../outside",
        confidence=0.9,
        probabilities={},
        template_noul=0.0,
        urgency_score=0.0,
        urgency_band="可稍后",
        open_actions_noul=None,
        action="file",
        reason="",
        model="jev-1.13.0",
    )
    with pytest.raises(ValueError):
        _target_path(tmp_path, tmp_path / "a.md", "标题", "20260409", decision)


def test_missing_key_exits_before_any_call(monkeypatch, capsys):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    assert os.environ.get("TYPESAFE_API_KEY") in (None, "")
    code = main(["missing.md"])
    assert code == 2
    assert "TYPESAFE_API_KEY" in capsys.readouterr().err
