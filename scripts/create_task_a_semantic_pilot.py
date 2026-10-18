"""Create the approved, blind, human semantic-validation pilot."""
import argparse
import json
from pathlib import Path

import pyarrow.parquet as pq
from task_a.semantic_pilot import sample_unique_strata, write_csv


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/task_a_semantic_pilot.json")
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text())
    master_path = Path(config["master_output"])
    reviewer_paths = [Path(path) for path in config["reviewer_worksheets"].values()]
    if any(path.exists() for path in [master_path, *reviewer_paths]):
        raise FileExistsError("Pilot outputs exist; refusing to overwrite annotations")
    rows = pq.read_table(config["source_train"]).to_pylist()
    selected, summary = sample_unique_strata(
        rows, config["sample_per_stratum"], config["seed"])
    for path in [master_path, *reviewer_paths]:
        path.parent.mkdir(parents=True, exist_ok=True)
    master_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n"
                                   for row in selected), encoding="utf-8")
    fields = ["pilot_id", "prompt", "safellm_label", "reviewer_id", "rationale"]
    blind = [{"pilot_id": row["pilot_id"], "prompt": row["prompt"],
              "safellm_label": "", "reviewer_id": "", "rationale": ""}
             for row in selected]
    for path in reviewer_paths:
        write_csv(path, fields, blind)
    print(json.dumps({"rows": len(selected), "strata": summary,
                      "reviewer_files": len(reviewer_paths),
                      "blind_files_exclude_source_labels": True}, indent=2))


if __name__ == "__main__":
    main()
