"""Sampling and analysis for the human semantic-validation pilot."""

from collections import Counter, defaultdict
import csv
import json
import math
import random

from task_a.leakage import comparison_key

LABELS = ("ADVERSARIAL", "BENIGN", "QUARANTINE")


def sample_unique_strata(rows, quota=50, seed=42):
    """Sample comparison-normalized unique prompts from four source strata."""
    if quota < 1:
        raise ValueError("quota must be positive")
    strata = defaultdict(dict)
    duplicate_candidates = Counter()
    for index, row in enumerate(rows):
        prompt = row.get("prompt")
        flag = row.get("adversarial")
        harm = row.get("prompt_harm_label")
        if not isinstance(prompt, str) or not prompt.strip():
            continue
        if type(flag) is not bool or harm not in {"harmful", "unharmful"}:
            continue
        stratum = f"{str(flag).lower()}__{harm}"
        key = comparison_key(prompt)
        duplicate_candidates[stratum] += key in strata[stratum]
        strata[stratum].setdefault(key, (index, row))

    selected = []
    summary = {}
    for stratum in ("false__harmful", "false__unharmful",
                    "true__harmful", "true__unharmful"):
        candidates = list(strata[stratum].values())
        rng = random.Random(f"{seed}:{stratum}")
        chosen = rng.sample(candidates, min(quota, len(candidates)))
        summary[stratum] = {
            "eligible_unique": len(candidates),
            "selected": len(chosen),
            "shortfall": max(0, quota - len(chosen)),
            "duplicate_candidates_skipped": duplicate_candidates[stratum],
        }
        for index, row in chosen:
            selected.append({
                "pilot_id": f"pilot-{len(selected) + 1:03d}",
                "source_id": f"wildguard:train:{index}",
                "prompt": row["prompt"],
                "source_adversarial": row["adversarial"],
                "source_harmfulness": row["prompt_harm_label"],
                "source_risk_category": row.get("subcategory"),
                "source_split": "train",
                "sampling_stratum": stratum,
            })
    return selected, summary


def read_annotations(path, expected_ids, expected_reviewer_id):
    """Validate a completed independent reviewer CSV."""
    with open(path, newline="", encoding="utf-8-sig") as source:
        rows = list(csv.DictReader(source))
    required = {"pilot_id", "prompt", "safellm_label", "reviewer_id", "rationale"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f"{path}: missing required columns or rows")
    found = [row["pilot_id"] for row in rows]
    if len(found) != len(set(found)) or set(found) != set(expected_ids):
        raise ValueError(f"{path}: IDs must match the pilot exactly once")
    result = {}
    for row in rows:
        label = row["safellm_label"].strip().upper()
        reviewer = row["reviewer_id"].strip()
        rationale = row["rationale"].strip()
        if label not in LABELS:
            raise ValueError(f'{path}: invalid label for {row["pilot_id"]}')
        if reviewer != expected_reviewer_id:
            raise ValueError(f'{path}: reviewer_id must be {expected_reviewer_id}')
        if not rationale:
            raise ValueError(f'{path}: rationale required for {row["pilot_id"]}')
        result[row["pilot_id"]] = {"label": label, "rationale": rationale}
    return result


def cohens_kappa(labels_a, labels_b):
    if len(labels_a) != len(labels_b) or not labels_a:
        raise ValueError("Two nonempty equal-length label lists are required")
    n = len(labels_a)
    observed = sum(a == b for a, b in zip(labels_a, labels_b)) / n
    counts_a, counts_b = Counter(labels_a), Counter(labels_b)
    expected = sum((counts_a[label] / n) * (counts_b[label] / n) for label in LABELS)
    if math.isclose(expected, 1.0):
        return 1.0 if math.isclose(observed, 1.0) else None
    return (observed - expected) / (1 - expected)


def analyze(master, review_a, review_b):
    labels_a = [review_a[row["pilot_id"]]["label"] for row in master]
    labels_b = [review_b[row["pilot_id"]]["label"] for row in master]
    agreement = sum(a == b for a, b in zip(labels_a, labels_b))
    strata = defaultdict(lambda: {"rows": 0, "disagreements": 0})
    source_crosstab = defaultdict(Counter)
    adjudication = []
    agreed_binary = 0
    source_mismatch = 0
    for row, a, b in zip(master, labels_a, labels_b):
        stat = strata[row["sampling_stratum"]]
        stat["rows"] += 1
        if a != b:
            stat["disagreements"] += 1
        if a == b:
            source_crosstab[str(row["source_adversarial"]).lower()][a] += 1
            if a in {"ADVERSARIAL", "BENIGN"}:
                agreed_binary += 1
                source_mismatch += (row["source_adversarial"] != (a == "ADVERSARIAL"))
        if a != b or "QUARANTINE" in {a, b}:
            adjudication.append({
                "pilot_id": row["pilot_id"], "prompt": row["prompt"],
                "reviewer_1_label": a,
                "reviewer_1_rationale": review_a[row["pilot_id"]]["rationale"],
                "reviewer_2_label": b,
                "reviewer_2_rationale": review_b[row["pilot_id"]]["rationale"],
                "adjudicated_label": "", "adjudicator_id": "", "adjudication_rationale": "",
            })
    for stat in strata.values():
        stat["disagreement_rate"] = stat["disagreements"] / stat["rows"]
    return {
        "rows": len(master),
        "agreement_count": agreement,
        "agreement_rate": agreement / len(master),
        "cohens_kappa_three_class": cohens_kappa(labels_a, labels_b),
        "reviewer_1_distribution": dict(Counter(labels_a)),
        "reviewer_2_distribution": dict(Counter(labels_b)),
        "disagreement_by_stratum": dict(strata),
        "source_adversarial_vs_agreed_human_label": {
            key: dict(value) for key, value in source_crosstab.items()
        },
        "agreed_binary_rows": agreed_binary,
        "source_label_mismatch_count_on_agreed_binary": source_mismatch,
        "source_label_mismatch_rate_on_agreed_binary": (
            source_mismatch / agreed_binary if agreed_binary else None),
        "adjudication_queue_rows": len(adjudication),
    }, adjudication


def write_csv(path, fieldnames, rows):
    with open(path, "x", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def jsonl_read(path):
    with open(path, encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]
