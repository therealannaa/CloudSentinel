"""Mechanical matching function — deterministic scoring of a reconstructed kill
chain against a ground-truth manifest.

Implements docs/week1/04_matching_function_spec.md. No human or LLM judging:
score() is a pure, total function of (reconstructed, manifest).

A reported stage matches a ground-truth stage iff (Section 2):
  1. exact TTP id match,
  2. telemetry source match,
  3. evidence binding: >= 1 shared evidence_event_id.
Matching is one-to-one (greedy by stage_id). Benign manifests (no stages) score
recall 1.0; any reported stage on a benign scenario is a false positive.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ScoreResult:
    tp: int
    fp: int
    fn: int
    recall: float
    precision: float
    f1: float
    order_penalty: float          # fraction of matched stages out of canonical order
    order_aware_recall: float     # recall * (1 - order_penalty)
    matched_gt: list[int] = field(default_factory=list)
    missed_gt: list[int] = field(default_factory=list)
    spurious_reported: list[int] = field(default_factory=list)

    def to_dict(self):
        return self.__dict__.copy()


def _stage_get(stage, key):
    """Accept either dicts or objects with attributes (Stage / dataclass)."""
    if isinstance(stage, dict):
        return stage[key]
    return getattr(stage, key)


def _stages_of(obj):
    if isinstance(obj, dict):
        return obj.get("stages", [])
    return getattr(obj, "stages", [])


def _base_ttp(ttp: str) -> str:
    """Base technique id, dropping any sub-technique suffix (T1078.004 -> T1078)."""
    return ttp.split(".")[0]


def _ttp_equal(a: str, b: str, mode: str) -> bool:
    """`exact`: full id must match. `parent`: match at the base-technique level, so a
    reasonable parent-vs-sub answer (T1078 vs T1078.004) is credited (docs/week1/04 §7)."""
    if mode == "parent":
        return _base_ttp(a) == _base_ttp(b)
    return a == b


def _matches(reported, truth, ttp_match: str = "exact") -> bool:
    if not _ttp_equal(_stage_get(reported, "ttp_id"), _stage_get(truth, "ttp_id"), ttp_match):
        return False
    if _stage_get(reported, "telemetry_source") != _stage_get(truth, "telemetry_source"):
        return False
    overlap = set(_stage_get(reported, "evidence_event_ids")) & set(
        _stage_get(truth, "evidence_event_ids"))
    return len(overlap) >= 1


def _longest_increasing_subseq_len(seq) -> int:
    """Length of the longest strictly-increasing subsequence (for order check)."""
    import bisect
    tails = []
    for x in seq:
        i = bisect.bisect_left(tails, x)
        if i == len(tails):
            tails.append(x)
        else:
            tails[i] = x
    return len(tails)


def score(reconstructed, manifest, ttp_match: str = "exact") -> ScoreResult:
    """Score one reconstructed chain against one manifest. `ttp_match` is 'exact'
    (default) or 'parent' (credit a parent-vs-sub-technique answer). See docstring."""
    gt = list(_stages_of(manifest))
    rep = list(_stages_of(reconstructed))

    matched_rep_idx: set[int] = set()
    # ordered list of (gt_stage_id, reported_position) for matched pairs
    matched_pairs: list[tuple[int, int]] = []
    matched_gt_ids: list[int] = []

    for g in gt:
        for j, r in enumerate(rep):
            if j in matched_rep_idx:
                continue
            if _matches(r, g, ttp_match):
                matched_rep_idx.add(j)
                matched_pairs.append((_stage_get(g, "stage_id"), j))
                matched_gt_ids.append(_stage_get(g, "stage_id"))
                break

    tp = len(matched_gt_ids)
    fn = len(gt) - tp
    fp = len(rep) - len(matched_rep_idx)

    recall = tp / (tp + fn) if (tp + fn) else 1.0          # benign: no GT stages
    precision = tp / (tp + fp) if (tp + fp) else 1.0       # benign + no reports
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    # Order penalty: of the matched stages, how many are NOT in canonical order.
    # Sort matched pairs by ground-truth stage_id, read off reported positions;
    # a perfectly-ordered reconstruction yields an increasing position sequence.
    if tp >= 2:
        positions = [j for _, j in sorted(matched_pairs, key=lambda p: p[0])]
        in_order = _longest_increasing_subseq_len(positions)
        order_penalty = round((tp - in_order) / tp, 6)
    else:
        order_penalty = 0.0

    order_aware_recall = round(recall * (1 - order_penalty), 6)

    missed = [_stage_get(g, "stage_id") for g in gt
              if _stage_get(g, "stage_id") not in set(matched_gt_ids)]
    spurious = [k for k in range(len(rep)) if k not in matched_rep_idx]

    return ScoreResult(
        tp=tp, fp=fp, fn=fn,
        recall=round(recall, 6), precision=round(precision, 6), f1=round(f1, 6),
        order_penalty=order_penalty, order_aware_recall=order_aware_recall,
        matched_gt=sorted(matched_gt_ids), missed_gt=missed, spurious_reported=spurious,
    )
