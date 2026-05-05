"""ChatDev script node entry point for patch validation."""

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from debugger_agents.io_utils import combined_input_text, extract_json_objects, find_project_path, input_texts, print_json
from debugger_agents.validator import validate_patch


def main() -> None:
    combined = combined_input_text()
    consensus = None
    for text in input_texts():
        for obj in extract_json_objects(text):
            if obj.get("type") == "consensus_result" or obj.get("winner"):
                consensus = obj
    winner = (consensus or {}).get("winner") or {}
    diff = winner.get("unified_diff") or winner.get("patch") or ""
    project_path = find_project_path(combined)
    command_match = re.search(r"(?:test_command|TEST_COMMAND)\s*[:=]\s*(.+)", combined)
    test_command = os.getenv("TEST_COMMAND") or (command_match.group(1).strip() if command_match else None)
    if test_command is None:
        for obj in extract_json_objects(combined):
            value = obj.get("test_command")
            if isinstance(value, str) and value.strip():
                test_command = value.strip()
                break
    if not test_command and project_path.is_file() and project_path.suffix == ".py":
        test_command = f"python3 {project_path.name}"

    result = validate_patch(project_path, diff, test_command)
    result["type"] = "validation_result"
    result["winner_id"] = (consensus or {}).get("winner_id")
    result["project_path"] = str(project_path)
    result["consensus"] = consensus
    print_json(result)


if __name__ == "__main__":
    main()
