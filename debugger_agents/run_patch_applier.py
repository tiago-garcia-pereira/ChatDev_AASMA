"""Apply the user-selected solution files to the target project without using LLMs."""

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from debugger_agents.io_utils import combined_input_text, find_project_path, input_texts, print_json

_CHOICE_TO_FIXER = {
    "1": "conservative",
    "2": "defensive",
    "3": "root_cause",
}


def main() -> None:
    text = combined_input_text()
    project_path = find_project_path(text)
    root = project_path if project_path.is_dir() else project_path.parent

    winner = _find_winner()
    payload: dict[str, Any] = {
        "type": "patch_applier_result",
        "project_path": str(project_path),
        "applied_files": [],
        "errors": [],
    }

    if winner is None:
        payload["errors"].append("winner not found in workflow inputs")
        print_json(payload)
        return

    solution_files = winner.get("solution_files")
    if not isinstance(solution_files, list) or not solution_files:
        payload["errors"].append("winner.solution_files is missing or empty")
        print_json(payload)
        return

    applied: list[dict[str, Any]] = []
    for item in solution_files:
        if not isinstance(item, dict):
            continue
        rel_path = str(item.get("path") or "").strip()
        code = str(item.get("code") or "")
        if not rel_path or not code:
            continue

        target = _resolve_target(root, rel_path)
        if target is None:
            payload["errors"].append(f"refusing to write outside project root: {rel_path}")
            print_json(payload)
            return

        _atomic_write_text(target, code)
        applied.append({"path": str(target)})

    payload["applied_files"] = applied
    payload["updated_count"] = len(applied)
    payload["applied_fixer_id"] = winner.get("fixer_id")
    print_json(payload)


def _find_winner() -> dict[str, Any] | None:
    # Read user choice from input_texts() which correctly parses
    # content blocks like [{"type": "text", "text": "2"}]
    user_choice = None
    for text in input_texts():
        for line in reversed(text.splitlines()):
            stripped = line.strip()
            if stripped in _CHOICE_TO_FIXER:
                user_choice = stripped
                break
        if user_choice:
            break

    chosen_fixer_id = _CHOICE_TO_FIXER.get(user_choice) if user_choice else None

    # Load consensus_result saved by run_consensus.py
    consensus_path = Path(tempfile.gettempdir()) / "chatdev_consensus_result.json"
    if not consensus_path.exists():
        return None

    try:
        consensus = json.loads(consensus_path.read_text(encoding="utf-8"))
    except Exception:
        return None

    # Find and return the proposal the user chose
    if chosen_fixer_id and isinstance(consensus.get("proposals"), list):
        for proposal in consensus["proposals"]:
            if proposal.get("fixer_id") == chosen_fixer_id:
                return proposal

    return None


def _resolve_target(root: Path, rel_path: str) -> Path | None:
    candidate = Path(rel_path).expanduser()
    if not candidate.is_absolute():
        candidate = (root / candidate).resolve()
    else:
        candidate = candidate.resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            delete=False,
            dir=str(path.parent),
            prefix=f".{path.name}.",
            suffix=".patch-applier.tmp",
        ) as handle:
            handle.write(content)
            tmp_path = Path(handle.name)
        os.replace(tmp_path, path)
    finally:
        if tmp_path is not None and tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass


if __name__ == "__main__":
    main()