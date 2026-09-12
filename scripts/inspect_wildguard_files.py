"""Inspect downloaded source files, without assigning SafeLLM labels or splits."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import pyarrow.parquet as pq


def inspect_file(path):
    path = Path(path)
    table = pq.read_table(path)
    required = {"prompt", "adversarial", "prompt_harm_label"}
    if not required.issubset(table.column_names):
        raise ValueError("Missing required WildGuardMix source fields")
    rows = table.select(sorted(required)).to_pylist()
    text_counts = Counter(r["prompt"] for r in rows if isinstance(r["prompt"], str))
    with path.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    return {
        "filename": path.name,
        "bytes": path.stat().st_size,
        "sha256": digest,
        "rows": table.num_rows,
        "schema": str(table.schema),
        "null_counts": {name: table[name].null_count for name in table.column_names},
        "source_adversarial_counts": dict(Counter(
            json.dumps(r["adversarial"]) for r in rows)),
        "source_harmfulness_counts": dict(Counter(
            json.dumps(r["prompt_harm_label"]) for r in rows)),
        "invalid_adversarial_values": sum(type(r["adversarial"]) is not bool for r in rows),
        "empty_or_invalid_prompts": sum(
            not isinstance(r["prompt"], str) or not r["prompt"].strip() for r in rows),
        "exact_prompt_duplicate_excess": sum(n - 1 for n in text_counts.values()),
        "safellm_labels_assigned": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", required=True, type=Path)
    parser.add_argument("--test", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = {"status": "source inspection only; not Gate 1 approval",
              "train": inspect_file(args.train), "test": inspect_file(args.test)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as output:
        json.dump(report, output, indent=2, allow_nan=False)
        output.write("\n")
    print(args.output)


if __name__ == "__main__":
    main()
