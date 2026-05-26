"""CLI wrapper for the autonomous multi-agent debugger workflow."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Sequence

DEFAULT_WORKFLOW = Path("yaml_instance/autonomous_code_debugger.yaml")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the autonomous code debugger workflow from the command line.",
    )
    parser.add_argument(
        "--file",
        type=Path,
        required=True,
        help="Python file or project path to debug.",
    )
    parser.add_argument(
        "--workflow",
        type=Path,
        default=DEFAULT_WORKFLOW,
        help=f"Workflow YAML to execute (default: {DEFAULT_WORKFLOW}).",
    )
    parser.add_argument(
        "--name",
        type=str,
        default=None,
        help="Optional session name. Defaults to the target file stem.",
    )
    parser.add_argument(
        "--test-command",
        type=str,
        default=None,
        help="Optional command used by the auto reproducer instead of inferring one.",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default="",
        help="Optional extra bug report, traceback, or debugging context.",
    )
    parser.add_argument(
        "--attachment",
        action="append",
        default=[],
        help="Extra file to attach to the initial debugger prompt (repeatable).",
    )
    return parser


def build_debug_prompt(target_path: Path, extra_prompt: str, test_command: str | None) -> str:
    lines = [f"PROJECT_PATH: {target_path}"]
    if test_command:
        lines.append(f"TEST_COMMAND: {test_command}")
    if extra_prompt.strip():
        lines.append("")
        lines.append(extra_prompt.strip())
    return "\n".join(lines)


def normalize_attachments(paths: Sequence[str | Path]) -> list[Path]:
    return [Path(path).expanduser().resolve() for path in paths]


def message_text(message: Any) -> str:
    if message is None:
        return "Workflow finished with no final message."
    return message.text_content().strip() or "Workflow finished with an empty final message."


def main() -> None:
    args = build_parser().parse_args()
    try:
        from runtime.sdk import run_workflow
    except ModuleNotFoundError as exc:
        raise SystemExit(
            f"Missing dependency while loading the workflow runtime: {exc.name}. "
            "Run this command with the project environment that has the debugger dependencies installed."
        ) from exc

    target_path = args.file.expanduser().resolve()
    if not target_path.exists():
        raise SystemExit(f"Target path does not exist: {target_path}")

    workflow_path = args.workflow.expanduser()
    session_name = args.name or target_path.stem
    attachments = normalize_attachments(args.attachment)
    missing_attachments = [path for path in attachments if not path.exists()]
    if missing_attachments:
        missing = ", ".join(str(path) for path in missing_attachments)
        raise SystemExit(f"Attachment path does not exist: {missing}")

    prompt = build_debug_prompt(target_path, args.prompt, args.test_command)
    result = run_workflow(
        workflow_path,
        task_prompt=prompt,
        attachments=attachments,
        session_name=session_name,
    )

    print(message_text(result.final_message))
    print(f"\nOutput directory: {result.meta_info.output_dir}")


if __name__ == "__main__":
    main()
