"""File work-library documents from one Jev call per file."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Sequence

from jev_file.catalog import destination_path
from jev_file.document import filing_filename, load_document
from jev_file.questions import MODEL, filing_questions
from jev_file.route import FilingDecision, decide, review_sort_key


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="用一次 Jev 调用判断工作文库文档该放进哪个目录。"
    )
    parser.add_argument("paths", nargs="+", type=Path, help="要判断的文件")
    parser.add_argument(
        "--library",
        type=Path,
        default=Path.cwd(),
        help="文库根目录，默认当前目录",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="只移动判定为可入库的文件；默认只打印建议",
    )
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args(argv)

    library = args.library.resolve()
    try:
        client = _client()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    try:
        rows = judge_paths(args.paths, library, apply=args.apply, client=client)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if args.json:
        json.dump(rows, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        for row in rows:
            _print_row(row)
    return 0


def judge_paths(
    paths: Sequence[Path],
    library: Path,
    *,
    apply: bool,
    client: Any,
) -> list[dict[str, Any]]:
    missing = [path for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"找不到文件：{missing[0]}")

    questions = filing_questions()
    rows: list[dict[str, Any]] = []
    with client:
        for path in paths:
            document = load_document(path)
            response = client.system_one(
                state=document.as_state(),
                questions=questions,
                model=MODEL,
            )
            decision = decide(response)
            target = _target_path(
                library, document.path, document.title, document.stamp, decision
            )
            moved = False
            if apply and decision.action == "file" and target is not None:
                moved = _move(document.path, target)
                if not moved:
                    decision = _blocked(decision)
            rows.append(
                {
                    "source": str(path),
                    "target": None if target is None else str(target),
                    "moved": moved,
                    **decision.to_dict(),
                }
            )
    rows.sort(key=lambda row: review_sort_key(_decision_from_row(row)))
    return rows


def _client() -> Any:
    import os

    if not os.environ.get("TYPESAFE_API_KEY", "").strip():
        raise RuntimeError(
            "缺少 TYPESAFE_API_KEY。在 https://console.typesafe.ai/settings/keys 创建密钥后执行：\n"
            "  export TYPESAFE_API_KEY='你的密钥'"
        )
    from typesafe_sdk import TypeSafeClient

    return TypeSafeClient(model=MODEL)


def _target_path(
    library: Path,
    source: Path,
    title: str,
    stamp: str,
    decision: FilingDecision,
) -> Path | None:
    if decision.relative_path is None:
        return None
    folder = (library / decision.relative_path).resolve()
    root = library.resolve()
    if folder != root and root not in folder.parents:
        raise ValueError(f"目录越出文库：{decision.relative_path}")
    return folder / filing_filename(source, title, stamp)


def _move(source: Path, target: Path) -> bool:
    if target.exists():
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(target))
    return True


def _blocked(decision: FilingDecision) -> FilingDecision:
    return FilingDecision(
        destination=decision.destination,
        relative_path=decision.relative_path,
        confidence=decision.confidence,
        probabilities=decision.probabilities,
        template_noul=decision.template_noul,
        urgency_score=decision.urgency_score,
        urgency_band=decision.urgency_band,
        open_actions_noul=decision.open_actions_noul,
        action="review",
        reason="目标文件已存在，没有覆盖。",
        model=decision.model,
    )


def _decision_from_row(row: dict[str, Any]) -> FilingDecision:
    return FilingDecision(
        destination=row["destination"],
        relative_path=row["relative_path"],
        confidence=row["confidence"],
        probabilities=row["probabilities"],
        template_noul=row["template_noul"],
        urgency_score=row["urgency_score"],
        urgency_band=row["urgency_band"],
        open_actions_noul=row["open_actions_noul"],
        action=row["action"],
        reason=row["reason"],
        model=row["model"],
    )


def _print_row(row: dict[str, Any]) -> None:
    action = "入库" if row["moved"] else ("建议入库" if row["action"] == "file" else "待人工确认")
    place = row["relative_path"] or "（无）"
    print(f"{row['source']}")
    print(f"  动作    {action}")
    print(f"  目录    {place}")
    print(f"  置信度  {row['confidence']:.2f}")
    runner = _runner_up(row["probabilities"], row["destination"])
    if runner and row["action"] == "review":
        label = destination_path(runner[0]) or runner[0]
        print(f"  次选    {label} {runner[1]:.2f}")
    print(f"  紧急度  {row['urgency_band']} ({row['urgency_score']:.2f})")
    if row["open_actions_noul"] is not None:
        print(f"  待办    {row['open_actions_noul']:.2f}")
    if row["target"]:
        print(f"  路径    {row['target']}")
    print(f"  原因    {row['reason']}")
    print(f"  模型    {row['model']}")
    print()


def _runner_up(probabilities: dict[str, float], winner: str) -> tuple[str, float] | None:
    ordered = sorted(probabilities.items(), key=lambda item: item[1], reverse=True)
    for key, probability in ordered:
        if key != winner:
            return key, probability
    return None
