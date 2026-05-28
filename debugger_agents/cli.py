"""Minimal command-line interface for the autonomous code debugger workflow.

The CLI intentionally exposes a single user-facing argument, the target project
path. All diagnostic context collection remains delegated to the workflow, so
the command-line contract mirrors the ChatDev API contract as closely as
possible.
"""

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
    """Workspace hook adapter that supplies the CLI prompt channel to the runtime.

    The workflow executor discovers human-interaction channels through a
    workspace hook abstraction. This adapter implements only the method required
    for that discovery path, allowing the CLI to provide terminal-based human
    input without modifying the shared workflow runtime.

    Attributes:
        channel: Prompt channel instance returned to the runtime when a human
            node requests user input.
    """

    channel: Any

    def get_prompt_channel(self) -> Any:
        """Return the prompt channel expected by the workflow runtime.

        Returns:
            The prompt channel configured by the CLI runner.
        """
        return self.channel


@dataclass
class VisibleCliPromptChannel:
    """Prompt channel that remains visible while workflow output is suppressed.

    The workflow is executed with standard output redirected to avoid exposing
    intermediate agent JSON. Human-in-the-loop prompts must bypass that
    redirection, hence the direct use of the original process streams.
    """

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
        """Collect a human response from the terminal.

        Args:
            node_id: Identifier of the human node requesting input.
            task: Human-readable instruction associated with the node.
            inputs: Optional textual preview of the messages that reached the
                human node.
            metadata: Optional runtime metadata. It is accepted for interface
                compatibility and is not required by this implementation.

        Returns:
            A PromptResult containing the line entered by the operator.
        """
        # The loading indicator is paused to avoid corrupting the terminal input
        # line while the human selector is awaiting a response.
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
    """Terminal progress indicator for long-running, muted workflow execution.

    The debugger CLI suppresses ordinary workflow output to keep the interface
    readable. This indicator provides minimal liveness feedback while preserving
    silence for intermediate JSON payloads and agent logs.
    """

    def __init__(self, message: str = "Running autonomous debugger") -> None:
        """Initialise the loading indicator.

        Args:
            message: Status text displayed next to the spinner or static status
                line.
        """
        self.message = message
        self.output = sys.__stdout__
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._started_at = 0.0
        self._enabled = hasattr(self.output, "isatty") and self.output.isatty()

    def start(self) -> None:
        """Start the spinner, or emit a static status line on non-interactive output.

        Interactive terminals receive an animated single-line spinner. Captured
        or redirected output receives a single status line to avoid background
        redraw characters in logs.
        """
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
        """Stop the spinner and clear the current terminal line when applicable.

        The method is idempotent, so it can be safely called before terminal
        prompts, after workflow completion, or during exception unwinding.
        """
        if not self._enabled:
            return
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1)
        self._thread = None
        self._clear_line()

    @contextlib.contextmanager
    def running(self) -> Iterator[None]:
        """Run a code block while the loading indicator is active.

        Yields:
            Control to the caller while the loading indicator remains active.
        """
        self.start()
        try:
            yield
        finally:
            self.stop()

    def _spin(self) -> None:
        """Continuously redraw the status line until a stop signal is received.

        This method executes in a daemon thread and communicates with the main
        thread through a threading.Event.
        """
        frames = "-\\|/"
        index = 0
        while not self._stop.is_set():
            elapsed = int(time.monotonic() - self._started_at)
            self.output.write(f"\r{frames[index % len(frames)]} {self.message} ({elapsed}s)")
            self.output.flush()
            index += 1
            time.sleep(0.12)

    def _clear_line(self) -> None:
        """Erase the transient spinner line from the terminal."""
        self.output.write("\r" + " " * (len(self.message) + 16) + "\r")
        self.output.flush()


