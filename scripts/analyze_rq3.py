"""RQ3 analysis: compare the held-out retrains with the RQ1 models and summarise their errors (no prompt text).

Reads the latest run per experiment and model under results/task_a_rq3_heldout_*/, the RQ1 predictions of the same
models, and dataset v2. Writes results/task_a_rq3_summary/summary.json, comparison.csv and two figures.
Degradation is measured only on rows that neither model trained on: the official-test cyberattack rows (A) and
the JailbreakHub test (B).
"""

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from preview_rq3_split import KEYWORDS  # noqa: E402
from run_rq3_experiment import EXPERIMENT_DIRS, wilson  # noqa: E402
from task_a.binary_metrics import binary_metrics  # noqa: E402
from task_a.cue_audit import review_priority  # noqa: E402
from task_a.plotting import MODEL_COLORS, TEXT_SECONDARY, apply_style  # noqa: E402

MODELS = {"logreg": "LogReg", "svm": "SVM", "distilbert": "DistilBERT"}
RQ1 = {"logreg": "results/task_a_binary_tfidf_v2/run_20261021T022858Z",
       "svm": "results/task_a_binary_tfidf_linear_svm_v2/run_20261021T022904Z",
       "distilbert": "results/task_a_binary_distilbert_v2/run_20261021T024649Z"}


def summary(gold, pred):
    m = binary_metrics(list(gold), list(pred))
    cm = m["confusion_matrix"]
    return {"n": m["n"], "macro_f1": m["macro_f1"], "accuracy": m["accuracy"],
            "adversarial": m["per_class"]["ADVERSARIAL"], "benign": m["per_class"]["BENIGN"],
            "fpr": m["fpr"], "confusion_matrix": cm,
            "recall_ci95": wilson(cm["tp"], cm["tp"] + cm["fn"]), "fpr_ci95": wilson(cm["fp"], cm["fp"] + cm["tn"])}


def latest(experiment, model):
    runs = sorted((ROOT / EXPERIMENT_DIRS[experiment] / model).glob("run_*/metrics.json"))
    return runs[-1].parent


