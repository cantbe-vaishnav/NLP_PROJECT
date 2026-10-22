# Task A error analysis (dataset v2, three models)

Descriptive analysis of the saved test predictions of the latest runs:
TF-IDF + Logistic Regression `run_20261021T022858Z`, TF-IDF + Linear SVM `run_20261021T022904Z`,
DistilBERT (256 tokens) `run_20261021T024649Z`. Numbers below come from running the code of
`notebooks/task_a_error_analysis_v2.ipynb` on those files; no model was trained or tuned and no
threshold was chosen. Rerun the notebook to regenerate them.

## Errors

| Test set | Model | Missed attacks | Benign flagged |
|---|---|---|---|
| Official WildGuardMix (810 attacks / 915 benign) | LogReg | 3 | 8 |
| | SVM | 2 | 6 |
| | DistilBERT | 3 | 1 |
| JailbreakHub (141 / 1,306) | LogReg | 47 | 64 |
| | SVM | 43 | 51 |
| | DistilBERT | 65 | 16 |

37 of 141 JailbreakHub attacks are missed by all three models; 10 JailbreakHub benign prompts are
flagged by all three. On the official test no prompt is wrong for all three models except one benign prompt.

## Missed JailbreakHub attacks: missed vs caught

| Model | Median tokens | Over 256 tokens | No strong cue | Cue after token 255 | Median similarity to training |
|---|---|---|---|---|---|
| LogReg | 210 vs 504 | 47% vs 80% | 74% vs 17% | 4% vs 10% | 0.22 vs 0.38 |
| SVM | 192 vs 454 | 47% vs 79% | 74% vs 19% | 5% vs 9% | 0.24 vs 0.38 |
| DistilBERT | 300 vs 540 | 58% vs 78% | 68% vs 9% | 8% vs 8% | 0.24 vs 0.41 |

"Strong cue" uses the existing `task_a/cue_audit.py` patterns; similarity is TF-IDF cosine to the
closest training prompt.

- Missed attacks are **shorter**, not longer, than caught attacks for all three models.
- For DistilBERT, a cue appearing only after the 256-token cut is equally rare among missed and
  caught attacks (8% each). Truncation therefore does not explain most DistilBERT misses in this
  test set; whether 512 tokens helps still has to be measured.
- Missed attacks mostly lack the familiar jailbreak wording (68–74% have no strong cue) and are
  less similar to anything in training. This points to unfamiliar formulations.

## Benign prompts flagged

Flagged benign prompts are longer (median 337–384 tokens vs about 190) and far more often contain a
strong jailbreak cue (31–63% vs about 4%) than benign prompts the models pass.

## Differences between the test sources

Official WildGuardMix benign prompts are short (median 19 tokens) and contain no strong cues;
JailbreakHub benign prompts are long role-play or template prompts (median 196 tokens). Official
attacks rarely contain cue words (95% none) yet are recognized, so the models learned WildGuardMix's
own style rather than general jailbreak wording.

## Label-review candidates

38 JailbreakHub prompts (31 attacks missed by all three with no strong cue; 7 benign prompts flagged
by all three that contain a strong cue). Only one had been reviewed before. Reading short excerpts:

- Several benign-labelled candidates contain a classic "DAN / do anything now" setup or an amoral,
  rule-free persona, which matches the jailbreak definition.
- Several attack-labelled candidates read like ordinary role-play character cards, marketing
  templates, a text adventure or a résumé assistant.
- Other attack-labelled candidates look like genuine attacks the cue patterns miss: leetspeak,
  emoji or Unicode small-caps obfuscation, and override wording such as "ignore all instructions
  you've received before".

These are candidates for human review only. The models' predictions are not evidence of the true
label, and no label was changed. Text is in the Git-ignored
`results/error_analysis/task_a_v2_<timestamp>/label_review_candidates.csv` written by the notebook.

## What this cannot establish

- Cause: these are associations within one test set.
- Where the malicious instruction sits: cue position is a proxy; prompts without cues have no position.
- True labels: JailbreakHub labels are source-defined; 174 corrections are reviewed but not
  human-verified, and the rest are unreviewed.
- Statistical significance: official-test differences are a handful of errors (11, 8 and 4).
