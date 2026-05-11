"""ChatDev script node entry point for static analysis."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from debugger_agents.io_utils import combined_input_text, find_project_path, print_json
from debugger_agents.static_analyzer import analyze_project


def main() -> None:
    text = combined_input_text()
    project_path = find_project_path(text)
    print_json({
        "type": "static_analysis",
        "analysis": analyze_project(project_path),
        "instruction": (
            "Fixers must return JSON with fixer_id, strategy, diagnosis, files_changed, "
            "solution_files (list of {path, code}) or solution_code, and confidence. "
            "Do not use git-style diffs."
        ),
    })


if __name__ == "__main__":
    main()

