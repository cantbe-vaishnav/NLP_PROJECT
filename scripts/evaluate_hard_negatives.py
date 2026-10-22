"""RQ2: score the frozen hard-negative set with the four selected Task A models (saved checkpoints, no retraining).

Inference matches the training notebooks: TF-IDF LogReg P(adversarial) >= 0.5; TF-IDF linear SVM decision value >= 0;
DistilBERT softmax P(adversarial) >= 0.5 with truncation at the run's max_length. Before scoring the new set, each
model re-scores 300 JailbreakHub test prompts and must match its saved predictions. Writes a timestamped run folder
under results/task_a_rq2_hard_negatives/ with metrics.json, predictions.csv (Git-ignored) and figures.
"""

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer, DataCollatorWithPadding

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from task_a.binary_metrics import binary_metrics  # noqa: E402

RUNS = {"LogReg": ("results/task_a_binary_tfidf_v2/run_20261021T022858Z", "proba", 0.5),
        "SVM": ("results/task_a_binary_tfidf_linear_svm_v2/run_20261021T022904Z", "decision", 0.0),
        "DistilBERT": ("results/task_a_binary_distilbert_v2/run_20261021T024649Z", "bert", 0.5),
        "DistilBERT-512": ("results/task_a_binary_distilbert_512_v2/run_20261021T231957Z", "bert", 0.5)}
RESULTS = ROOT / "results/task_a_rq2_hard_negatives"
ERROR_FEATURES = ROOT / "results/error_analysis/task_a_v2_20261022T040723Z/test_error_features.csv"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def wilson(k, n, z=1.96):
    """95% Wilson interval for a proportion k/n."""
    if n == 0:
        return [None, None]
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(float(centre - half), 4), round(float(centre + half), 4)]


def rate(pred):
    """Share flagged as adversarial with its Wilson interval."""
    k, n = int(pred.sum()), int(len(pred))
    return {"n": n, "flagged": k, "rate": round(k / n, 4) if n else None, "ci95": wilson(k, n)}


class Scorer:
    """Loads one saved model and returns its score for a list of texts, as in the training notebooks."""

    def __init__(self, run, kind, device):
        self.kind, self.device = kind, device
        if kind in ("proba", "decision"):
            self.model = joblib.load(ROOT / run / "model.joblib")
        else:
            config = json.loads((ROOT / run / "run.json").read_text(encoding="utf-8"))["config"]
            self.max_length = config["max_length"]
            self.tokenizer = AutoTokenizer.from_pretrained(ROOT / run / "model")
            self.model = AutoModelForSequenceClassification.from_pretrained(ROOT / run / "model").to(device).eval()
            self.collate = DataCollatorWithPadding(self.tokenizer)
            self.bf16 = device.type == "cuda" and torch.cuda.is_bf16_supported()

    @torch.no_grad()
    def __call__(self, texts):
        if self.kind == "proba":
            return self.model.predict_proba(texts)[:, 1]
        if self.kind == "decision":
            return self.model.decision_function(texts)
        encoded = self.tokenizer(list(texts), truncation=True, max_length=self.max_length)
        rows = [{"input_ids": i, "attention_mask": m} for i, m in zip(encoded["input_ids"], encoded["attention_mask"])]
        scores = []
        for start in range(0, len(rows), 64):
            batch = {k: v.to(self.device) for k, v in self.collate(rows[start:start + 64]).items()}
            with torch.autocast(device_type=self.device.type, dtype=torch.bfloat16, enabled=self.bf16):
                logits = self.model(**batch).logits
            scores += torch.softmax(logits.float(), dim=-1)[:, 1].tolist()
        return np.array(scores)


