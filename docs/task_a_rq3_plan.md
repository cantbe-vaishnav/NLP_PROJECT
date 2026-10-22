# Task A RQ3: proposed held-out experiment plan (awaiting owner approval)

Date: 2026-10-22. **Nothing has been trained, no split built, model selection unchanged.** Counts below come from
`scripts/preview_rq3_split.py` → `results/task_a_rq3_plan/split_preview.json`.

## What the metadata supports

| Source | Category metadata | Usable for a held-out split? |
|---|---|---|
| WildGuardMix | `subcategory`: 14 **harm topics** (cyberattack, sexual_content, ...) plus `benign` and `others`, on **both** labels | Yes, as an unseen *harm topic*, not an unseen attack *technique* |
| WildGuardMix | no attack-tactic field (the WildJailbreak tactics are not in WildGuardMix) | No |
| JailbreakHub | platform, community, date; no category | Only as an unseen *source* or a time split |

The question "does the detector catch an attack technique it never saw?" is not answerable from the metadata. Any
tactic labels would have to be derived (for example from the cue regexes), and I don't recommend calling a
regex-derived split an unseen-category evaluation. The two experiments below each test one thing the metadata
does support. Neither is a random split.

## Experiment A (recommended): unseen harm category, `cyberattack`

**Why this category.** It is semantically distinct from the other topics (technical intrusion and malware rather
than speech harms). It has both labels in adequate numbers (533 pool rows: 150 adversarial, 383 direct harmful
requests). No near-duplicate family links it to kept rows. Sexual content and private information were also
checked, with similar counts; cyberattack is the most topically separable of the three.

**Leakage control.** The subcategory alone does not hold the topic out: cyber prompts also sit in `others`,
`benign`, fraud and other subcategories, and in JailbreakHub. A strict keyword list (hacking, malware,
ransomware, phishing, keylogger, DDoS, botnet, SQL injection, backdoor, trojan, spyware, zero-day, brute force,
password cracking, cyberattack) removes 1,453 related train/validation rows as well. The keyword list matches
only 69% of the cyberattack rows themselves, so some cyber-topic prompts phrased without these words will
remain in training. The report will state this residual leakage.

| Set | Benign (0) | Adversarial (1) | Use |
|---|---|---|---|
| Train (after removal) | 31,891 | 20,778 | fit |
| Validation (after removal) | 3,690 | 2,324 | model selection only (no cyber rows) |
| **Held-out category test** (cyberattack rows from train+val) | 383 | 150 | primary RQ3 result |
| Held-out category, official test rows | 17 | 31 | seen vs unseen comparison (below) |
| Keyword-related rows removed from training | 484 | 969 | secondary, reported separately (heuristic) |
| Reference: official test without cyberattack | 898 | 779 | in-distribution reference |
| Reference: JailbreakHub test (unchanged) | 1,306 | 141 | cross-source reference |

Label 0 here means "direct (non-adversarial) request", which within this topic is usually harmful. The test
therefore asks whether the model still separates jailbreak framing from direct requests on a topic it has not
seen, which is the binary task's definition.

**Measuring degradation.** (1) On the 48 official-test cyberattack rows, which neither model trained on, compare
the current selected models (category seen in training) with the retrained models (category unseen). This is
the clean comparison, but n=48 is small. (2) For each retrained model, compare macro-F1, adversarial recall and
FPR on the held-out category against the reference official test. Report Wilson or bootstrap intervals.

## Experiment B (recommended as a cheap companion): unseen source, train without JailbreakHub

Train and select on WildGuardMix only (22,397 / 20,606 train, 2,482 / 2,290 validation); evaluate on the
unchanged JailbreakHub test (1,306 / 141) and the official test. WildGuardMix adversarial prompts are
synthetic (WildJailbreak tactics), while JailbreakHub prompts are human-written forum jailbreaks, so this tests
generalisation to unseen *in-the-wild formulations*. 51 near-duplicate families mix the two sources, and none
crosses a split, so there is no leakage from them. It is a source split, not a category split, and will be
reported as such.

## Models, settings and cost

| Model | Why | Settings | Cost per experiment |
|---|---|---|---|
| TF-IDF + Logistic Regression | RQ1 baseline | as RQ1 (C grid 0.1/1/10, validation macro-F1, threshold 0.5) | a few minutes, CPU |
| TF-IDF + Linear SVM | best JailbreakHub macro-F1 in RQ1 | as RQ1 (C grid 0.01–10, threshold 0) | a few minutes, CPU |
| DistilBERT-256 | transformer | as RQ1 (3 epochs max, early stopping on validation, lr 2e-5, bf16) | about 20 min on the RTX 4060 (5.6 min/epoch in RQ1) |

DistilBERT-512 is optional (about 35 min per experiment; one RQ1 epoch took 142 min due to an interruption).
Both experiments with the three models take about 1–1.5 hours, one seed (42). New run folders only; the current
selected runs and `docs/task_a_results.md` selections stay unchanged.

## Outputs after approval

Split-definition JSON (IDs per set, keyword list, hashes), configs, training/evaluation scripts or notebooks
reusing the RQ1 code, `predictions.csv` (Git-ignored), metrics with intervals, plots, error examples, and
`docs/task_a_rq3_report.md`.

## Decisions needed from the owner

1. Approve Experiment A with `cyberattack` (or name another subcategory), including the keyword-closure rule.
2. Approve Experiment B (source held-out) as a companion.
3. Models: LogReg + SVM + DistilBERT-256 (recommended), and whether to add DistilBERT-512.