def build_parser() -> argparse.ArgumentParser:
    """Build the deliberately minimal CLI argument parser.

    Returns:
        An ArgumentParser accepting only the target project path. Additional
        diagnostic flags are intentionally excluded because context discovery is
        delegated to the workflow itself.
    """
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
    """Parse command-line arguments and execute the debugger workflow.

    Args:
        argv: Optional argument vector used by tests or embedded callers. When
            omitted, argparse reads arguments from sys.argv.

    Returns:
        Process-style exit code: 0 on success and 1 on runtime failure.
    """
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
    """Execute the configured autonomous debugger workflow for one project path.

    Args:
        args: Parsed CLI namespace. Only args.project_path is part of the public
            command-line contract.

    Returns:
        A tuple containing the final report text and the directory where
        workflow artifacts were persisted.

    Raises:
        FileNotFoundError: If the fixed workflow YAML or target project path is
            missing.
    """
    ensure_schema_registry_populated()

    # The workflow definition is fixed by design. Users provide only the target
    # path; the workflow remains responsible for reproducing and contextualising
    # the failure.
    workflow_path = DEFAULT_WORKFLOW.resolve()
    if not workflow_path.exists():
        raise FileNotFoundError(f"workflow YAML not found: {workflow_path}")

    project_path = args.project_path.expanduser().resolve()
    if not project_path.exists():
        raise FileNotFoundError(f"project path not found: {project_path}")

    # Config validation emits informational text that is useful for development
    # but noisy for the debugger CLI, so it is hidden from the end user.
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

    # The custom prompt channel preserves human interaction while the rest of the
    # workflow output remains suppressed.
    loading = LoadingIndicator()
    channel: Any = VisibleCliPromptChannel(loading=loading)
    workspace_hook_factory = lambda _runtime: FixedPromptHook(channel)

    executor = GraphExecutor(
        graph_context,
        workspace_hook_factory=workspace_hook_factory,
    )
    executor.logger.log_to_console = False
    _print_agent_starts_in_cli(executor, loading)
    # Intermediate node outputs, including agent JSON proposals and votes, remain
    # available in the artifact directory but are not printed to the terminal.
    with loading.running():
        with _silence_stdout():
            graph_context.record(executor.run(task_input))

    final_message = executor.get_final_output_message()
    final_text = final_message.text_content() if isinstance(final_message, Message) else ""
    return final_text, graph_context.directory


def _build_prompt(project_path: Path) -> str:
    """Construct the sole initial prompt field consumed by the workflow.

    Args:
        project_path: Resolved target project path supplied by the CLI user.

    Returns:
        The initial workflow prompt containing only PROJECT_PATH.
    """
    return f"PROJECT_PATH: {project_path}"


def _print_agent_starts_in_cli(executor: GraphExecutor, loading: LoadingIndicator) -> None:
    """Print agent start notifications for CLI runs without affecting other clients.

    This function wraps the executor instance created by the CLI rather than
    changing GraphExecutor globally. Consequently, ChatDev API and web-client
    executions retain their existing output behaviour.

    Args:
        executor: Workflow executor instance owned by this CLI invocation.
        loading: Loading indicator that must be temporarily paused before
            writing terminal status lines.
    """
    original_record_node_start = executor.log_manager.record_node_start

    def record_node_start_with_cli_status(
        node_id: str,
        inputs: list[dict[str, str]],
        node_type: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Proxy node-start logging while adding CLI-only agent status lines."""
        if node_type == "agent":
            _write_cli_status(f"Starting agent: {node_id}", loading)
        original_record_node_start(node_id, inputs, node_type, details)

    executor.log_manager.record_node_start = record_node_start_with_cli_status


def _write_cli_status(message: str, loading: LoadingIndicator) -> None:
    """Write a CLI-only status line without disturbing the spinner state.

    Args:
        message: Status message to display to the CLI user.
        loading: Active loading indicator that may need to be paused before
            writing to the terminal.
    """
    if loading._enabled:
        loading.stop()
        sys.__stdout__.write(f"{message}\n")
        sys.__stdout__.flush()
        loading.start()
        return
    sys.__stdout__.write(f"{message}\n")
    sys.__stdout__.flush()


@contextlib.contextmanager
def _silence_stdout():
    """Temporarily redirect standard output to the operating system null device.

    Yields:
        Control to the caller while ordinary stdout is suppressed. Direct writes
        to sys.__stdout__ remain visible for intentional CLI status output.
    """
    with open(os.devnull, "w", encoding="utf-8") as devnull:
        with contextlib.redirect_stdout(devnull):
            yield


@contextlib.contextmanager
def _pause_loading(loading: LoadingIndicator | None) -> Iterator[None]:
    """Suspend the loading indicator while direct terminal interaction occurs.

    Args:
        loading: Optional loading indicator to pause. Passing None makes the
            context manager a no-op.

    Yields:
        Control to the caller while the spinner is stopped.
    """
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