def main():
    df = pd.read_parquet(ROOT / "data/processed/binary_jailbreak_v2/combined.parquet",
                         columns=["example_id", "text", "label", "source_dataset", "split", "source_metadata"]).set_index("example_id")
    df["subcategory"] = df["source_metadata"].map(lambda s: json.loads(s).get("subcategory"))
    df["has_keyword"] = df["text"].str.contains(KEYWORDS)
    df["has_strong_cue"] = df["text"].map(lambda t: bool(review_priority(t)[1]))
    df["chars"] = df["text"].str.len()
    out = {"runs": {}, "metrics": {}, "rq1_vs_heldout": {}, "errors": {}, "runtime_seconds": {}}
    rows = []
    for experiment in ["A", "B"]:
        for model, name in MODELS.items():
            run = latest(experiment, model)
            record = json.loads((run / "run.json").read_text(encoding="utf-8"))
            pred = pd.read_csv(run / "predictions.csv")
            out["runs"][f"{experiment}|{model}"] = str(run.relative_to(ROOT)).replace("\\", "/")
            out["runtime_seconds"][f"{experiment}|{model}"] = record["runtime_seconds"]
            for set_name, g in pred.groupby("split"):
                s = summary(g["gold"], g["pred"])
                out["metrics"][f"{experiment}|{model}|{set_name}"] = s
                rows.append({"experiment": experiment, "model": name, "set": set_name, "n": s["n"], "macro_f1": s["macro_f1"],
                             "adv_precision": s["adversarial"]["precision"], "adv_recall": s["adversarial"]["recall"],
                             "adv_f1": s["adversarial"]["f1"], "benign_precision": s["benign"]["precision"],
                             "benign_recall": s["benign"]["recall"], "benign_f1": s["benign"]["f1"], "fpr": s["fpr"],
                             **{k: v for k, v in s["confusion_matrix"].items()}})

            # Same rows scored by the RQ1 model (trained with the held-out data) vs the held-out retrain.
            rq1 = pd.read_csv(ROOT / RQ1[model] / "predictions.csv").set_index("example_id")
            shared = {"A": ["heldout_cyberattack_official_test", "official_test_without_cyberattack", "test_jailbreakhub"],
                      "B": ["test_jailbreakhub", "official_test"]}[experiment]
            for set_name in shared:
                g = pred[pred["split"] == set_name].set_index("example_id")
                out["rq1_vs_heldout"][f"{experiment}|{model}|{set_name}"] = {
                    "rq1_seen": summary(g["gold"], rq1.loc[g.index, "pred"]), "heldout": summary(g["gold"], g["pred"]),
                    "prediction_changes": int((rq1.loc[g.index, "pred"] != g["pred"]).sum())}

            # Error profile on the primary held-out set (counts and rates, no text).
            primary = "heldout_cyberattack_pool" if experiment == "A" else "test_jailbreakhub"
            g = pred[pred["split"] == primary].set_index("example_id").join(df[["has_keyword", "has_strong_cue", "chars", "subcategory"]])
            g["error"] = g["gold"] != g["pred"]
            prof = {}
            for label, lg in g.groupby("gold"):
                prof[f"label_{label}"] = {
                    "n": int(len(lg)), "errors": int(lg["error"].sum()),
                    "error_rate_with_keyword": round(float(lg.loc[lg["has_keyword"], "error"].mean()), 4) if lg["has_keyword"].any() else None,
                    "error_rate_without_keyword": round(float(lg.loc[~lg["has_keyword"], "error"].mean()), 4) if (~lg["has_keyword"]).any() else None,
                    "error_rate_with_strong_cue": round(float(lg.loc[lg["has_strong_cue"], "error"].mean()), 4) if lg["has_strong_cue"].any() else None,
                    "error_rate_without_strong_cue": round(float(lg.loc[~lg["has_strong_cue"], "error"].mean()), 4) if (~lg["has_strong_cue"]).any() else None,
                    "median_chars_errors": float(lg.loc[lg["error"], "chars"].median()) if lg["error"].any() else None,
                    "median_chars_correct": float(lg.loc[~lg["error"], "chars"].median()) if (~lg["error"]).any() else None}
            out["errors"][f"{experiment}|{model}|{primary}"] = prof

    # Errors shared by all three held-out models on each primary set.
    for experiment, primary in [("A", "heldout_cyberattack_pool"), ("B", "test_jailbreakhub")]:
        preds = []
        for m in MODELS:
            p = pd.read_csv(latest(experiment, m) / "predictions.csv")
            preds.append(p[p["split"] == primary].set_index("example_id"))
        wrong = sum((p["gold"] != p["pred"]).astype(int) for p in preds)
        out["errors"][f"{experiment}|all_models_wrong"] = {
            "label_1_missed_by_all": int(((preds[0]["gold"] == 1) & (wrong == 3)).sum()),
            "label_0_flagged_by_all": int(((preds[0]["gold"] == 0) & (wrong == 3)).sum())}

    dest = ROOT / "results/task_a_rq3_summary"
    dest.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(dest / "comparison.csv", index=False, float_format="%.4f")
    (dest / "summary.json").write_text(json.dumps(out, indent=2, default=float), encoding="utf-8")

    # Figure: seen (RQ1) vs held-out retrain on the rows neither trained on.
    apply_style()
    panels = [("A", "heldout_cyberattack_official_test", "A: official-test cyberattack rows (n=48)"),
              ("A", "official_test_without_cyberattack", "A: rest of official test (n=1,677)"),
              ("B", "test_jailbreakhub", "B: JailbreakHub test (n=1,447)")]
    for metric, label, fname in [("macro_f1", "Macro-F1", "rq3_macro_f1.png"), ("recall", "Adversarial recall", "rq3_recall.png")]:
        fig, axes = plt.subplots(1, 3, figsize=(13, 3.8), sharey=True)
        for ax, (experiment, set_name, title) in zip(axes, panels):
            for i, (model, name) in enumerate(MODELS.items()):
                pair = out["rq1_vs_heldout"][f"{experiment}|{model}|{set_name}"]
                get = (lambda s: s["macro_f1"]) if metric == "macro_f1" else (lambda s: s["adversarial"]["recall"])
                seen, held = get(pair["rq1_seen"]), get(pair["heldout"])
                ax.plot([i - 0.15, i + 0.15], [seen, held], color=MODEL_COLORS[name], linewidth=2)
                ax.plot(i - 0.15, seen, "o", color=MODEL_COLORS[name], markersize=8, markerfacecolor="white", markeredgewidth=2)
                ax.plot(i + 0.15, held, "o", color=MODEL_COLORS[name], markersize=8, markeredgecolor="white", markeredgewidth=2)
                if metric == "recall":
                    ci = pair["heldout"]["recall_ci95"]
                    ax.plot([i + 0.15, i + 0.15], ci, color=MODEL_COLORS[name], linewidth=1, alpha=0.6)
            ax.set_xticks(range(len(MODELS)))
            ax.set_xticklabels(["TF-IDF LogReg", "TF-IDF SVM", "DistilBERT-256"])
            ax.set_title(title, fontsize=10)
        axes[0].set_ylabel(label)
        fig.text(0.5, 0.005, "Hollow dot: RQ1 model (held-out data seen in training). Filled dot: held-out retrain"
                 + (" (line: 95% Wilson interval)." if metric == "recall" else "."), ha="center", fontsize=8, color=TEXT_SECONDARY)
        fig.tight_layout(rect=(0, 0.05, 1, 1))
        fig.savefig(dest / fname, dpi=150)
    print(json.dumps({k: v for k, v in out.items() if k in ("runtime_seconds", "errors")}, indent=1, default=float))


if __name__ == "__main__":
    main()
