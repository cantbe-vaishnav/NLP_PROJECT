"""TF-IDF + Logistic Regression baseline for binary jailbreak detection.

Fits on split == "train" only, chooses C on "validation" macro-F1 (threshold fixed at
0.5), refits nothing on validation, and scores the held-out test splits only when
--evaluate-test is given. Metrics are reported overall and per source. Writes config,
metrics and predictions to a new output directory (predictions are Git-ignored).
The primary interface is notebooks/task_a_binary_tfidf_baseline_v2.ipynb; both use
the shared logic in task_a.tfidf_baseline.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform

from task_a.tfidf_baseline import TEST_SPLITS, group_by_split, load_rows, score_split, select_c, write_run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/task_a_binary_tfidf.json")
    parser.add_argument("--evaluate-test", action="store_true",
                        help="score test_official and test_jailbreakhub once, after selection")
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    out = Path(config["output_dir"])
    if out.exists():
        raise FileExistsError(f"{out} exists; refusing to overwrite")
    rows, digest = load_rows(config["dataset"])
    by_split = group_by_split(rows)
    seed, params, threshold = config["seed"], config["model"], config["threshold"]

    best_c, search, model = select_c(by_split["train"], by_split["validation"], config["c_grid"],
                                     params, seed, threshold)
    splits = ["validation"] + (list(TEST_SPLITS) if args.evaluate_test else [])
    results, predictions = {}, []
    for split in splits:
        results[split], preds = score_split(model, by_split.get(split, []), split, threshold)
        predictions += preds

    import sklearn
    record = {"created_utc": datetime.now(timezone.utc).isoformat(), "config": config,
              "dataset_sha256": digest, "selected_C": best_c, "c_search": search,
              "evaluated_splits": splits, "test_evaluated": args.evaluate_test,
              "versions": {"python": platform.python_version(), "scikit_learn": sklearn.__version__}}
    write_run(out, record, results, predictions)
    print(json.dumps({"selected_C": best_c, "c_search": search,
                      **{s: results[s]["all"] for s in splits}}, indent=2))


if __name__ == "__main__":
    main()
