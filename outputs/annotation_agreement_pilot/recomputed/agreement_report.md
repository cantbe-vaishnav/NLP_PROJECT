# Task A pilot: observed agreement among submitted annotations

Label schema (canonical, four labels kept separate): BENIGN, HARMFUL, ADVERSARIAL, QUARANTINE.
Items: 200. Reviewers: 1, 2, 3.

**Limitation.** Reviewer independence has not been verified. Reviewer 1's rationales contain review-dialogue language, Reviewer 2's rationales are repeated generic sentences, and file timestamps alone do not establish independence. These figures describe observed agreement among the submitted annotations, not independent inter-annotator reliability, and not agreement with any source-dataset label.

**Inputs.** The reviewer annotation files are external to the repository (annotation files are Git-ignored licensed data). These results cannot be reproduced from the repository alone; the files analysed are identified by SHA-256:

- Reviewer 1: `task_a_pilot_reviewer_1_FINAL.csv` `be6ac33ee823fd7a6dbbea11854f15cf5d9039a0e650a4920dbac38e7fe3f35e`
- Reviewer 2: `reviewer2_corrected.xlsx` `34b8fdac00becf607a41a1306ba34829c58c78dad1b245ec0a472eb73f72f6c3`
- Reviewer 3: `reviewer3_corrected.xlsx` `18d26d52563e61db2b25b303f09655fb495a479ba8bd436d5b7ea7348515eef0`

## Label distributions

| Reviewer | BENIGN | HARMFUL | ADVERSARIAL | QUARANTINE | QUARANTINE rate |
|---|---|---|---|---|---|
| 1 | 102 | 47 | 46 | 5 | 2.5% |
| 2 | 91 | 57 | 41 | 11 | 5.5% |
| 3 | 104 | 26 | 47 | 23 | 11.5% |

## Pairwise agreement

| Pair | Raw agreement | Rate | Cohen's kappa |
|---|---|---|---|
| 1-2 | 161/200 | 0.8050 | 0.7011 |
| 1-3 | 129/200 | 0.6450 | 0.4516 |
| 2-3 | 130/200 | 0.6500 | 0.4791 |

Fleiss' kappa (3 reviewers): **0.5412**

## Agreement patterns

| Pattern | Items | Rate |
|---|---|---|
| unanimous | 115 | 0.5750 |
| two_vs_one | 75 | 0.3750 |
| three_way | 10 | 0.0500 |

## Confusion matrix: reviewer 1 (rows) vs reviewer 2 (columns)

| | BENIGN | HARMFUL | ADVERSARIAL | QUARANTINE |
|---|---|---|---|---|
| BENIGN | 84 | 7 | 5 | 6 |
| HARMFUL | 0 | 42 | 2 | 3 |
| ADVERSARIAL | 7 | 6 | 33 | 0 |
| QUARANTINE | 0 | 2 | 1 | 2 |

## Confusion matrix: reviewer 1 (rows) vs reviewer 3 (columns)

| | BENIGN | HARMFUL | ADVERSARIAL | QUARANTINE |
|---|---|---|---|---|
| BENIGN | 85 | 3 | 8 | 6 |
| HARMFUL | 3 | 20 | 16 | 8 |
| ADVERSARIAL | 14 | 3 | 22 | 7 |
| QUARANTINE | 2 | 0 | 1 | 2 |

## Confusion matrix: reviewer 2 (rows) vs reviewer 3 (columns)

| | BENIGN | HARMFUL | ADVERSARIAL | QUARANTINE |
|---|---|---|---|---|
| BENIGN | 84 | 1 | 2 | 4 |
| HARMFUL | 3 | 22 | 22 | 10 |
| ADVERSARIAL | 11 | 3 | 21 | 6 |
| QUARANTINE | 6 | 0 | 2 | 3 |

Per-item disagreements (85 rows) are in the accompanying disagreement table; none have been adjudicated.
