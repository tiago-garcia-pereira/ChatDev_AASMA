"""Small data helpers for debugger proposals, votes, and validation output."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PatchProposal:
    fixer_id: str
    strategy: str
    diagnosis: str
    solution_code: str
    confidence: float = 0.0
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def proposal_id(self) -> str:
        return self.fixer_id

    @classmethod
    def from_dict(cls, data: dict[str, Any], fallback_id: str = "unknown") -> "PatchProposal":
        # Prefer plain code output; keep legacy diff fields for backward compatibility.
        solution_code = str(data.get("solution_code") or "")
        if not solution_code:
            files = data.get("solution_files")
            if isinstance(files, list):
                rendered: list[str] = []
                for item in files:
                    if not isinstance(item, dict):
                        continue
                    path = str(item.get("path") or "").strip()
                    code = str(item.get("code") or "")
                    if not code:
                        continue
                    if path:
                        rendered.append(f"# FILE: {path}\n{code}")
                    else:
                        rendered.append(code)
                solution_code = "\n\n".join(rendered).strip()
        if not solution_code:
            solution_code = str(data.get("unified_diff") or data.get("patch") or "")

        return cls(
            fixer_id=str(data.get("fixer_id") or data.get("agent") or fallback_id),
            strategy=str(data.get("strategy") or ""),
            diagnosis=str(data.get("diagnosis") or data.get("rationale") or ""),
            solution_code=solution_code,
            confidence=_float(data.get("confidence"), default=0.0),
            raw=dict(data),
        )


@dataclass
class FixerVote:
    voter_id: str
    ranking: list[str]
    selected: str | None = None
    rationale: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any], fallback_id: str = "unknown") -> "FixerVote":
        ranking = data.get("ranking") or []
        if isinstance(ranking, str):
            ranking = [item.strip() for item in ranking.split(",") if item.strip()]
        elif not isinstance(ranking, list):
            ranking = []
        selected = data.get("selected") or data.get("vote")
        return cls(
            voter_id=str(data.get("voter_id") or data.get("fixer_id") or data.get("agent") or fallback_id),
            ranking=[str(item) for item in ranking],
            selected=str(selected) if selected else None,
            rationale=str(data.get("rationale") or data.get("reason") or ""),
        )


def _float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
