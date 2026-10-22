"""Categorized jailbreak-cue audit of the built binary dataset (read-only).

Reads `combined.parquet`, writes a full review list of BENIGN JailbreakHub rows that match
any cue (Git-ignored, includes a text excerpt for reviewers) and a counts-only summary
with cue rates per source and label. Labels and dataset files are not modified.
"""
import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path

import pyarrow.parquet as pq

from task_a.cue_audit import CUES, is_aiprm_boilerplate, review_priority

EXCERPT = 300


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="data/processed/binary_jailbreak/combined.parquet")
    parser.add_argument("--review-list", default="data/processed/binary_jailbreak/cue_review.csv")
    parser.add_argument("--summary", default="results/data_audit/jailbreak_cue_audit.json")
    args = parser.parse_args()
    for path in (args.review_list, args.summary):
        if Path(path).exists():
            raise FileExistsError(f"{path} exists; refusing to overwrite")
    rows = pq.read_table(args.dataset, columns=[
        "example_id", "text", "label", "split", "source_dataset", "source_config",
        "source_metadata", "family_label_mixed"]).to_pylist()

    rates = defaultdict(Counter)
    totals = Counter()
    review = []
    for r in rows:
        group = f"{r['source_config']}/label={r['label']}"
        totals[group] += 1
        priority, strong, matches = review_priority(r["text"])
        for category in matches:
            rates[group][category] += 1
        rates[group][f"priority_{priority}"] += 1
        if r["source_dataset"] == "jailbreakhub" and r["label"] == 0 and matches:
            meta = json.loads(r["source_metadata"])
            review.append({
                "example_id": r["example_id"], "split": r["split"], "label": r["label"],
                "priority": priority, "strong_categories": ";".join(strong),
                "all_categories": ";".join(matches),
                "matched_terms": json.dumps(matches, ensure_ascii=False),
                "aiprm_boilerplate": is_aiprm_boilerplate(r["text"]),
                "platform": meta.get("platform"), "source": meta.get("source"),
                "mixed_label_family": r["family_label_mixed"], "chars": len(r["text"]),
                "excerpt": " ".join(r["text"][:EXCERPT].split())})
    order = {"high": 0, "medium": 1, "low": 2}
    review.sort(key=lambda x: (order[x["priority"]], x["example_id"]))

    Path(args.review_list).parent.mkdir(parents=True, exist_ok=True)
    with open(args.review_list, "x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(review[0]))
        writer.writeheader()
        writer.writerows(review)
    summary = {
        "note": "Counts only. Cues are review aids, not labels; no row was changed.",
        "categories": {k: v[1] for k, v in CUES.items()},
        "rows_per_group": dict(totals),
        "cue_rate_per_group": {g: {k: round(v / totals[g], 4) for k, v in sorted(c.items())}
                               for g, c in sorted(rates.items())},
        "review_list": {"rows": len(review), "by_priority": dict(Counter(x["priority"] for x in review)),
                        "by_split": dict(Counter(x["split"] for x in review)),
                        "aiprm_boilerplate": sum(x["aiprm_boilerplate"] for x in review),
                        "by_source": dict(Counter(x["source"] for x in review).most_common(8))},
    }
    Path(args.summary).write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary["review_list"], indent=2))
    for g in sorted(summary["cue_rate_per_group"]):
        print(g, totals[g], {k: v for k, v in summary["cue_rate_per_group"][g].items()})


if __name__ == "__main__":
    main()
