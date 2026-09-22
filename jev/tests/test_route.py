from jev_file.catalog import DESTINATIONS
from jev_file.questions import filing_questions
from jev_file.route import decide, review_sort_key


def _response(
    choice="doc_minutes",
    confidence=0.91,
    template=0.05,
    urgency=1.2,
    open_actions=0.88,
    probabilities=None,
):
    if probabilities is None:
        probabilities = {choice: 0.94, "other": 0.06}
    return {
        "model": "jev-1.13.0",
        "answers": {
            "destination": {
                "choice": choice,
                "confidence": confidence,
                "probabilities": probabilities,
            },
            "unfilled_template": {"noul": template},
            "urgency": {"score": urgency},
            "open_actions": {"noul": open_actions},
        },
    }


def test_questions_share_one_request():
    questions = filing_questions()
    assert set(questions) == {
        "destination",
        "unfilled_template",
        "urgency",
        "open_actions",
    }
    assert questions["destination"]["type"] == "choice"
    assert "other" in questions["destination"]["criteria"]
    assert questions["destination"]["criteria"].keys() == DESTINATIONS.keys()
    assert len(questions["urgency"]["criteria"]) == 3


def test_clear_minutes_can_be_filed_and_keeps_open_actions():
    decision = decide(_response())
    assert decision.action == "file"
    assert decision.relative_path == "文档/会议纪要"
    assert decision.urgency_band == "本周"
    assert decision.open_actions_noul == 0.88
    assert decision.model == "jev-1.13.0"


def test_low_confidence_stays_with_a_person():
    decision = decide(_response(confidence=0.62, probabilities={"doc_minutes": 0.55, "doc_report": 0.40}))
    assert decision.action == "review"
    assert "人工" in decision.reason


def test_blank_template_is_not_filed_even_when_the_folder_looks_obvious():
    decision = decide(_response(choice="doc_report", confidence=0.95, template=0.9))
    assert decision.action == "review"
    assert "模板" in decision.reason


def test_other_never_files():
    decision = decide(_response(choice="other", confidence=0.99, template=0.0))
    assert decision.action == "review"
    assert decision.relative_path is None


def test_reference_material_drops_the_speculative_follow_up():
    decision = decide(_response(choice="ref_industry", open_actions=0.99))
    assert decision.action == "file"
    assert decision.open_actions_noul is None


def test_same_day_urgency_is_a_threshold_not_a_ratio():
    assert decide(_response(urgency=1.5)).urgency_band == "今天"
    assert decide(_response(urgency=0.49)).urgency_band == "可稍后"


def test_review_queue_puts_uncertain_urgent_items_first():
    holding = decide(_response(confidence=0.4, urgency=1.8))
    ready = decide(_response(urgency=2.0))
    later = decide(_response(confidence=0.4, urgency=0.2))
    ordered = sorted([ready, later, holding], key=review_sort_key)
    assert ordered == [holding, later, ready]
