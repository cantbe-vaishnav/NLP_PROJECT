"""RQ2 analysis of a saved hard-negative run: AUROC, representative false positives and the two report figures.

Usage: python scripts/analyze_hard_negatives.py results/task_a_rq2_hard_negatives/run_<timestamp>
Reads the run's predictions.csv and metrics.json and the frozen set's text; writes analysis.json,
false_positives.md (synthetic and NotInject prompts only; no licensed JailbreakHub text) and two PNGs.
"""

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from task_a.plotting import MODEL_COLORS, MODEL_LABELS, SEQUENTIAL, TEXT_SECONDARY, apply_style  # noqa: E402

MODELS = ["LogReg", "SVM", "DistilBERT", "DistilBERT-512"]


def main(run_dir):
    run_dir = Path(run_dir)
    pred = pd.read_csv(run_dir / "predictions.csv")
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "results/task_a_rq2_hard_negatives/build_manifest.json").read_text(encoding="utf-8"))
    text = pd.read_parquet(ROOT / manifest["output"], columns=["example_id", "text"]).set_index("example_id")["text"]
    pred["text"] = pred["example_id"].map(text)
    synth = pred[pred["component"] == "synthetic_v1"]

    # Threshold-free separation on the synthetic set, and how many models flag each benign prompt.
    analysis = {"synthetic_v1_auroc": {m: round(float(roc_auc_score(synth["label"], synth[f"{m}_score"])), 4) for m in MODELS}}
    pred["models_flagging"] = pred[[f"{m}_pred" for m in MODELS]].sum(axis=1)
    benign = pred[pred["label"] == 0]
    analysis["benign_flagged_by_k_models"] = {c: g["models_flagging"].value_counts().sort_index().to_dict()
                                              for c, g in benign.groupby("component")}
    adv = synth[synth["label"] == 1]
    analysis["adversarial_missed_by_all"] = int((adv[[f"{m}_pred" for m in MODELS]].sum(axis=1) == 0).sum())
    analysis["synthetic_median_chars_by_label"] = synth.assign(n=synth["text"].str.len()).groupby("label")["n"].median().to_dict()
    (run_dir / "analysis.json").write_text(json.dumps(analysis, indent=2, default=int), encoding="utf-8")

    # Representative false positives: benign prompts flagged by at least three of the four models.
    lines = ["# RQ2 representative false positives", "",
             "Benign prompts flagged by at least 3 of 4 models. Synthetic items are LLM-authored; NotInject is MIT-licensed.", ""]
    for _, r in benign[benign["models_flagging"] >= 3].sort_values(["component", "category"]).iterrows():
        flags = ", ".join(m for m in MODELS if r[f"{m}_pred"] == 1)
        lines += [f"## `{r['example_id']}` ({r['category']}; flagged by {flags})", "", "> " + r["text"].replace("\n", "\n> "), ""]
    (run_dir / "false_positives.md").write_text("\n".join(lines), encoding="utf-8")

    apply_style()
    # Figure 1: false-positive rate per benign slice and model, with 95% Wilson intervals.
    ref = metrics["reference_saved_test_benign"]
    slices = [("Official WildGuardMix test, no cue", lambda m: ref["test_official|no_cue"][m]),
              ("JailbreakHub test, no cue", lambda m: ref["test_jailbreakhub|no_cue"][m]),
              ("JailbreakHub proxy slice (with cue)", lambda m: ref["test_jailbreakhub|with_cue"][m]),
              ("NotInject (English)", lambda m: metrics["models"][m]["notinject_fpr_english"]),
              ("Synthetic hard negatives, no cue", lambda m: metrics["models"][m]["synthetic_v1_benign_fpr_by_strong_cue"]["False"]),
              ("Synthetic hard negatives, with cue", lambda m: metrics["models"][m]["synthetic_v1_benign_fpr_by_strong_cue"]["True"])]
    fig, ax = plt.subplots(figsize=(9.5, 5))
    offsets = np.linspace(-0.27, 0.27, len(MODELS))
    for k, m in enumerate(MODELS):
        for i, (_, get) in enumerate(slices):
            r = get(m)
            y = len(slices) - 1 - i + offsets[k]
            ax.plot(r["ci95"], [y, y], color=MODEL_COLORS[m], linewidth=2, solid_capstyle="round")
            ax.plot(r["rate"], y, "o", color=MODEL_COLORS[m], markersize=8, markeredgecolor="white", markeredgewidth=2,
                    label=MODEL_LABELS[m] if i == 0 else None)
    ax.set_yticks(range(len(slices)))
    ax.set_yticklabels([f"{name} (n={get('LogReg')['n']})" for name, get in reversed(slices)])
    ax.set_xlabel("False-positive rate (benign prompts flagged as adversarial), 95% Wilson interval")
    ax.grid(axis="x"); ax.grid(axis="y", visible=False)
    ax.set_xlim(0, None)
    ax.legend(loc="lower right")
    ax.set_title("False positives by benign slice and model")
    fig.tight_layout()
    fig.savefig(run_dir / "fpr_by_slice.png", dpi=150)

    # Figure 2: per-category FPR on synthetic benign prompts and recall on their adversarial counterparts.
    cats = ["EDU", "SEC", "CLS", "POL", "MIT", "DOC", "ROL", "META"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    for ax, key, title in [(axes[0], "synthetic_v1_benign_fpr_by_category", "Benign: false-positive rate (n=30 each)"),
                           (axes[1], "synthetic_v1_adversarial_recall_by_category", "Adversarial counterparts: recall (n=10 each)")]:
        grid = np.array([[metrics["models"][m][key][c]["rate"] for c in cats] for m in MODELS])
        ax.imshow(grid, cmap=SEQUENTIAL, vmin=0, vmax=1, aspect="auto")
        for i in range(len(MODELS)):
            for j in range(len(cats)):
                ax.text(j, i, f"{grid[i, j]:.2f}", ha="center", va="center", fontsize=9,
                        color="white" if grid[i, j] > 0.55 else "#1b1b1a")
        ax.set_xticks(range(len(cats))); ax.set_xticklabels(cats)
        ax.set_yticks(range(len(MODELS))); ax.set_yticklabels([MODEL_LABELS[m] for m in MODELS])
        ax.grid(False); ax.set_title(title)
        for spine in ax.spines.values():
            spine.set_visible(False)
    fig.text(0.5, 0.01, "Synthetic, LLM-authored prompts; small cells (n=10-30), read with the intervals in metrics.json.",
             ha="center", fontsize=8, color=TEXT_SECONDARY)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(run_dir / "synthetic_by_category.png", dpi=150)
    print(json.dumps(analysis, indent=2, default=int))


if __name__ == "__main__":
    main(sys.argv[1])
