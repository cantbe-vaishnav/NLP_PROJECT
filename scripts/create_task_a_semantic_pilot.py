"""Create the approved, blind, human semantic-validation pilot."""
import argparse
import csv
import json
from pathlib import Path

import pyarrow.parquet as pq
from task_a.semantic_pilot import sample_unique_strata, write_csv


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/task_a_semantic_pilot.json")
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text())
    outputs = [Path(config[key]) for key in
               ["master_output", "reviewer_1_output", "reviewer_2_output"]]
    if any(path.exists() for path in outputs):
        raise FileExistsError("Pilot outputs exist; refusing to overwrite annotations")
    rows = pq.read_table(config["source_train"]).to_pylist()
    selected, summary = sample_unique_strata(
        rows, config["sample_per_stratum"], config["seed"])
    for path in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)
    outputs[0].write_text("".join(json.dumps(row, ensure_ascii=False) + "\n"
                                  for row in selected), encoding="utf-8")
    fields = ["pilot_id", "prompt", "safellm_label", "reviewer_id", "rationale"]
    blind = [{"pilot_id": row["pilot_id"], "prompt": row["prompt"],
              "safellm_label": "", "reviewer_id": "", "rationale": ""}
             for row in selected]
    write_csv(outputs[1], fields, blind)
    write_csv(outputs[2], fields, blind)
    print(json.dumps({"rows": len(selected), "strata": summary,
                      "blind_files_exclude_source_labels": True}, indent=2))


if __name__ == "__main__":
    main()
