"""Three-reviewer, four-label agreement analysis for the Task A pilot.

Reads completed reviewer files (read-only), validates them, and writes a JSON result,
a Markdown report and a per-item disagreement table. Nothing is adjudicated.
"""
import argparse
import hashlib
import json
from pathlib import Path

from task_a.semantic_pilot import (
    LABELS, analyze_agreement, expected_pilot_ids, jsonl_read, load_reviews, render_report,
    source_label_crosstab, stratum_disagreement, write_csv)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/task_a_semantic_pilot.json")
    parser.add_argument("--reviewer-file", action="append", default=[], metavar="ID=PATH",
                        help="override a configured reviewer file (repeatable)")
    parser.add_argument("--output-dir", help="override analysis_output_dir")
    parser.add_argument("--include-prompts", action="store_true",
                        help="include licensed prompt text in the disagreement table")
    parser.add_argument("--source-crosstab", action="store_true",
                        help="also write a descriptive source-flag x label table "
                             "(requires the local master; see docs/task_a_source_label_comparison.md)")
    args = parser.parse_args()

    config = json.loads(Path(args.config).read_text())
    if tuple(config["allowed_labels"]) != LABELS:
        raise ValueError("Config allowed_labels must equal the canonical four-label schema")
    files = dict(config["analysis_reviewers"])
    for item in args.reviewer_file:
        reviewer, _, path = item.partition("=")
        if reviewer not in files or not path:
            raise ValueError(f"--reviewer-file must be ID=PATH with a configured ID: {item}")
        files[reviewer] = path

    reviews = load_reviews(files, expected_pilot_ids(config["expected_items"]))
    results, disagreements = analyze_agreement(reviews, args.include_prompts)
    results["inputs"] = {
        "location": "external to the repository (annotation files are Git-ignored licensed data)",
        "reproducible_from_repository_alone": False,
        "files": {reviewer: {"name": Path(path).name,
                             "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()}
                  for reviewer, path in files.items()},
    }
    if args.source_crosstab:
        master = jsonl_read(config["master_output"])  # fails loudly if absent; never rebuilt
        results["disagreement_by_stratum"] = stratum_disagreement(master, reviews)
        results["source_adversarial_flag_vs_label_descriptive"] = source_label_crosstab(
            master, reviews)

    out = Path(args.output_dir or config["analysis_output_dir"])
    names = ["agreement_results.json", "agreement_report.md", "disagreement_table.csv"]
    if any((out / name).exists() for name in names):
        raise FileExistsError("Analysis outputs exist; refusing to overwrite")
    out.mkdir(parents=True, exist_ok=True)
    (out / names[0]).write_text(json.dumps(results, indent=2, allow_nan=False) + "\n",
                                encoding="utf-8")
    (out / names[1]).write_text(render_report(results), encoding="utf-8")
    ids = results["reviewers"]
    fields = (["pilot_id", "pattern", "category"] +(["prompt"] if args.include_prompts else [])
              + [f"reviewer_{r}_label" for r in ids] + [f"reviewer_{r}_rationale" for r in ids])
    write_csv(out / names[2], fields, disagreements)
    print(render_report(results))


if __name__ == "__main__":
    main()
