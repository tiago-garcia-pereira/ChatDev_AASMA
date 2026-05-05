"""Build explicit debugger context from the initial prompt and uploaded files."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from debugger_agents.io_utils import combined_input_text, find_project_path, print_json, uploaded_python_files


def main() -> None:
    text = combined_input_text()
    uploaded = uploaded_python_files()
    payload = {
        "type": "debugger_input_context",
        "original_prompt": text,
        "uploaded_python_files": [],
        "project_path": None,
        "test_command": None,
    }

    project_path = find_project_path(text)
    if uploaded:
        target = uploaded[0]
        content = target.read_text(encoding="utf-8", errors="replace")
        payload["project_path"] = str(target)
        payload["test_command"] = f"python3 {target.name}"
        payload["uploaded_python_files"].append(
            {
                "name": target.name,
                "local_path": str(target),
                "content": content,
            }
        )
    elif project_path.exists():
        payload["project_path"] = str(project_path)
        if project_path.is_file() and project_path.suffix == ".py":
            payload["test_command"] = f"python3 {project_path.name}"
            payload["uploaded_python_files"].append(
                {
                    "name": project_path.name,
                    "local_path": str(project_path),
                    "content": project_path.read_text(encoding="utf-8", errors="replace"),
                }
            )

    print_json(payload)


if __name__ == "__main__":
    main()
