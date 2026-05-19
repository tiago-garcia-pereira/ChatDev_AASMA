"""Apply the consensus winner solution files to the target project without using LLMs."""

import os
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from debugger_agents.io_utils import combined_input_text, extract_json_objects, find_project_path, print_json


def main() -> None:
    text = combined_input_text()
    project_path = find_project_path(text)
    root = project_path if project_path.is_dir() else project_path.parent

    winner = _find_winner(text)
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
    print_json(payload)


def _find_winner(text: str) -> dict[str, Any] | None:
    for obj in extract_json_objects(text):
        if obj.get("type") == "consensus_result" and isinstance(obj.get("winner"), dict):
            return obj["winner"]
        if isinstance(obj.get("winner"), dict) and "scores" in obj:
            return obj["winner"]
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