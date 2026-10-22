"""Task B input format: one claim, the evidence text it is checked against, and a three-way label.

Each JSONL line is {"id": str, "claim": str, "evidence": str, "label": str} with label in LABELS.
SUPPORTED = the evidence entails the claim; CONTRADICTED = the evidence entails its negation;
UNSUPPORTED = the evidence does not settle the claim (similar wording is not support).
"""
import json
from pathlib import Path

LABELS = ("SUPPORTED", "CONTRADICTED", "UNSUPPORTED")
FEVER_LABELS = {"SUPPORTS": "SUPPORTED", "REFUTES": "CONTRADICTED", "NOT ENOUGH INFO": "UNSUPPORTED"}


def map_fever_label(label):
    """FEVER verdict -> SafeLLM label; unknown values raise instead of being guessed."""
    if label not in FEVER_LABELS:
        raise ValueError(f"unknown FEVER label: {label!r}")
    return FEVER_LABELS[label]


def load_claims(path):
    """Read and validate one split; every record needs a non-empty claim and evidence text."""
    records = []
    with open(Path(path), encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            record = json.loads(line)
            missing = {"id", "claim", "evidence", "label"} - set(record)
            if missing:
                raise ValueError(f"{path}:{line_number} missing fields {sorted(missing)}")
            if record["label"] not in LABELS:
                raise ValueError(f"{path}:{line_number} label {record['label']!r} not in {LABELS}")
            if not str(record["claim"]).strip() or not str(record["evidence"]).strip():
                raise ValueError(f"{path}:{line_number} empty claim or evidence")
            records.append(record)
    ids = [r["id"] for r in records]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{path} contains duplicate ids")
    return records
