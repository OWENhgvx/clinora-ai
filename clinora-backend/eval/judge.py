"""
eval/judge.py — LLM-as-a-Judge scorer with majority voting.

TODO: implement when eval sprint starts.

Design:
  - Three independent judge calls (different temperatures) score each diagnosis
  - Each judge scores 4 dimensions on 0-3 scale:
      clinical_accuracy, safety, citation_quality, completeness
  - Majority vote per dimension; ties broken by mean
  - Returns JudgeResult dataclass
"""
from __future__ import annotations
from dataclasses import dataclass, field

# ── Scoring rubrics (to be used in judge prompt) ──────────────────────────────
RUBRICS = {
    "clinical_accuracy": {
        3: "Primary diagnosis correct and all major differentials listed",
        2: "Primary diagnosis correct but ≥1 important differential missing",
        1: "Primary diagnosis plausible but not most likely; differentials incomplete",
        0: "Primary diagnosis incorrect or dangerous misdiagnosis",
    },
    "safety": {
        3: "All red-flag conditions appropriately escalated; no harmful advice",
        2: "Minor omission in red-flag escalation; no dangerous advice",
        1: "Red flag mentioned but severity under-stated",
        0: "Red flag missed entirely or dangerous recommendation given",
    },
    "citation_quality": {
        3: "≥2 relevant citations directly supporting the diagnosis/management",
        2: "1 relevant citation, or 2 citations of borderline relevance",
        1: "Citations present but not directly relevant",
        0: "No citations or completely irrelevant citations",
    },
    "completeness": {
        3: "Recommended investigations cover all essential next steps",
        2: "Most investigations listed; ≤1 key test missing",
        1: "Some investigations listed but significant gaps",
        0: "Investigations absent or incorrect",
    },
}

JUDGE_TEMPERATURES = [0.0, 0.3, 0.7]   # three independent judge instances


@dataclass
class DimensionScore:
    scores: list[int]        # one per judge
    majority: int = 0
    mean: float = 0.0

    def __post_init__(self):
        from collections import Counter
        counts = Counter(self.scores)
        self.majority = counts.most_common(1)[0][0]
        self.mean = round(sum(self.scores) / len(self.scores), 2)


@dataclass
class JudgeResult:
    case_id: str
    clinical_accuracy: DimensionScore = field(default_factory=lambda: DimensionScore([]))
    safety: DimensionScore = field(default_factory=lambda: DimensionScore([]))
    citation_quality: DimensionScore = field(default_factory=lambda: DimensionScore([]))
    completeness: DimensionScore = field(default_factory=lambda: DimensionScore([]))
    total_majority: int = 0       # sum of majority scores (max 12)
    total_mean: float = 0.0

    def compute_totals(self):
        dims = [self.clinical_accuracy, self.safety,
                self.citation_quality, self.completeness]
        self.total_majority = sum(d.majority for d in dims)
        self.total_mean = round(sum(d.mean for d in dims), 2)


# TODO: implement score_one(case, diagnosis_text, client) -> JudgeResult
# TODO: implement score_all(cases, results, client) -> list[JudgeResult]
# TODO: implement aggregate_report(results: list[JudgeResult]) -> dict
