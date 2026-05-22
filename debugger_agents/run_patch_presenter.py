"""Formats the three patch proposals for the human to review and select."""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


_FIXER_LABELS = {
    "conservative": ("1", "Conservative Fix"),
    "defensive":    ("2", "Defensive Fix"),
    "root_cause":   ("3", "Root Cause Fix"),
}

_ORDER = ["conservative", "defensive", "root_cause"]


def main() -> None:
    consensus_path = Path(tempfile.gettempdir()) / "chatdev_consensus_result.json"
    if not consensus_path.exists():
        print("ERROR: consensus_result not found. Cannot present patch options.")
        sys.exit(1)

    try:
        consensus = json.loads(consensus_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"ERROR: could not read consensus_result: {e}")
        sys.exit(1)

    proposals_by_id = {p["fixer_id"]: p for p in consensus.get("proposals", [])}
    winner_id = consensus.get("winner_id", "")

    lines = []
    lines.append("══════════════════════════════════════════")
    lines.append("PATCH OPTIONS — please type 1, 2, or 3")
    lines.append("══════════════════════════════════════════")
    lines.append("")

    for fixer_id in _ORDER:
        number, label = _FIXER_LABELS[fixer_id]
        proposal = proposals_by_id.get(fixer_id)
        if not proposal:
            continue

        lines.append(f"[{number}] {label}  (fixer: {fixer_id})")
        lines.append(f"Strategy   : {proposal.get('strategy', 'n/a')}")
        lines.append(f"Diagnosis  : {proposal.get('diagnosis', 'n/a')}")
        lines.append(f"Confidence : {proposal.get('confidence', 'n/a')}")
        lines.append("Solution:")

        solution_files = proposal.get("solution_files") or []
        for sf in solution_files:
            code = sf.get("code", "")
            for code_line in code.splitlines():
                lines.append(f"  {code_line}")

        lines.append("")
        lines.append("──────────────────────────────────────────")
        lines.append("")

    # Map winner_id to number for the recommendation
    winner_number = _FIXER_LABELS.get(winner_id, ("?", ""))[0]
    lines.append(f"Borda consensus recommends: [{winner_number}] {winner_id}")
    lines.append("Type 1, 2, or 3 to apply that patch (or REJECT to skip):")

    print("\n".join(lines))


if __name__ == "__main__":
    main()