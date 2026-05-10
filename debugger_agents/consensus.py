"""Consensus algorithms for patch proposals."""

from collections import defaultdict

from debugger_agents.schemas import FixerVote, PatchProposal


def borda_count(proposals: list[PatchProposal], votes: list[FixerVote]) -> dict:
    proposal_ids = [proposal.proposal_id for proposal in proposals]
    n = len(proposal_ids)
    scores: defaultdict[str, float] = defaultdict(float)
    for vote in votes:
        ranking = [item for item in vote.ranking if item in proposal_ids]
        if not ranking and vote.selected in proposal_ids:
            ranking = [vote.selected]
        if not ranking:
            continue
        ranking.extend(item for item in proposal_ids if item not in ranking)
        for rank, proposal_id in enumerate(ranking):
            scores[proposal_id] += n - rank - 1
    if not scores:
        for proposal in proposals:
            scores[proposal.proposal_id] = proposal.confidence
    return _winner_payload("borda", proposals, dict(scores))


def select_winner(
    proposals: list[PatchProposal],
    votes: list[FixerVote],
) -> dict:
    return borda_count(proposals, votes)


def _winner_payload(method: str, proposals: list[PatchProposal], scores: dict[str, float]) -> dict:
    proposal_map = {proposal.proposal_id: proposal for proposal in proposals}
    ranked = sorted(scores.items(), key=lambda item: (item[1], proposal_map.get(item[0], PatchProposal(item[0], "", "", "")).confidence), reverse=True)
    winner_id = ranked[0][0] if ranked else (proposals[0].proposal_id if proposals else None)
    winner = proposal_map.get(winner_id) if winner_id else None
    return {
        "method": method,
        "winner_id": winner_id,
        "scores": scores,
        "ranked": [{"proposal_id": proposal_id, "score": score} for proposal_id, score in ranked],
        "winner": winner.raw if winner else None,
    }
