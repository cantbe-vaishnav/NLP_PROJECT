# Task A results: adversarial-prompt detection (dataset v2)

All numbers come from saved run artifacts (`results/task_a_binary_*/run_*/metrics.json`,
`run.json`, `predictions.csv`). Positive class = ADVERSARIAL (jailbreak). Model selection used the
validation split only: C for the TF-IDF models, the checkpoint epoch for DistilBERT, and the input
length (256 vs 512 tokens). Both test sets were scored once after selection.

## Data

| Split | WildGuardMix benign / adversarial | JailbreakHub benign / adversarial |
|---|---|---|
| train | 22,397 / 20,606 | 10,271 / 1,183 |
| validation | 2,482 / 2,290 | 1,298 / 142 |
| test_official (WildGuardMix test, unchanged) | 915 / 810 | – |
| test_jailbreakhub | 5 / 0 | 1,301 / 141 |

Near-duplicate families never cross splits, and no test prompt appears in train or validation
(checked in every notebook). JailbreakHub labels include 174 reviewed corrections that are
not human-verified; the remaining JailbreakHub labels are source labels.

## Main results (test sets scored once)

| Model (selected setting) | Run | Val macro-F1 | Official test macro-F1 | Official FPR | JailbreakHub macro-F1 | JailbreakHub recall | JailbreakHub precision | JailbreakHub FPR |
|---|---|---|---|---|---|---|---|---|
| TF-IDF + Logistic Regression (C = 10) | `run_20261021T022858Z` | 0.979 | 0.994 | 0.009 | 0.793 | 0.667 | 0.595 | 0.049 |
| TF-IDF + Linear SVM (C = 1) | `run_20261021T022904Z` | 0.981 | 0.995 | 0.007 | **0.820** | **0.695** | 0.658 | 0.039 |
| DistilBERT, 256 tokens (epoch 2) | `run_20261021T024649Z` | 0.982 | **0.998** | 0.001 | 0.811 | 0.539 | **0.826** | **0.012** |
| DistilBERT, 512 tokens (epoch 2) | `run_20261021T231957Z` | **0.984** | **0.998** | 0.001 | 0.817 | 0.610 | 0.735 | 0.024 |

Test sizes: official 1,725 prompts (810 adversarial); JailbreakHub 1,447 prompts (141 adversarial).
Error counts on the official test: LogReg 11, SVM 8, DistilBERT-256 4, DistilBERT-512 3.
Differences that small are not evidence that one model is better.

## Findings

- **RQ1 (TF-IDF vs DistilBERT):** on the in-distribution official test all models are near
  ceiling (0.994–0.998 macro-F1). On the cross-source JailbreakHub test the models make different
  trade-offs. At default thresholds the SVM finds the most attacks (recall 0.695) and has the best
  macro-F1 (0.820), while DistilBERT flags far fewer benign prompts (FPR 0.012–0.024) but misses
  more attacks. Contextual representations did not, in this setup, produce a clear overall gain.
- **Cross-source gap:** every model loses 0.18–0.20 macro-F1 from the official test to
  JailbreakHub, even though JailbreakHub prompts are also in training. This is the main
  limitation of the detectors.
- **Input length (256 vs 512):** 512 tokens was chosen on validation (0.984 vs 0.982; two
  256-token runs span 0.982–0.982, so the margin is small). On JailbreakHub, 512 tokens raised
  recall (0.539 → 0.610) and doubled FPR (0.012 → 0.024). Truncation at 256 tokens affects
  44% of JailbreakHub test prompts; at 512 tokens, 25%.
- **Overfitting:** TF-IDF models fit JailbreakHub training prompts almost perfectly (train
  macro-F1 0.979–0.987) but reach only 0.826–0.831 on JailbreakHub validation; DistilBERT's
  gap is smaller (0.898 → 0.802 at 256, 0.918 → 0.847 at 512). WildGuardMix gaps are below 0.01.
- **RQ7 (thresholds):** with thresholds chosen on validation for a validation FPR of at most
  5%, JailbreakHub recall rises to 0.766–0.801, but JailbreakHub FPR rises to 0.11–0.13.
  Validation is mostly WildGuardMix, so validation-chosen thresholds transfer poorly to
  JailbreakHub (`notebooks/task_a_threshold_analysis_v2.ipynb`).

Error analysis, hard-negative and unseen-formulation slices: [task_a_error_analysis.md](task_a_error_analysis.md).

## Figures

Drawn from the saved runs above (no retraining), with an interpretation under each chart. Shared colors and
model names: `src/task_a/plotting.py`.

| Figure | Notebook |
|---|---|
| Class balance per split and source | `task_a_error_analysis_v2` |
| Test performance per model (macro-F1, adversarial precision/recall/F1, FPR), one row per test set | `task_a_error_analysis_v2` |
| Cross-dataset macro-F1 gap (official WildGuardMix vs JailbreakHub) | `task_a_error_analysis_v2` |
| Confusion matrices, 4 models × 2 test sets (counts and % of true class, FN/FP marked) | `task_a_error_analysis_v2` |
| Missed vs caught JailbreakHub attacks; RQ2 hard-negative FPR; RQ3 recall by similarity bin | `task_a_error_analysis_v2` |
| RQ7 recall and FPR at the validation-chosen thresholds (validation vs both test sets) | `task_a_threshold_analysis_v2` |

## Status of Task A research questions

| RQ | Status |
|---|---|
| RQ1 TF-IDF vs DistilBERT | Done (table above). |
| RQ2 hard negatives | Partial: a proxy slice of benign test prompts containing jailbreak vocabulary (66 JailbreakHub prompts). A curated hard-negative set (benign text discussing attacks) does not exist yet. |
| RQ3 unseen formulations / categories | Partial: recall by similarity to the closest training prompt (fixed bins). An unseen-category split needs retraining with a held-out category (WildGuardMix has category metadata); not run, requires approval. |
| RQ7 threshold trade-off | Done for validation-chosen operating points. |
| Human annotation pilot | 200 prompts, 3 reviewers, Fleiss' kappa 0.541 (`outputs/annotation_agreement_pilot/recomputed/`). Uses the four-label scheme; no adjudicated gold set; reviewer independence owner-confirmed, not audited. Not used by the binary experiments. |

## Limitations

- Labels are source-defined; JailbreakHub labels are noisy (the error analysis lists 37 label-review candidates).
- One training run per configuration; GPU training is not bit-for-bit reproducible.
- Leakage checks are lexical (TF-IDF cosine, shingles); paraphrased duplicates could remain.
- The official test is near ceiling, so it cannot separate the models.

## Reproduce

Run in VS Code with `C:\Program Files\Python311\python.exe` (or any Python with pandas, scikit-learn,
torch, transformers): `task_a_binary_tfidf_baseline_v2` → `task_a_binary_tfidf_linear_svm_v2` →
`task_a_binary_distilbert_v2` (training, GPU) → `task_a_binary_distilbert_512_v2` (training, GPU) →
`task_a_error_analysis_v2` → `task_a_threshold_analysis_v2`. Each run writes a new timestamped folder.
