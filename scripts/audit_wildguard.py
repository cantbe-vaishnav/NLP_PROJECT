"""Reproducible full-source audit and pending review queue. No label mapping."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import statistics

import pyarrow.parquet as pq
from task_a.leakage import duplicate_summary, adjacent_near_duplicates


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/task_a_full_audit.json")
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text())
    paths = [Path(config[k]) for k in ["report", "review_queue", "near_duplicate_pairs"]]
    if any(p.exists() for p in paths):
        raise FileExistsError("Audit outputs exist; choose fresh output paths")
    records = []
    sources = {}
    for split in ["train", "test"]:
        path = Path(config[split])
        rows = pq.read_table(path).to_pylist()
        with path.open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        sources[split] = {"sha256": digest, "bytes": path.stat().st_size, "rows": len(rows)}
        for index, row in enumerate(rows):
            records.append({**row, "id": f"wildguard:{split}:{index}", "split": split})
    report = {"config": config, "sources": sources, "gate_1_passed": False,
              "safellm_labels_assigned": False}
    for split in ["train", "test"]:
        rows = [r for r in records if r["split"] == split]
        lengths = [len(r["prompt"]) for r in rows if isinstance(r["prompt"], str)]
        report[split] = {
            "source_adversarial_counts": dict(Counter(str(r["adversarial"]) for r in rows)),
            "source_risk_category_counts": dict(Counter(r["subcategory"] for r in rows)),
            "source_flag_harm_strata": dict(Counter(
                f'{r["adversarial"]}/{r["prompt_harm_label"]}' for r in rows)),
            "empty_or_invalid_ids": [r["id"] for r in rows
                if not isinstance(r["prompt"], str) or not r["prompt"].strip()],
            "characters": {"min": min(lengths), "max": max(lengths),
                           "mean": statistics.mean(lengths), "median": statistics.median(lengths)},
        }
    report["exact"] = duplicate_summary(records)
    report["normalized"] = duplicate_summary(records, normalized=True)
    pairs = list(adjacent_near_duplicates(records, config["shingle_words"],
                                          config["near_jaccard_threshold"]))
    report["near_duplicate_diagnostic"] = {
        "method": "adjacent sorted normalized unique prompts; word-shingle Jaccard",
        "limitations": "low recall; not a template or leakage clearance",
        "pairs": len(pairs),
        "cross_official_split_pairs": sum(p["cross_official_split"] for p in pairs),
    }
    # Training only: avoid selecting rules based on final test examples.
    rng = random.Random(config["seed"])
    queue = []
    for flag in [False, True]:
        for harm in ["harmful", "unharmful"]:
            stratum = [r for r in records if r["split"] == "train"
                       and r["adversarial"] == flag and r["prompt_harm_label"] == harm]
            for r in rng.sample(stratum, min(config["sample_per_stratum"], len(stratum))):
                queue.append({"id": r["id"], "prompt": r["prompt"],
                              "source_adversarial": r["adversarial"],
                              "source_harmfulness": r["prompt_harm_label"],
                              "label": None, "status": "pending_human_review", "reviews": []})
    report["review_queue_rows"] = len(queue)
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
    paths[0].write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    for path, rows in [(paths[1], queue), (paths[2], pairs)]:
        path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    print(json.dumps({k: v for k, v in report.items() if k not in ['train', 'test', 'exact', 'normalized']}))
    for name in ["exact", "normalized"]:
        print(name, {k: v for k, v in report[name].items() if not k.endswith('_ids')})


if __name__ == "__main__":
    main()
