"""Deterministic Task B baselines and evaluation helpers."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import time
from typing import Callable

from .schema import ClaimEvidence, LABELS


TOKEN = re.compile(r"\b\w+\b", re.UNICODE)
NEGATIONS = {"no", "not", "never", "none", "neither", "without", "n't"}
NUMBER = re.compile(r"\b\d+(?:[.,]\d+)*\b")


def tokens(text: str) -> set[str]:
    return set(TOKEN.findall(text.lower()))


def majority_prior(training_labels: list[str]) -> str:
    if not training_labels or any(label not in LABELS for label in training_labels):
        raise ValueError("Provide non-empty Task B training/development labels")
    counts = Counter(training_labels)
    return max(LABELS, key=lambda label: counts[label])


def overlap_score(record: ClaimEvidence) -> float:
    """Largest share of claim tokens found in one evidence sentence (0 for an empty claim)."""
    claim_tokens = tokens(record.claim)
    if not claim_tokens:
        return 0.0
    return max(len(claim_tokens & tokens(item.text)) / len(claim_tokens) for item in record.evidence)


def lexical_overlap(record: ClaimEvidence, threshold: float = 0.5) -> str:
    """Only SUPPORTED/UNSUPPORTED; cannot identify contradictions."""
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be between 0 and 1")
    if not tokens(record.claim):
        return "UNSUPPORTED"
    return "SUPPORTED" if overlap_score(record) >= threshold else "UNSUPPORTED"


def lexical_cues(record: ClaimEvidence, threshold: float = 0.5) -> str:
    """Fixed negation/numeric cues; rough diagnostic, not semantic reasoning."""
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be between 0 and 1")
    claim = tokens(record.claim)
    content = claim - NEGATIONS - set(NUMBER.findall(record.claim))
    if not content:
        return "UNSUPPORTED"
    best = max(record.evidence,
               key=lambda item: len(content & tokens(item.text)) / len(content))
    overlap = len(content & tokens(best.text)) / len(content)
    if overlap < threshold:
        return "UNSUPPORTED"
    claim_numbers = set(NUMBER.findall(record.claim))
    evidence_numbers = set(NUMBER.findall(best.text))
    number_conflict = bool(claim_numbers and evidence_numbers and claim_numbers.isdisjoint(evidence_numbers))
    negation_conflict = bool(claim & NEGATIONS) != bool(tokens(best.text) & NEGATIONS)
    return "CONTRADICTED" if number_conflict or negation_conflict else "SUPPORTED"


def evaluate(gold: list[str], predicted: list[str], labels: tuple[str, ...],
             latency_seconds: list[float] | None = None) -> dict:
    if not gold or len(gold) != len(predicted):
        raise ValueError("gold and predictions must have the same non-zero length")
    if any(label not in labels for label in gold + predicted):
        raise ValueError("labels outside the declared evaluation set")
    matrix = [[sum(g == actual and p == guess for g, p in zip(gold, predicted))
               for guess in labels] for actual in labels]
    per_class = {}
    for index, label in enumerate(labels):
        tp = matrix[index][index]
        support = sum(matrix[index])
        predicted_count = sum(row[index] for row in matrix)
        precision = tp / predicted_count if predicted_count else 0.0
        recall = tp / support if support else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {"precision": precision, "recall": recall,
                            "f1": f1, "support": support}
    result = {"n": len(gold), "labels": list(labels), "accuracy":
              sum(g == p for g, p in zip(gold, predicted)) / len(gold),
              "macro_f1": sum(row["f1"] for row in per_class.values()) / len(labels),
              "per_class": per_class, "confusion_matrix": matrix,
              "incorrect_supported": sum(g != "SUPPORTED" and p == "SUPPORTED"
                                          for g, p in zip(gold, predicted))}
    if "CONTRADICTED" in labels:
        result["contradicted_recall"] = per_class["CONTRADICTED"]["recall"]
    if latency_seconds is not None:
        if len(latency_seconds) != len(gold):
            raise ValueError("latency length mismatch")
        result["latency_mean_ms"] = 1000 * sum(latency_seconds) / len(gold)
        result["latency_total_seconds"] = sum(latency_seconds)
    return result


def timed_predictions(records: list[ClaimEvidence], predictor: Callable[[ClaimEvidence], str]):
    predictions, latency = [], []
    for record in records:
        start = time.perf_counter()
        predictions.append(predictor(record))
        latency.append(time.perf_counter() - start)
    return predictions, latency


def fever_binary_proxy(label: str) -> str:
    """For FEVER SUPPORTS/REFUTES diagnostics only: any non-support is negative."""
    if label not in LABELS:
        raise ValueError("unknown Task B label")
    return "SUPPORTED" if label == "SUPPORTED" else "CONTRADICTED"


def choose_threshold(gold: list[str], predict_at: Callable[[float], list[str]],
                     grid: list[float], labels: tuple[str, ...] = ("SUPPORTED", "CONTRADICTED")) -> tuple[float, list[dict]]:
    """Pick the cutoff with the best validation macro-F1.

    With the default two labels this scores the FEVER binary diagnostic (UNSUPPORTED counted as
    not-supported); with all three LABELS, predictions are scored as they are. Use validation
    records only. Ties keep the earlier (lower) grid value.
    """
    if not grid or sorted(grid) != list(grid):
        raise ValueError("grid must be non-empty and ascending")
    binary = tuple(labels) == ("SUPPORTED", "CONTRADICTED")
    search = []
    for threshold in grid:
        predicted = [fever_binary_proxy(label) if binary else label for label in predict_at(threshold)]
        search.append({"threshold": threshold, "validation_macro_f1": evaluate(gold, predicted, labels)["macro_f1"]})
    best = max(search, key=lambda row: row["validation_macro_f1"])  # max() keeps the first of equal values
    return best["threshold"], search


def new_run_dir(parent: str | Path, prefix: str = "run_") -> Path:
    """Create and return a new <prefix><UTC timestamp> folder; a taken name gets a numeric suffix, never reused."""
    parent = Path(parent)
    parent.mkdir(parents=True, exist_ok=True)
    stamp = prefix + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for attempt in range(1, 1000):
        path = parent / (stamp if attempt == 1 else f"{stamp}_{attempt}")
        try:
            path.mkdir()
            return path
        except FileExistsError:
            continue
    raise FileExistsError(f"no free run folder name for {parent / stamp}")


def save_run(output_dir: str | Path, config: dict, predictions: list[dict], results: dict) -> None:
    """Write one run to a new directory; an existing run is never overwritten."""
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=False)
    for name, data in (("config.json", config), ("results.json", results)):
        (directory / name).write_text(json.dumps(data, indent=2), encoding="utf-8")
    with (directory / "predictions.jsonl").open("w", encoding="utf-8") as handle:
        for row in predictions:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
