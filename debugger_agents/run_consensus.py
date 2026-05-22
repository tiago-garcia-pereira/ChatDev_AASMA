"""ChatDev script node entry point for consensus selection."""

import sys
import json
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from debugger_agents.consensus import select_winner
from debugger_agents.io_utils import extract_json_objects, input_texts, print_json
from debugger_agents.schemas import FixerVote, PatchProposal


def _is_proposal(obj: dict) -> bool:
    return bool(obj.get("fixer_id") and (obj.get("solution_code") or obj.get("solution_files") or obj.get("unified_diff") or obj.get("patch")))


def _is_vote(obj: dict) -> bool:
    return bool(obj.get("voter_id") and (obj.get("ranking") or obj.get("vote") or obj.get("selected")))


def main() -> None:
    proposals_by_id: dict[str, PatchProposal] = {}
    votes_by_id: dict[str, FixerVote] = {}
    project_path: str | None = None
    test_command: str | None = None
    for text in input_texts():
        for obj in extract_json_objects(text):
            if project_path is None and isinstance(obj.get("project_path"), str):
                project_path = obj["project_path"]
            if test_command is None and isinstance(obj.get("test_command"), str):
                test_command = obj["test_command"]
            if _is_proposal(obj):
                proposal = PatchProposal.from_dict(obj)
                proposals_by_id.setdefault(proposal.proposal_id, proposal)
            if _is_vote(obj):
                vote = FixerVote.from_dict(obj)
                votes_by_id.setdefault(vote.voter_id, vote)
    proposals = list(proposals_by_id.values())
    votes = list(votes_by_id.values())
    result = select_winner(proposals, votes)
    result["type"] = "consensus_result"
    result["proposal_count"] = len(proposals)
    result["valid_proposal_count"] = len(proposals)
    result["rejected_proposals"] = []
    result["vote_count"] = len(votes)
    if project_path:
        result["project_path"] = project_path
    if test_command:
        result["test_command"] = test_command
    result["proposals"] = [proposal.raw for proposal in proposals]
    result["votes"] = [
        {
            "voter_id": vote.voter_id,
            "ranking": vote.ranking,
            "selected": vote.selected,
            "rationale": vote.rationale,
        }
        for vote in votes
    ]

    # Save consensus_result to a known temp file so run_patch_applier.py can read it
    consensus_path = Path(tempfile.gettempdir()) / "chatdev_consensus_result.json"
    consensus_path.write_text(json.dumps(result), encoding="utf-8")

    print_json(result)

if __name__ == "__main__":
    main()