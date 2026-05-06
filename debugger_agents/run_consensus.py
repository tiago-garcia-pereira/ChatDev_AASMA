"""ChatDev script node entry point for consensus selection."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from debugger_agents.consensus import select_winner
from debugger_agents.heuristic_fixer import build_heuristic_proposal
from debugger_agents.io_utils import combined_input_text, extract_json_objects, find_project_path, input_texts, print_json
from debugger_agents.schemas import FixerVote, PatchProposal
from debugger_agents.validator import check_patch_applicability


def main() -> None:
    proposals: list[PatchProposal] = []
    votes: list[FixerVote] = []
    context = combined_input_text()
    project_path = find_project_path(context)
    for text in input_texts():
        for obj in extract_json_objects(text):
            if obj.get("unified_diff") or obj.get("patch"):
                proposals.append(PatchProposal.from_dict(obj))
            if obj.get("ranking") or obj.get("vote") or obj.get("selected"):
                votes.append(FixerVote.from_dict(obj))

    heuristic = build_heuristic_proposal(project_path, context)
    if heuristic:
        proposals.append(PatchProposal.from_dict(heuristic))

    valid_proposals: list[PatchProposal] = []
    rejected = []
    for proposal in proposals:
        check = check_patch_applicability(project_path, proposal.unified_diff)
        if check.get("valid"):
            valid_proposals.append(proposal)
        else:
            rejected.append({
                "proposal_id": proposal.proposal_id,
                "reason": check.get("reason", "invalid patch"),
            })

    result = select_winner(valid_proposals, votes)
    result["type"] = "consensus_result"
    result["proposal_count"] = len(proposals)
    result["valid_proposal_count"] = len(valid_proposals)
    result["rejected_proposals"] = rejected
    result["vote_count"] = len(votes)
    print_json(result)


if __name__ == "__main__":
    main()
