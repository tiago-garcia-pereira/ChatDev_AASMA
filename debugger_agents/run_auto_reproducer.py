"""Run a likely failing command from PROJECT_PATH/PATH_PROJECT context."""

import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from debugger_agents.io_utils import combined_input_text, extract_json_objects, find_project_path, print_json


def main() -> None:
    text = combined_input_text()
    project_path = find_project_path(text)
    command_match = re.search(r"(?:test_command|TEST_COMMAND)\s*[:=]\s*(.+)", text)
    command = os.getenv("TEST_COMMAND") or (command_match.group(1).strip() if command_match else None)
    if command is None:
        for obj in extract_json_objects(text):
            value = obj.get("test_command")
            if isinstance(value, str) and value.strip():
                command = value.strip()
                break

    if command is None:
        command = infer_command(project_path)

    cwd = project_path.parent if project_path.is_file() else project_path
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        result = {
            "type": "auto_reproduction",
            "project_path": str(project_path),
            "test_command": command,
            "cwd": str(cwd),
            "exit_code": completed.returncode,
            "passed": completed.returncode == 0,
            "stdout": completed.stdout[-8000:],
            "stderr": completed.stderr[-8000:],
        }
    except subprocess.TimeoutExpired as exc:
        result = {
            "type": "auto_reproduction",
            "project_path": str(project_path),
            "test_command": command,
            "cwd": str(cwd),
            "passed": False,
            "error": "command timed out",
            "stdout": (exc.stdout or "")[-8000:] if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "")[-8000:] if isinstance(exc.stderr, str) else "",
        }

    print_json(result)


def infer_command(project_path: Path) -> str:
    if project_path.is_file() and project_path.suffix == ".py":
        return f"python3 {project_path.name}"

    if project_path.is_dir():
        if (project_path / "pytest.ini").exists() or (project_path / "tests").exists():
            return "python3 -m pytest"
        main_py = project_path / "main.py"
        if main_py.exists():
            return "python3 main.py"

    return "python3 -m compileall -q ."


if __name__ == "__main__":
    main()
