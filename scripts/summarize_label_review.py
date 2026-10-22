"""Summarize the JailbreakHub label review into a counts-only report (no prompt text).

Inputs (Git-ignored): the built `combined.parquet` and the two review CSVs under
`data/processed/binary_jailbreak/review/`. Outputs: a JSON and Markdown report with
status counts, the reverse-audit sampling method and estimate, proposed exclusions
(IDs only) and their hypothetical impact per split. Nothing is excluded or relabelled
here; the dataset is unchanged.
"""
import argparse
from collections import Counter, defaultdict
import csv
import json
import math
from pathlib import Path

import pyarrow.parquet as pq

from task_a.cue_audit import review_priority

REVIEW_DIR = "data/processed/binary_jailbreak/review"


def wilson(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(centre - half, 4), round(centre + half, 4)]


def read(name):
    with open(Path(REVIEW_DIR) / name, encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def split_counts(rows):
    out = defaultdict(Counter)
    for r in rows:
        out[r["split"]][f"{r['source_dataset']}/label={r['label']}"] += 1
    return {s: dict(sorted(c.items())) for s, c in sorted(out.items())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="data/processed/binary_jailbreak/combined.parquet")
    parser.add_argument("--json", default="results/data_audit/label_review_report.json")
    parser.add_argument("--markdown", default="results/data_audit/label_review_report.md")
    args = parser.parse_args()
    for path in (args.json, args.markdown):
        if Path(path).exists():
            raise FileExistsError(f"{path} exists; refusing to overwrite")

    rows = pq.read_table(args.dataset, columns=["example_id", "text", "label", "split",
                                                "source_dataset", "family_label_mixed"]).to_pylist()
    by_id = {r["example_id"]: r for r in rows}
    high, rev = read("high_priority_benign_review.csv"), read("reverse_sample_jailbreak_review.csv")

    jbh_pos = [r for r in rows if r["source_dataset"] == "jailbreakhub" and r["label"] == 1]
    priority = {r["example_id"]: review_priority(r["text"])[0] for r in jbh_pos}
    rev_low = [r for r in rev if priority[r["example_id"]] in ("none", "low")]
    pool_low = [r for r in jbh_pos if priority[r["example_id"]] in ("none", "low")]
    k_all = sum(r["status"] == "CONFIRMED_MISLABEL" for r in rev)
    k_low = sum(r["status"] == "CONFIRMED_MISLABEL" for r in rev_low)
    ci_low = wilson(k_low, len(rev_low))

    excluded = [r["example_id"] for r in high + rev if r["status"] == "CONFIRMED_MISLABEL"]
    ambiguous = [r["example_id"] for r in high + rev if r["status"] == "AMBIGUOUS"]
    drop = set(excluded)
    report = {
        "note": "Counts and IDs only. Reviews are full-text reviews, not human annotation. "
                "No row has been excluded or relabelled; exclusions below are proposals.",
        "high_priority_benign_review": {
            "rows": len(high), "status": dict(Counter(r["status"] for r in high)),
            "status_by_split": {s: dict(Counter(r["status"] for r in high if r["split"] == s))
                                for s in sorted({r["split"] for r in high})},
            "confirmed_in_mixed_label_families": sum(
                r["status"] == "CONFIRMED_MISLABEL" and by_id[r["example_id"]]["family_label_mixed"]
                for r in high)},
        "reverse_audit": {
            "population": "retained JailbreakHub rows with label 1 in combined.parquet",
            "population_rows": len(jbh_pos),
            "sampling": "sorted by example_id, Python random.seed(42), random.sample(n=40)",
            "status": dict(Counter(r["status"] for r in rev)),
            "mislabel_rate": round(k_all / len(rev), 4), "mislabel_rate_wilson95": wilson(k_all, len(rev)),
            "status_by_cue_priority": {p: dict(Counter(r["status"] for r in rev if priority[r["example_id"]] == p))
                                       for p in ("high", "medium", "low", "none")},
            "remaining_scope": {
                "definition": "label-1 JailbreakHub rows whose cue priority is none or low",
                "rows": len(pool_low), "already_reviewed": len(rev_low),
                "by_split": dict(Counter(r["split"] for r in pool_low)),
                "total_characters": sum(len(r["text"]) for r in pool_low),
                "sample_mislabel_rate_in_scope": round(k_low / len(rev_low), 4) if rev_low else None,
                "sample_mislabel_rate_in_scope_wilson95": ci_low,
                "estimated_mislabels_in_scope": None if ci_low is None else
                    [round(ci_low[0] * len(pool_low)), round(k_low / len(rev_low) * len(pool_low)),
                     round(ci_low[1] * len(pool_low))]}},
        "proposed_exclusions": {"count": len(excluded), "reason": "CONFIRMED_MISLABEL in review",
                                "example_ids": sorted(excluded)},
        "ambiguous_kept_for_decision": {"count": len(ambiguous), "example_ids": sorted(ambiguous)},
        "split_counts_current": split_counts(rows),
        "split_counts_after_proposed_exclusions": split_counts([r for r in rows if r["example_id"] not in drop]),
    }
    Path(args.json).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    Path(args.markdown).write_text(render(report), encoding="utf-8")
    print(render(report))


def render(rep):
    h, r = rep["high_priority_benign_review"], rep["reverse_audit"]
    s = r["remaining_scope"]
    lines = ["# JailbreakHub label review (counts only)", "", rep["note"], "",
             "## High-priority BENIGN rows (full text reviewed)", "",
             f"Rows: {h['rows']}. Status: {h['status']}. By split: {h['status_by_split']}.",
             f"Confirmed mislabels already in mixed-label near-duplicate families: "
             f"{h['confirmed_in_mixed_label_families']}.", "",
             "## Reverse audit of ADVERSARIAL (jailbreak-config) rows", "",
             f"Population {r['population_rows']}; sampling: {r['sampling']}.",
             f"Status: {r['status']}; mislabel rate {r['mislabel_rate']} (Wilson 95% {r['mislabel_rate_wilson95']}).",
             f"By cue priority: {r['status_by_cue_priority']}.", "",
             f"Remaining scope ({s['definition']}): {s['rows']} rows ({s['already_reviewed']} already reviewed), "
             f"by split {s['by_split']}, {s['total_characters']} characters. In-scope sample mislabel rate "
             f"{s['sample_mislabel_rate_in_scope']} (Wilson 95% {s['sample_mislabel_rate_in_scope_wilson95']}); "
             f"estimated mislabels in scope (low, point, high): {s['estimated_mislabels_in_scope']}.", "",
             "## Proposed exclusions (not applied)", "",
             f"{rep['proposed_exclusions']['count']} rows marked CONFIRMED_MISLABEL; "
             f"{rep['ambiguous_kept_for_decision']['count']} AMBIGUOUS rows kept for an owner decision. "
             "IDs are listed in the JSON report.", "",
             "| Split | Group | Current | After exclusions |", "|---|---|---|---|"]
    cur, aft = rep["split_counts_current"], rep["split_counts_after_proposed_exclusions"]
    for split in cur:
        for group, n in cur[split].items():
            lines.append(f"| {split} | {group} | {n} | {aft.get(split, {}).get(group, 0)} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
