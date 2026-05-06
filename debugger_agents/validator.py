"""Patch validation helpers."""

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def validate_patch(project_path: str | Path, unified_diff: str, test_command: str | None = None) -> dict[str, Any]:
    source = Path(project_path).resolve()
    if not source.exists():
        return {"passed": False, "error": f"project path does not exist: {source}"}

    with tempfile.TemporaryDirectory(prefix="chatdev_debugger_") as tmp:
        tmp_path = Path(tmp) / "project"
        if source.is_dir():
            ignore = shutil.ignore_patterns(".git", ".venv", "__pycache__", ".pytest_cache", "node_modules")
            shutil.copytree(source, tmp_path, ignore=ignore)
        else:
            tmp_path.mkdir()
            shutil.copy2(source, tmp_path / source.name)

        patch_result = subprocess.run(
            ["git", "apply", "--whitespace=nowarn", "-"],
            cwd=str(tmp_path),
            input=unified_diff,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if patch_result.returncode != 0:
            return {
                "passed": False,
                "stage": "apply_patch",
                "exit_code": patch_result.returncode,
                "stdout": patch_result.stdout,
                "stderr": patch_result.stderr,
                "sandbox": str(tmp_path),
            }

        command = test_command or (f"python3 {source.name}" if source.is_file() and source.suffix == ".py" else "python -m compileall -q .")
        test_result = subprocess.run(
            command,
            cwd=str(tmp_path),
            shell=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return {
            "passed": test_result.returncode == 0,
            "stage": "test",
            "test_command": command,
            "exit_code": test_result.returncode,
            "stdout": test_result.stdout[-6000:],
            "stderr": test_result.stderr[-6000:],
        }


def check_patch_applicability(project_path: str | Path, unified_diff: str) -> dict[str, Any]:
    source = Path(project_path).resolve()
    if not source.exists():
        return {"valid": False, "reason": f"project path does not exist: {source}"}
    if "diff --git " not in unified_diff or "--- " not in unified_diff or "+++ " not in unified_diff:
        return {"valid": False, "reason": "patch is not a complete git-style unified diff"}

    with tempfile.TemporaryDirectory(prefix="chatdev_patch_check_") as tmp:
        tmp_path = Path(tmp) / "project"
        if source.is_dir():
            ignore = shutil.ignore_patterns(".git", ".venv", "__pycache__", ".pytest_cache", "node_modules")
            shutil.copytree(source, tmp_path, ignore=ignore)
            target_name = None
        else:
            tmp_path.mkdir()
            shutil.copy2(source, tmp_path / source.name)
            target_name = source.name

        if target_name and f" b/{target_name}" not in unified_diff and f"+++ b/{target_name}" not in unified_diff:
            return {"valid": False, "reason": f"patch does not target {target_name}"}

        patch_result = subprocess.run(
            ["git", "apply", "--check", "--whitespace=nowarn", "-"],
            cwd=str(tmp_path),
            input=unified_diff,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return {
            "valid": patch_result.returncode == 0,
            "reason": "" if patch_result.returncode == 0 else patch_result.stderr.strip(),
        }
