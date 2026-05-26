# Debugger Agents Documentation

## Overview
The `debugger_agents` directory contains a suite of deterministic scripts and helpers designed to support an **Autonomous Code Debugger** workflow. These agents work together to ingest bug reports, analyze source code, reproduce failures, and reach a consensus on the best fix among multiple proposed patches.

## Goal
The primary goal of these agents is to automate the "Diagnose -> Reproduce -> Fix -> Validate" cycle. By providing standardized I/O handling and specialized analysis tools, they enable a multi-agent system to handle complex software debugging tasks with minimal human intervention.

---

## Script & Module Breakdown

### 🛠 Core Logic & Utilities

#### `consensus.py`
Implements consensus algorithms to evaluate multiple patch proposals.
*   **Borda Count:** A positional voting system used to rank patches based on "Fixer" agent votes.
*   **Winner Selection:** Logic to determine the winning patch by combining rankings and agent confidence scores.

#### `io_utils.py`
Provides foundational I/O operations for ChatDev script nodes.
*   **Input Parsing:** Extracts messages and JSON objects from the `CHATDEV_NODE_INPUTS` environment variable.
*   **Project Discovery:** Heuristically finds the target project path from prompts, file paths, or environment variables.
*   **File Handling:** Identifies and resolves paths for uploaded Python files.

#### `schemas.py`
Defines the data structures (Dataclasses) used throughout the debugger workflow.
*   **`PatchProposal`**: Stores fixer IDs, strategy, diagnosis, and the actual solution code/diff.
*   **`FixerVote`**: Represents an agent's ranking and rationale for different proposals.

#### `static_analyzer.py`
The engine for code health checks.
*   Performs AST (Abstract Syntax Tree) parsing and compilation checks on up to 200 Python files.
* It checks Python files for syntax errors, compilation errors, and optionally runs external static analysis tools like Ruff and MyPy.
*   The module is designed to analyze Python code for errors without executing it, helping developers catch issues early in the development process.
*   Integrates with external tools like `ruff` and `mypy` if available in the environment.

---

### 🚀 Execution Entry Points (Script Nodes)

#### `run_input_context.py`
**Purpose:** Prepares the initial state.
*   Extracts the original user prompt and any uploaded files.
*   Builds a standardized `debugger_input_context` JSON object containing the project path and basic test commands.

#### `run_static_analyzer.py`
**Purpose:** Performs deep-code analysis.
*   Invokes the `static_analyzer.py` logic.
*   Provides agents with a detailed report of syntax errors, type mismatches, and linting violations.

#### `run_auto_reproducer.py`
**Purpose:** Confirms the bug exists.
*   Infers or extracts a test command (e.g., `pytest`, `python3 main.py`).
*   Executes the command in a subprocess and captures `stdout`/`stderr` to provide a "ground truth" failure for the agents.

#### `run_consensus.py`
**Purpose:** Decides on the final fix.
*   Gathers all `PatchProposal` objects and `FixerVote` objects from the conversation history.
*   Uses `consensus.py` to calculate the winner and outputs a final `consensus_result`.

---

## Typical Workflow Flow
1.  **`run_input_context`**: Bootstraps the environment and identifies the target code.
2.  **`run_static_analyzer`**: Identifies obvious syntax or type errors.
3.  **`run_auto_reproducer`**: Validates the reported bug by running tests.
4.  *Fixer Agents (LLMs)*: Propose patches based on the analysis and reproduction output.
5.  *Reviewer Agents (LLMs)*: Vote on the proposed patches.
6.  **`run_consensus`**: Finalizes the best solution to be applied to the codebase.
