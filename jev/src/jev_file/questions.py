"""One System One request for every document.

Question ids are for code. The model only sees `instructions` and `criteria`.
Instructions and criteria are English because that is Jev's primary training
language; the Chinese document stays in `state`.
"""

from __future__ import annotations

from jev_file.catalog import DESTINATIONS

MODEL = "jev-latest"

# Character cap keeps `state` well under the 32k-token state budget.
BODY_CHAR_LIMIT = 12_000

# Starting gates. They are not fitted on this library. Chinese text is less
# accurate than English on the current model, and a wrong folder is annoying,
# so automatic filing stays stricter than the docs' low-stakes examples.
AUTO_FILE_CONFIDENCE = 0.80
TEMPLATE_YES = 0.65
TEMPLATE_NO = 0.35
OPEN_ACTIONS_YES = 0.70


def filing_questions() -> dict[str, dict]:
    return {
        "destination": {
            "type": "choice",
            "instructions": (
                "Which single library destination best fits `title` and `body`?"
            ),
            "criteria": {
                key: value["description"] for key, value in DESTINATIONS.items()
            },
        },
        "unfilled_template": {
            "type": "noul",
            "instructions": (
                "Is `body` an unfilled template or a skeleton of headings and "
                "blank placeholders, rather than a completed document?"
            ),
            "criteria": {
                "true": "Most substantive fields are empty, or the text is only a form.",
                "false": "The document contains completed prose, decisions, or filled entries.",
            },
        },
        "urgency": {
            "type": "score",
            "instructions": "How soon does `body` require someone to act?",
            "criteria": [
                "No deadline is stated, and nothing in the document is blocking other work.",
                "The document names work to handle within the coming weeks, without a same-day blocker.",
                "The document states a same-day deadline, an outage, or work that is currently blocked.",
            ],
        },
        "open_actions": {
            "type": "noul",
            "instructions": (
                "If this is an operational work document rather than reference "
                "or archive material, does `body` leave at least one concrete "
                "task unfinished?"
            ),
            "criteria": {
                "true": "A follow-up is named and is not marked done.",
                "false": "No open follow-up is stated, or every named task is already complete.",
            },
        },
    }
