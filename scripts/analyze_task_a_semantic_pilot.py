"""Validate completed independent reviews and create analysis/adjudication files."""
import argparse
import json
from pathlib import Path

from task_a.semantic_pilot import analyze, jsonl_read, read_annotations, write_csv


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/task_a_semantic_pilot.json")
    parser.add_argument("--reviewer-1-id", required=True)
    parser.add_argument("--reviewer-2-id", required=True)
    args = parser.parse_args()
    if args.reviewer_1_id == args.reviewer_2_id:
        raise ValueError("Reviewers must have distinct IDs")
    config = json.loads(Path(args.config).read_text())
    master = jsonl_read(config["master_output"])
    expected_ids = [row["pilot_id"] for row in master]
    review_a = read_annotations(config["reviewer_1_output"], expected_ids, args.reviewer_1_id)
    review_b = read_annotations(config["reviewer_2_output"], expected_ids, args.reviewer_2_id)
    results, queue = analyze(master, review_a, review_b)
    result_path, queue_path = Path(config["results_output"]), Path(config["adjudication_output"])
    if result_path.exists() or queue_path.exists():
        raise FileExistsError("Analysis outputs exist; refusing to overwrite")
    result_path.parent.mkdir(parents=True, exist_ok=True)
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(results, indent=2, allow_nan=False) + "\n")
    fields = ["pilot_id", "prompt", "reviewer_1_label", "reviewer_1_rationale",
              "reviewer_2_label", "reviewer_2_rationale", "adjudicated_label",
              "adjudicator_id", "adjudication_rationale"]
    write_csv(queue_path, fields, queue)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
