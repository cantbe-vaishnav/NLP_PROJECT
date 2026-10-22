# Task A error analysis (dataset v2, four models)

Descriptive analysis of the saved test predictions of the latest runs: TF-IDF + Logistic Regression
`run_20261021T022858Z`, TF-IDF + Linear SVM `run_20261021T022904Z`, DistilBERT-256
`run_20261021T024649Z`, DistilBERT-512 `run_20261021T231957Z`. Produced by
`notebooks/task_a_error_analysis_v2.ipynb` (executed, outputs saved). No model was trained or
tuned and no threshold was chosen here.

## Errors

| Test set | Model | Missed attacks | Benign flagged |
|---|---|---|---|
| Official WildGuardMix (810 attacks / 915 benign) | LogReg | 3 | 8 |
| | SVM | 2 | 6 |
| | DistilBERT-256 | 3 | 1 |
| | DistilBERT-512 | 2 | 1 |
| JailbreakHub (141 / 1,306) | LogReg | 47 | 64 |
| | SVM | 43 | 51 |
| | DistilBERT-256 | 65 | 16 |
| | DistilBERT-512 | 55 | 31 |

36 of 141 JailbreakHub attacks are missed by all four models (83% of them contain no strong
jailbreak cue); 9 JailbreakHub benign prompts are flagged by all four.

## Missed JailbreakHub attacks: missed vs caught

| Model | Median tokens | Over 256 tokens | No strong cue | Cue after token 255 | Median similarity to training |
|---|---|---|---|---|---|
| LogReg | 210 vs 504 | 47% vs 80% | 74% vs 17% | 4% vs 10% | 0.22 vs 0.38 |
| SVM | 192 vs 454 | 47% vs 79% | 74% vs 19% | 5% vs 9% | 0.24 vs 0.38 |
| DistilBERT-256 | 300 vs 540 | 58% vs 78% | 68% vs 9% | 8% vs 8% | 0.24 vs 0.41 |
| DistilBERT-512 | 294 vs 412 | 53% vs 79% | 73% vs 13% | 11% vs 6% | 0.24 vs 0.39 |

"Strong cue" uses the patterns in `task_a/cue_audit.py`; similarity is TF-IDF cosine to the
closest training prompt.

- Missed attacks are shorter, not longer, than caught attacks for every model.
- For DistilBERT-256, a cue appearing only after the 256-token cut is equally rare among missed and
  caught attacks (8% each), so truncation does not explain most misses. The 512-token model
  misses fewer attacks (55 vs 65) but flags more benign prompts (31 vs 16).
- Missed attacks mostly lack familiar jailbreak wording (68–74% have no strong cue) and are less
  similar to training prompts. This is consistent with unfamiliar formulations, not proof of cause.

## RQ2 proxy: benign prompts with jailbreak vocabulary

| Test set | Benign prompts | LogReg FPR | SVM FPR | DistilBERT-256 FPR | DistilBERT-512 FPR |
|---|---|---|---|---|---|
| JailbreakHub, no strong cue | 1,240 | 0.035 | 0.026 | 0.005 | 0.009 |
| JailbreakHub, with strong cue | 66 | 0.303 | 0.288 | 0.152 | 0.303 |
| Official, no strong cue | 915 | 0.009 | 0.007 | 0.001 | 0.001 |

Benign prompts that use jailbreak vocabulary are flagged 4–30 times more often. The slice is small
(66 prompts), has noisy labels, and is not a curated hard-negative set; the official test has no
benign prompts with strong cues.

## RQ3 proxy: recall by similarity to training (fixed bins)

| Test set | Similarity | Attacks | LogReg | SVM | DistilBERT-256 | DistilBERT-512 |
|---|---|---|---|---|---|---|
| JailbreakHub | low (< 0.2) | 51 | 0.569 | 0.627 | 0.431 | 0.529 |
| | medium (0.2–0.4) | 33 | 0.636 | 0.606 | 0.485 | 0.545 |
| | high (≥ 0.4) | 57 | 0.772 | 0.807 | 0.667 | 0.719 |
| Official WildGuardMix | low (< 0.2) | 708 | 0.997 | 0.997 | 0.997 | 0.999 |
| | medium (0.2–0.4) | 99 | 1.000 | 1.000 | 1.000 | 1.000 |

On JailbreakHub, recall drops for attacks worded unlike any training prompt. On WildGuardMix,
low lexical similarity does not hurt, which suggests the models learned WildGuardMix's own attack
style rather than lexical overlap. Bins with 3 or fewer prompts are omitted here.

## Differences between the test sources

Official WildGuardMix benign prompts are short (median 19 tokens) and never contain strong cues;
JailbreakHub benign prompts are long role-play or template prompts (median 196 tokens). Official
attacks rarely contain cue words (95% none) yet are recognized.

## Label-review candidates

37 JailbreakHub prompts: 30 attacks missed by all four models with no strong cue, and 7 benign
prompts flagged by all four that contain a strong cue. One had been reviewed before. Reading short
excerpts, some benign-labelled candidates contain classic "DAN / do anything now" setups, some
attack-labelled candidates read like ordinary role-play cards or templates, and others look like
real attacks the cue patterns miss (leetspeak, emoji or Unicode obfuscation, new override wording).
Model predictions are not evidence of the true label and no label was changed. All 37 have since been
inspected in a model-assisted review (not human-verified); recommendations are in
[task_a_label_review_report.md](task_a_label_review_report.md). The notebook writes their text to the Git-ignored
`results/error_analysis/task_a_v2_<timestamp>/label_review_candidates.csv`.

## What this cannot establish

- Cause: these are associations within one test set.
- Where the malicious instruction sits: cue position is a proxy; prompts without cues have none.
- True labels: most JailbreakHub labels are unreviewed source labels; the 174 applied corrections were
  verified by the project owner.
- Significance on the official test: a handful of errors per model.
