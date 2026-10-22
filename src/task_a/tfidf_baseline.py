"""TF-IDF + Logistic Regression baseline for binary jailbreak detection (shared logic).

Used by `scripts/train_binary_tfidf.py` and `notebooks/task_a_binary_tfidf_baseline_v2.ipynb`.
Protocol: fit on split == "train" only; choose C by validation macro-F1 at a fixed
threshold; refit the selected C on train; score test splits only after selection.
"""
import csv
import hashlib
import json
from pathlib import Path

import pyarrow.parquet as pq

from task_a.binary_metrics import binary_metrics

TEST_SPLITS = ("test_official", "test_jailbreakhub")
COLUMNS = ["example_id", "text", "label", "source_dataset", "split"]


def load_rows(path, columns=COLUMNS):
    """Read the dataset and return (rows, SHA-256 of the file)."""
    path = Path(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return pq.read_table(path, columns=columns).to_pylist(), digest


def group_by_split(rows):
    by_split = {}
    for r in rows:
        by_split.setdefault(r["split"], []).append(r)
    return by_split


def fit(texts, labels, c, params, seed):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    model = make_pipeline(
        TfidfVectorizer(ngram_range=tuple(params["ngram_range"]), min_df=params["min_df"],
                        sublinear_tf=True, lowercase=True),
        LogisticRegression(C=c, class_weight=params["class_weight"], max_iter=params["max_iter"],
                           solver="liblinear", random_state=seed))
    return model.fit(texts, labels)


def evaluate(rows, scores, threshold):
    """Metrics overall and per source, plus thresholded predictions."""
    pred = [int(s >= threshold) for s in scores]
    gold = [r["label"] for r in rows]
    out = {"all": binary_metrics(gold, pred)}
    for source in sorted({r["source_dataset"] for r in rows}):
        idx = [i for i, r in enumerate(rows) if r["source_dataset"] == source]
        out[source] = binary_metrics([gold[i] for i in idx], [pred[i] for i in idx])
    return out, pred


def select_c(train, validation, c_grid, params, seed, threshold):
    """Grid search over C using validation macro-F1 only; ties go to the smaller C.

    Returns (selected C, search table, model refitted on train with the selected C).
    """
    texts, labels = [r["text"] for r in train], [r["label"] for r in train]
    search = []
    for c in c_grid:
        model = fit(texts, labels, c, params, seed)
        metrics, _ = evaluate(validation, model.predict_proba([r["text"] for r in validation])[:, 1],
                              threshold)
        search.append({"C": c, "validation_macro_f1": metrics["all"]["macro_f1"]})
    best_c = max(search, key=lambda s: (s["validation_macro_f1"], -s["C"]))["C"]
    return best_c, search, fit(texts, labels, best_c, params, seed)


def score_split(model, rows, split, threshold):
    """Metrics and per-row prediction records for one split."""
    scores = model.predict_proba([r["text"] for r in rows])[:, 1]
    metrics, pred = evaluate(rows, scores, threshold)
    predictions = [{"example_id": r["example_id"], "split": split, "gold": r["label"],
                    "score": round(float(s), 6), "pred": p} for r, s, p in zip(rows, scores, pred)]
    return metrics, predictions


def write_run(out, record, results, predictions, model=None):
    """Write run.json, metrics.json, predictions.csv (and model.joblib) to a new directory."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    (out / "run.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    (out / "metrics.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    with open(out / "predictions.csv", "x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["example_id", "split", "gold", "score", "pred"])
        writer.writeheader()
        writer.writerows(predictions)
    if model is not None:
        import joblib
        joblib.dump(model, out / "model.joblib")
