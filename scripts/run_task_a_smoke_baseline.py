"""Task A TF-IDF + LogReg smoke test (grouped out-of-fold CV on unanimous pilot items).

Pipeline validation only. It makes no held-out test claim and never uses source flags
or 2-vs-1 votes as labels. Outputs hold IDs and metrics; predictions.csv carries gold and
predicted labels (annotation content) and must stay out of Git unless approved.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import platform

from task_a.baseline import (
    SMOKE_BANNER, cross_validate, duplicate_groups, grouped_stratified_folds,
    per_class_metrics, split_manifest, unanimous_records)
from task_a.semantic_pilot import LABELS, expected_pilot_ids, jsonl_read, load_reviews


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/task_a_smoke_baseline.json")
    parser.add_argument("--reviewer-file", action="append", required=True, metavar="ID=PATH")
    parser.add_argument("--output-dir")
    args = parser.parse_args()

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    if tuple(config["allowed_labels"]) != LABELS:
        raise ValueError("Config allowed_labels must equal the canonical four-label schema")
    files = {}
    for item in args.reviewer_file:
        reviewer, _, path = item.partition("=")
        if not reviewer or not path:
            raise ValueError(f"--reviewer-file must be ID=PATH: {item}")
        files[reviewer] = path

    reviews = load_reviews(files, expected_pilot_ids(200))
    master = jsonl_read(config["master"])
    records = unanimous_records(master, reviews, config["exclude_ids"])
    counts = {label: sum(r["label"] == label for r in records) for label in LABELS}
    if len(records) != config["expected_eligible_items"] or \
            {k: v for k, v in counts.items() if v} != config["expected_label_counts"]:
        raise ValueError(f"Eligible set differs from config: {len(records)} items, {counts}")

    k, seed = config["folds"], config["seed"]
    groups = duplicate_groups(records, config["near_duplicate_threshold"], config["shingle_words"])
    assignment = grouped_stratified_folds(records, groups, k, seed)
    predictions, fold_info = cross_validate(records, assignment, k, seed, config["model"])
    gold = [r["label"] for r in records]
    pred = [predictions[r["id"]] for r in records]
    majority = max(LABELS, key=lambda label: counts[label])
    results = {
        "banner": SMOKE_BANNER,
        "eligible_items": len(records),
        "label_counts": counts,
        "absent_classes": [label for label in LABELS if not counts[label]],
        "duplicate_groups": len(set(groups.values())),
        "grouped_items": sum(1 for g in set(groups.values())
                             if sum(v == g for v in groups.values()) > 1),
        "folds": fold_info,
        "tfidf_logreg_out_of_fold": per_class_metrics(gold, pred),
        "majority_class_reference": {"label": majority,
                                     **per_class_metrics(gold, [majority] * len(gold))},
    }
    provenance = {
        "config": config, "python": platform.python_version(),
        "input_sha256": {"master": sha256(config["master"]),
                         **{f"reviewer_{r}": sha256(p) for r, p in sorted(files.items())}},
        "eligible_ids_sha256": hashlib.sha256("\n".join(r["id"] for r in records).encode()).hexdigest(),
        "note": "reviewer files are external to the repository; results are not reproducible "
                "from the repository alone",
    }
    try:
        import sklearn
        provenance["scikit_learn"] = sklearn.__version__
    except ImportError:
        pass

    out = Path(args.output_dir or config["output_dir"])
    out.mkdir(parents=True, exist_ok=False)
    dump = lambda name, obj: (out / name).write_text(
        json.dumps(obj, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    dump("config_and_provenance.json", provenance)
    dump("split_manifest.json", split_manifest(assignment, groups, k))
    dump("metrics.json", results)
    with open(out / "predictions.csv", "x", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["id", "fold", "gold_label", "predicted_label"])
        for r in records:
            writer.writerow([r["id"], assignment[r["id"]], r["label"], predictions[r["id"]]])
    (out / "report.md").write_text(render(results, k), encoding="utf-8")
    print(render(results, k))


def fmt(value):
    return "n/a (absent)" if value is None else f"{value:.3f}"


def render(results, k):
    m, ref = results["tfidf_logreg_out_of_fold"], results["majority_class_reference"]
    lines = ["# Task A TF-IDF + LogReg smoke test", "", f"**{SMOKE_BANNER}**", "",
             f"Items: {results['eligible_items']} unanimous pilot items; labels {results['label_counts']}.",
             f"Absent classes (no items, no metrics): {', '.join(results['absent_classes']) or 'none'}.",
             f"Evaluation: {k}-fold grouped, stratified out-of-fold; {results['duplicate_groups']} "
             f"duplicate groups ({results['grouped_items']} with more than one member).", "",
             "| Class | Support | Precision | Recall | F1 |", "|---|---|---|---|---|"]
    for label, c in m["per_class"].items():
        lines.append(f"| {label} | {c['support']} | {fmt(c['precision'])} | {fmt(c['recall'])} | {fmt(c['f1'])} |")
    lines += ["", f"Macro-F1 over {', '.join(m['macro_f1_classes'])}: {fmt(m['macro_f1'])} "
              f"(majority-class reference {ref['label']}: {fmt(ref['macro_f1'])}).",
              f"Accuracy: {fmt(m['accuracy'])}.", "",
              "Confusion matrix (rows gold, columns predicted; order "
              f"{', '.join(m['confusion_matrix']['rows_gold_cols_pred'])}):", ""]
    for gold_label, row in m["confusion_matrix"]["counts"].items():
        lines.append(f"- {gold_label}: " + ", ".join(str(row[p]) for p in LABELS))
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
