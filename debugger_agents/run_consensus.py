"""ChatDev script node entry point for consensus selection."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from debugger_agents.consensus import select_winner
from debugger_agents.io_utils import extract_json_objects, input_texts, print_json
from debugger_agents.schemas import FixerVote, PatchProposal


def main() -> None:
    proposals: list[PatchProposal] = []
    votes: list[FixerVote] = []
    for text in input_texts():
        for obj in extract_json_objects(text):
            if obj.get("unified_diff") or obj.get("patch"):
                proposals.append(PatchProposal.from_dict(obj))
            if obj.get("ranking") or obj.get("vote") or obj.get("selected"):
                votes.append(FixerVote.from_dict(obj))

    result = select_winner(proposals, votes)
    result["type"] = "consensus_result"
    result["proposal_count"] = len(proposals)
    result["vote_count"] = len(votes)
    print_json(result)


if __name__ == "__main__":
    main()