def main():
    manifest = json.loads((RESULTS / "build_manifest.json").read_text(encoding="utf-8"))
    data_path = ROOT / manifest["output"]
    assert sha256(data_path) == manifest["output_sha256"], "hard-negative set differs from the frozen manifest"
    data = pd.read_parquet(data_path)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Reproduction check on JailbreakHub test prompts (saved predictions vs re-scored now).
    ds = pd.read_parquet(ROOT / "data/processed/binary_jailbreak_v2/combined.parquet", columns=["example_id", "text", "split"])
    check = ds[ds["split"] == "test_jailbreakhub"].sample(300, random_state=42)
    reproduction = {}
    for model, (run, kind, threshold) in RUNS.items():
        scorer = Scorer(run, kind, device)
        saved = pd.read_csv(ROOT / run / "predictions.csv").set_index("example_id").loc[check["example_id"]]
        now = scorer(check["text"].tolist())
        reproduction[model] = {"pred_agreement": float(((now >= threshold).astype(int) == saved["pred"].values).mean()),
                               "max_abs_score_diff": float(np.abs(now - saved["score"].values).max())}
        data[f"{model}_score"] = scorer(data["text"].tolist())
        data[f"{model}_pred"] = (data[f"{model}_score"] >= threshold).astype(int)
        del scorer
        torch.cuda.empty_cache()
    print("reproduction:", json.dumps(reproduction, indent=1))
    assert all(r["pred_agreement"] == 1.0 for r in reproduction.values()), "inference does not reproduce saved predictions"

    models = list(RUNS)
    synth = data[data["component"] == "synthetic_v1"]
    benign_synth = synth[synth["label"] == 0]
    notinject = data[data["component"] == "notinject"]
    metrics = {"dataset_sha256": manifest["output_sha256"], "reproduction_check": reproduction, "models": {}}
    for m in models:
        out = {"synthetic_v1_all": binary_metrics(synth["label"].tolist(), synth[f"{m}_pred"].tolist()),
               "synthetic_v1_benign_fpr": rate(benign_synth[f"{m}_pred"]),
               "synthetic_v1_adversarial_recall": rate(synth.loc[synth["label"] == 1, f"{m}_pred"]),
               "synthetic_v1_benign_fpr_by_category": {c: rate(g[f"{m}_pred"]) for c, g in benign_synth.groupby("category")},
               "synthetic_v1_adversarial_recall_by_category": {c: rate(g[f"{m}_pred"]) for c, g in
                                                               synth[synth["label"] == 1].groupby("category")},
               "synthetic_v1_benign_fpr_by_strong_cue": {str(k): rate(g[f"{m}_pred"]) for k, g in benign_synth.groupby("has_strong_cue")},
               "notinject_fpr": rate(notinject[f"{m}_pred"]),
               "notinject_fpr_english": rate(notinject.loc[~notinject["multilingual"], f"{m}_pred"]),
               "notinject_fpr_by_category": {c: rate(g[f"{m}_pred"]) for c, g in notinject.groupby("category")},
               "notinject_fpr_by_trigger_count": {s: rate(g[f"{m}_pred"]) for s, g in notinject.groupby("structure")}}
        # Matched pairs: both items of a designed pair classified correctly.
        pairs = synth[synth["label"] == 1][["example_id", "pair_id", f"{m}_pred"]].merge(
            synth[["example_id", f"{m}_pred"]].rename(columns={"example_id": "pair_id", f"{m}_pred": "hn_pred"}), on="pair_id")
        out["synthetic_v1_pairs_both_correct"] = rate((pairs[f"{m}_pred"] == 1) & (pairs["hn_pred"] == 0))
        metrics["models"][m] = out

    # Reference slices from the saved test predictions (same definitions as the error-analysis notebook).
    feats = pd.read_csv(ERROR_FEATURES)
    benign = feats[feats["label"] == 0].assign(has_cue=lambda f: f["first_cue_token"].notna())
    reference = {}
    for (split, has_cue), g in benign.groupby(["split", "has_cue"]):
        reference[f"{split}|{'with_cue' if has_cue else 'no_cue'}"] = {m: rate(g[m]) for m in models}
    metrics["reference_saved_test_benign"] = reference

    run_dir = RESULTS / datetime.now(timezone.utc).strftime("run_%Y%m%dT%H%M%SZ")
    run_dir.mkdir(parents=True)
    keep = ["example_id", "component", "category", "structure", "label", "pair_id", "has_strong_cue", "multilingual",
            "closest_train_similarity"] + [f"{m}_{k}" for m in models for k in ("score", "pred")]
    data[keep].to_csv(run_dir / "predictions.csv", index=False)
    (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (run_dir / "run.json").write_text(json.dumps({
        "created_utc": datetime.now(timezone.utc).isoformat(), "script": "scripts/evaluate_hard_negatives.py",
        "runs": {m: r[0] for m, r in RUNS.items()}, "thresholds": {m: r[2] for m, r in RUNS.items()},
        "device": str(device), "versions": {"torch": torch.__version__}}, indent=2), encoding="utf-8")
    print("saved to", run_dir.relative_to(ROOT))


if __name__ == "__main__":
    main()
