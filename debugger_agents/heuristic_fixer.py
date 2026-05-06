"""Small deterministic fallback fixes for simple Python crashes."""

import difflib
import re
from pathlib import Path
from typing import Any


def build_heuristic_proposal(project_path: str | Path, context_text: str) -> dict[str, Any] | None:
    path = Path(project_path).resolve()
    if not path.is_file() or path.suffix != ".py" or not path.exists():
        return None
    if "IndexError" not in context_text or "list index out of range" not in context_text:
        return None

    original_text = path.read_text(encoding="utf-8", errors="replace")
    lines = original_text.splitlines()
    for line_index, line in enumerate(lines):
        subscript_match = re.search(r"\b([A-Za-z_]\w*)\s*\[\s*(\d+)\s*\]", line)
        if not subscript_match:
            continue
        variable = subscript_match.group(1)
        requested_index = int(subscript_match.group(2))
        length = _find_literal_list_length(lines, variable)
        if length is None or not length or requested_index < length:
            continue

        fixed_index = length - 1
        new_lines = list(lines)
        start, end = subscript_match.span(2)
        new_lines[line_index] = line[:start] + str(fixed_index) + line[end:]
        new_text = "\n".join(new_lines)
        if original_text.endswith("\n"):
            new_text += "\n"
        diff = _git_style_diff(path.name, original_text, new_text)
        return {
            "fixer_id": "deterministic_fallback",
            "strategy": "Deterministic fallback for literal list IndexError.",
            "diagnosis": (
                f"{variable} has {length} elements, but the code accesses index "
                f"{requested_index}; changed it to {fixed_index}."
            ),
            "files_changed": [str(path)],
            "unified_diff": diff,
            "confidence": 0.99,
        }
    return None


def _find_literal_list_length(lines: list[str], variable: str) -> int | None:
    pattern = re.compile(rf"^\s*{re.escape(variable)}\s*=\s*\[(.*)\]\s*$")
    for line in lines:
        match = pattern.match(line)
        if not match:
            continue
        body = match.group(1).strip()
        if not body:
            return 0
        return len([item for item in body.split(",") if item.strip()])
    return None


def _git_style_diff(filename: str, old_text: str, new_text: str) -> str:
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()
    diff_lines = list(difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        lineterm="",
    ))
    if old_text and not old_text.endswith("\n"):
        diff_lines = _insert_no_newline_marker(diff_lines, "-")
    if new_text and not new_text.endswith("\n"):
        diff_lines = _insert_no_newline_marker(diff_lines, "+")
    return "diff --git a/{0} b/{0}\n".format(filename) + "\n".join(diff_lines) + "\n"


def _insert_no_newline_marker(diff_lines: list[str], prefix: str) -> list[str]:
    for index in range(len(diff_lines) - 1, -1, -1):
        line = diff_lines[index]
        if line.startswith(prefix) and not line.startswith(prefix * 3):
            return diff_lines[: index + 1] + [r"\ No newline at end of file"] + diff_lines[index + 1 :]
    return diff_lines
