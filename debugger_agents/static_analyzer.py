"""Static analysis helpers for Python bug-fixing workflows."""

import ast
import py_compile
import subprocess
from pathlib import Path
from typing import Any


def analyze_project(project_path: str | Path) -> dict[str, Any]:
    root = Path(project_path).resolve()
    files = sorted(root.rglob("*.py")) if root.is_dir() else [root]
    py_files = [path for path in files if path.exists() and ".venv" not in path.parts and "__pycache__" not in path.parts]
    ast_errors = []
    compile_errors = []

    for path in py_files[:200]:
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except Exception as exc:
            ast_errors.append({"file": str(path), "error": str(exc)})
        try:
            py_compile.compile(str(path), doraise=True)
        except Exception as exc:
            compile_errors.append({"file": str(path), "error": str(exc)})

    return {
        "project_path": str(root),
        "python_files_checked": len(py_files[:200]),
        "ast_errors": ast_errors,
        "compile_errors": compile_errors,
        "ruff": _optional_tool(root, ["ruff", "check", str(root)]),
        "mypy": _optional_tool(root, ["mypy", str(root)]),
    }


def _optional_tool(root: Path, cmd: list[str]) -> dict[str, Any]:
    try:
        completed = subprocess.run(cmd, cwd=str(root if root.is_dir() else root.parent), capture_output=True, text=True, timeout=30)
    except FileNotFoundError:
        return {"available": False, "output": "not installed"}
    except subprocess.TimeoutExpired:
        return {"available": True, "output": "timed out"}
    return {
        "available": True,
        "exit_code": completed.returncode,
        "output": (completed.stdout + completed.stderr)[-6000:],
    }

