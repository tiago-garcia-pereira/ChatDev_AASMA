"""Apply the validated winning patch to the original project path."""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from debugger_agents.io_utils import extract_json_objects, input_texts, print_json


def main() -> None:
    validation = None
    for text in input_texts():
        for obj in extract_json_objects(text):
            if obj.get("type") == "validation_result":
                validation = obj

    if not validation:
        print_json({"type": "apply_patch_result", "applied": False, "reason": "no validation result"})
        return

    if not validation.get("passed"):
        print_json({
            "type": "apply_patch_result",
            "applied": False,
            "reason": "validation did not pass",
            "validation": validation,
        })
        return

    consensus = validation.get("consensus") or {}
    winner = consensus.get("winner") or {}
    diff = winner.get("unified_diff") or winner.get("patch") or ""
    project_path = Path(str(validation.get("project_path") or "")).expanduser().resolve()
    cwd = project_path.parent if project_path.is_file() else project_path

    completed = subprocess.run(
        ["git", "apply", "--whitespace=nowarn", "-"],
        cwd=str(cwd),
        input=diff,
        capture_output=True,
        text=True,
        timeout=30,
    )
    print_json({
        "type": "apply_patch_result",
        "applied": completed.returncode == 0,
        "project_path": str(project_path),
        "cwd": str(cwd),
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "winner_id": validation.get("winner_id"),
    })


if __name__ == "__main__":
    main()
