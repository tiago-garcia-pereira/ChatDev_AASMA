"""Command line runner for the autonomous code debugger workflow."""

from __future__ import annotations

import argparse
import contextlib
import os
import sys
import threading
import time
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Sequence

warnings.filterwarnings(
    "ignore",
    message=r"urllib3 .* doesn't match a supported version!",
)

from check.check import load_config
from entity.graph_config import GraphConfig
from entity.messages import Message
from runtime.bootstrap.schema import ensure_schema_registry_populated
from utils.human_prompt import PromptResult
from workflow.graph import GraphExecutor
from workflow.graph_context import GraphContext


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORKFLOW = REPO_ROOT / "yaml_instance" / "autonomous_code_debugger.yaml"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "WareHouse"


@dataclass
class FixedPromptHook:
    """Small workspace hook used only to provide a prompt channel."""

    channel: Any

    def get_prompt_channel(self) -> Any:
        return self.channel


@dataclass
class VisibleCliPromptChannel:
    """Prompt channel that remains visible while workflow stdout is muted."""

    output: Any = sys.__stdout__
    input_stream: Any = sys.__stdin__
    loading: "LoadingIndicator | None" = None

    def request(
        self,
        *,
        node_id: str,
        task: str,
        inputs: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PromptResult:
        with _pause_loading(self.loading):
            header = ["===== HUMAN INPUT REQUIRED ====="]
            if inputs:
                header.append("=== Node inputs ===")
                header.append(inputs)
            header.append(f"=== Task for human ({node_id}) ===")
            header.append(task)
            header.append("=== Your response: ===")
            self.output.write("\n".join(header) + "\n")
            self.output.flush()
            response = self.input_stream.readline().rstrip("\n")
        return PromptResult(text=response)


class LoadingIndicator:
    """Small terminal spinner for long muted workflow runs."""

    def __init__(self, message: str = "Running autonomous debugger") -> None:
        self.message = message
        self.output = sys.__stdout__
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._started_at = 0.0
        self._enabled = hasattr(self.output, "isatty") and self.output.isatty()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        if not self._enabled:
            self.output.write(f"{self.message}...\n")
            self.output.flush()
            return
        self._stop.clear()
        self._started_at = time.monotonic()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if not self._enabled:
            return
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1)
        self._thread = None
        self._clear_line()

    @contextlib.contextmanager
    def running(self) -> Iterator[None]:
        self.start()
        try:
            yield
        finally:
            self.stop()

    def _spin(self) -> None:
        frames = "-\\|/"
        index = 0
        while not self._stop.is_set():
            elapsed = int(time.monotonic() - self._started_at)
            self.output.write(f"\r{frames[index % len(frames)]} {self.message} ({elapsed}s)")
            self.output.flush()
            index += 1
            time.sleep(0.12)

    def _clear_line(self) -> None:
        self.output.write("\r" + " " * (len(self.message) + 16) + "\r")
        self.output.flush()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the autonomous code debugger workflow from the command line.",
    )
    parser.add_argument(
        "project_path",
        type=Path,
        help="Target project directory or file to debug.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        final_text, output_dir = run_debugger(args)
    except Exception as exc:
        print(f"debugger CLI failed: {exc}", file=sys.stderr)
        return 1

    if final_text:
        print(final_text)
    print(f"\nArtifacts: {output_dir}")
    return 0


def run_debugger(args: argparse.Namespace) -> tuple[str, Path]:
    ensure_schema_registry_populated()

    workflow_path = DEFAULT_WORKFLOW.resolve()
    if not workflow_path.exists():
        raise FileNotFoundError(f"workflow YAML not found: {workflow_path}")

    project_path = args.project_path.expanduser().resolve()
    if not project_path.exists():
        raise FileNotFoundError(f"project path not found: {project_path}")

    with _silence_stdout():
        design = load_config(workflow_path)

    graph_config = GraphConfig.from_definition(
        design.graph,
        name="autonomous_debugger_cli",
        output_root=DEFAULT_OUTPUT_ROOT,
        source_path=str(workflow_path),
        vars=design.vars,
    )

    graph_context = GraphContext(config=graph_config)
    task_input = _build_prompt(project_path)

    loading = LoadingIndicator()
    channel: Any = VisibleCliPromptChannel(loading=loading)
    workspace_hook_factory = lambda _runtime: FixedPromptHook(channel)

    executor = GraphExecutor(
        graph_context,
        workspace_hook_factory=workspace_hook_factory,
    )
    executor.logger.log_to_console = False
    with loading.running():
        with _silence_stdout():
            graph_context.record(executor.run(task_input))

    final_message = executor.get_final_output_message()
    final_text = final_message.text_content() if isinstance(final_message, Message) else ""
    return final_text, graph_context.directory


def _build_prompt(project_path: Path) -> str:
    return f"PROJECT_PATH: {project_path}"


@contextlib.contextmanager
def _silence_stdout():
    with open(os.devnull, "w", encoding="utf-8") as devnull:
        with contextlib.redirect_stdout(devnull):
            yield


@contextlib.contextmanager
def _pause_loading(loading: LoadingIndicator | None) -> Iterator[None]:
    if loading is None:
        yield
        return
    loading.stop()
    try:
        yield
    finally:
        loading.start()


if __name__ == "__main__":
    raise SystemExit(main())
