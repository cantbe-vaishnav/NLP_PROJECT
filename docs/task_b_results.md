# Task B results: claim verification against evidence (FEVER)

Labels: SUPPORTED, CONTRADICTED, UNSUPPORTED. All numbers come from saved runs under
`outputs/task_b/` (Git-ignored; regenerate with the notebooks). Every cutoff was chosen on a
validation sample drawn from FEVER `train.jsonl`; the test set (FEVER `shared_task_dev.jsonl`) was
scored once per run. NLI uses `FacebookAI/roberta-large-mnli` (commit `2a8f12d2`, MIT; weights
checked against the published SHA-256), with evidence as premise and claim as hypothesis, labels
read from the model config, and no tuned threshold. Sections 1–2 use it zero-shot; Section 3
fine-tunes it for the two-class task only.

## Data coverage

| Set | Claims |
|---|---|
| Test SUPPORTS/REFUTES with gold evidence | 13,202 (6,597 / 6,605); 130 excluded (evidence not found) |
| Test NOT ENOUGH INFO with retrieved evidence | 6,552; 114 excluded (no title-matched page) |
| Validation (two-class) | 3,965 resolved of 4,000 sampled |
| Validation (three-class) | 5,945 (3,965 gold + 1,980 NEI retrieved) of 6,000 sampled |

Validation claims never share their text with a test claim. Every model in a table was scored on
the same claim IDs (checked in the notebooks).

## 1. Two-class diagnostic (SUPPORTS vs REFUTES, gold evidence, 13,202 claims)

UNSUPPORTED predictions are counted as "not supported" for scoring, so the CONTRADICTED column
means "not supported", not "contradiction detected".

| Method | Cutoff (source) | Accuracy | Macro-F1 | Run |
|---|---|---|---|---|
| Majority (training prior) | – | 0.500 | 0.333 | `fever_baselines/run_20261022T010816Z` |
| Lexical overlap | 0.5 (fixed) | 0.551 | 0.524 | same |
| Lexical overlap | 0.6 (validation) | 0.575 | 0.574 | same |
| Lexical cues (negation/number) | 0.5 (validation and fixed) | 0.602 | 0.593 | same |
| MiniLM embedding similarity | 0.5 (fixed) | 0.557 | 0.523 | `embedding_nli/run_20261022T010937Z` |
| MiniLM embedding similarity | 0.65 (validation) | 0.602 | 0.601 | same |
| **RoBERTa-MNLI (NLI)** | none | 0.814 | **0.811** | `embedding_nli/run_20261022T015303Z` |

The embedding rows of that NLI run reproduce the earlier embedding run exactly. NLI per class:
SUPPORTED precision 0.937 / recall 0.674, not-supported precision 0.746 / recall 0.955; 2,147 of the
13,202 predictions were raw UNSUPPORTED (counted as not-supported here). Mean latency 341 ms per claim.

## 2. Three-class evaluation (19,754 claims)

| Method | Cutoff (validation) | Accuracy | Macro-F1 | SUPPORTED F1 | CONTRADICTED F1 | UNSUPPORTED F1 |
|---|---|---|---|---|---|---|
| Majority | – | 0.334 | 0.167 | 0.501 | 0.000 | 0.000 |
| Lexical overlap | 0.6 | 0.405 | 0.324 | 0.502 | 0.000 | 0.470 |
| Lexical cues | 0.5 | 0.429 | **0.390** | 0.524 | 0.245 | 0.401 |
| MiniLM embedding similarity | 0.65 | 0.411 | 0.329 | 0.498 | 0.000 | 0.490 |
| **RoBERTa-MNLI (NLI)** | none | 0.704 | **0.699** | 0.738 | 0.776 | 0.583 |

Runs: `outputs/task_b/fever_three_class/run_20261022T010325Z` (baselines) and
`run_20261022T030846Z` (same baselines reproduced exactly, plus NLI; mean NLI latency 25 ms per claim).
NLI precision / recall: SUPPORTED 0.816 / 0.674, CONTRADICTED 0.686 / 0.891, UNSUPPORTED 0.625 / 0.546.
Its main error is calling UNSUPPORTED claims CONTRADICTED (2,266 of 6,552) and SUPPORTED claims
UNSUPPORTED (1,727 of 6,597).

Three-class results are **not comparable** with the two-class diagnostic and must be reported
separately.

## 3. Two-class fine-tuning of RoBERTa-MNLI (SUPPORTED vs CONTRADICTED)

`FacebookAI/roberta-large-mnli` was fine-tuned on FEVER training claims with gold evidence and scored
once on the same 13,202 test claims as Section 1. Run: `outputs/task_b/fever_finetune/run_20261022T191303Z`
(config `configs/task_b_fever_finetune_two_class.json`, notebook
`notebooks/task_b_fever_finetune_two_class.ipynb`). This is **two-class verification only**: gold
evidence is given, NOT ENOUGH INFO claims are absent, and retrieval is not evaluated.

### Training data

Built by `scripts/build_task_b_train_split.py` from `train.jsonl` with the same evidence resolver as the
test and validation sets; claim texts are compared after `claim_key` (case and spacing ignored).

| Step | Rows |
|---|---|
| SUPPORTS/REFUTES rows in `train.jsonl` | 109,810 (80,035 / 29,775) |
| Removed: claim text also in `shared_task_dev.jsonl` (any label) | 3 |
| Removed: claim text of a validation claim (the 4,000 sampled rows plus 870 rows sharing their text) | 4,870 |
| Removed: claim text with conflicting labels in `train.jsonl` (753 such texts, counting NOT ENOUGH INFO; 86 have both SUPPORTS and REFUTES) | 1,207 |
| Eligible | 103,730 |
| Gold evidence resolved | 102,859 (871 unresolved, excluded) |
| **Training split** (every resolved REFUTES + equal seeded sample of SUPPORTS, seed 42) | **53,378 (26,689 / 26,689)** |

The split has no claim text in common with the test records, the full dev file or the validation set
(also checked with Unicode NFC normalisation), no shared IDs and no conflicting-label text. Counts, seed
and source hashes are in the split's `split_manifest.json` (Git-ignored with the data).

### Training setup and checkpoint selection

- **Input:** premise = the claim's gold evidence sentences joined by a space, hypothesis = claim;
  only the evidence is truncated, at 256 tokens (0.28% of training pairs). SUPPORTED → ENTAILMENT (id 2),
  CONTRADICTED → CONTRADICTION (id 0), ids read from the model config. The three-way head is kept;
  NEUTRAL is never a training target. Cross-entropy loss.
- **Optimisation:** 1 epoch (1,669 optimizer steps), batch 16 × gradient accumulation 2, AdamW
  (learning rate 1e-5, weight decay 0.01), 6% linear warm-up then linear decay, gradient clipping 1.0,
  bf16 autocast, gradient checkpointing, seed 42. **One run, one seed.**
- **Selection:** validation macro-F1 under the primary (per-sentence) protocol at each quarter epoch;
  ties keep the earlier step. The test set was not used for selection.

| Step | Validation macro-F1, per-sentence | Validation macro-F1, joined |
|---|---|---|
| 0 (zero-shot) | 0.807 | 0.829 |
| 417 | 0.954 | 0.958 |
| 834 | 0.957 | 0.962 |
| **1,252 (selected)** | **0.961** | 0.966 |
| 1,669 | 0.959 | 0.965 |

The selected checkpoint (`model/` in the run folder, SHA-256 `a3cf1622…`, Git-ignored) reloads with
unchanged labels and identical logits, and reproduces its validation predictions exactly.

### Test results (13,202 claims, scored once)

Two inference protocols are reported, and each compares zero-shot and fine-tuned under the same protocol.
Comparing across protocols does not measure the effect of fine-tuning.

- **Primary, per-sentence:** the unchanged `nli_predictor` used for the zero-shot baseline in Section 1
  (each evidence sentence scored, project aggregation rule, UNSUPPORTED counted as not-supported). Its
  zero-shot row is the saved Section 1 run, on identical claim IDs.
- **Secondary, joined:** one (joined evidence, claim) pair per claim, the training input format; the
  zero-shot model was re-scored this way for the comparison.

| Protocol | Model | Accuracy | Macro-F1 | SUPPORTED P / R | CONTRADICTED P / R | Raw UNSUPPORTED |
|---|---|---|---|---|---|---|
| **Per-sentence (primary)** | Zero-shot | 0.814 | 0.811 | 0.937 / 0.674 | 0.746 / 0.955 | 2,147 |
| **Per-sentence (primary)** | **Fine-tuned** | **0.956** | **0.956** | 0.960 / 0.952 | 0.952 / 0.961 | 0 |
| Joined (secondary) | Zero-shot | 0.827 | 0.825 | 0.937 / 0.702 | 0.762 / 0.953 | 2,062 |
| Joined (secondary) | Fine-tuned | 0.959 | 0.959 | 0.960 / 0.958 | 0.958 / 0.960 | 0 |

CONTRADICTED here means "not supported", as in Section 1. Confusion matrices (rows gold
SUPPORTED, CONTRADICTED; columns predicted): per-sentence zero-shot [[4,445, 2,152], [297, 6,308]],
fine-tuned [[6,278, 319], [260, 6,345]]; joined zero-shot [[4,628, 1,969], [309, 6,296]], fine-tuned
[[6,319, 278], [261, 6,344]].

Under the primary protocol the fine-tuned model corrects 2,040 zero-shot errors and introduces 170 new
ones (McNemar χ² = 1,581 with continuity correction, p < 0.001). This tests these test claims for this
one trained model; it says nothing about variation between training runs. The gain is mainly SUPPORTED
recall (0.674 → 0.952). Of the 2,152 supported claims the zero-shot model missed, 1,727 were raw
UNSUPPORTED (neutral) and 425 CONTRADICTED; the fine-tuned model never predicts neutral on this test set.

Training took 2,202 s plus 1,576 s of in-training validation and saving on an RTX 4060 Laptop GPU (8 GB;
24.2 examples/s; peak 6.68 GiB allocated, 8.09 GiB reserved). The whole notebook, including the zero-shot
reference, the reload check and test scoring, took about 85 minutes. Mean NLI latency is not comparable with the
Section 1 figure and is not reported.

### Limits of this result

- **Two-class only.** The fine-tuned model was never trained to output NEUTRAL and predicted no
  UNSUPPORTED on the test set. It is **not a three-class model** and does not replace the zero-shot
  RoBERTa-MNLI in Section 2 or in the pipeline (the RQ8 notebook passes the zero-shot snapshot
  `models/task_b/roberta-large-mnli/` to `src/pipeline/end_to_end.py`). Do not use it as if it can say
  UNSUPPORTED.
- **Gold evidence is given;** retrieval is not tested.
- **One seed, one run;** no variance estimate.
- **Train and test claims may cite the same Wikipedia pages;** only claim-text overlap was excluded.
  FEVER training and dev claims come from the same annotation process, so this is an in-distribution test.
- **Evidence keeps FEVER's Penn Treebank tokens** (`-LRB-` etc.), as in the baselines.

## Findings

- **Similarity is not support.** Embedding similarity and lexical overlap cannot output
  CONTRADICTED at all; contradicted claims share most of their words with the evidence, so these
  methods label them SUPPORTED or UNSUPPORTED. In the three-class setting their CONTRADICTED F1
  is 0. Only the negation/number cue baseline finds some contradictions (recall 0.149).
- **Validation-chosen cutoffs help in the two-class diagnostic** (embedding 0.523 → 0.601), mostly
  by calling more claims "not supported", not by detecting contradictions.
- **NLI clearly beats similarity and lexical baselines** on identical claims: 0.811 vs 0.601
  (two-class) and 0.699 vs 0.390 (three-class), because it is trained to separate entailment from
  contradiction. It is far slower (25–341 ms vs under 1 ms per claim).
- The three-class NLI result depends on unreviewed retrieved NEI evidence; its UNSUPPORTED scores
  in particular are only as valid as that evidence.
- **Fine-tuning on FEVER training claims raises two-class macro-F1 from 0.811 to 0.956** under the
  unchanged per-sentence protocol (Section 3), mostly by recovering supported claims the zero-shot model
  called neutral (1,727) or contradicted (425). This is an in-distribution, gold-evidence, single-run result for a two-class model.

## The NOT ENOUGH INFO evidence policy and its limits

FEVER annotators judged NEI claims unverifiable from Wikipedia, so they keep FEVER's label, mapped
to UNSUPPORTED. They have no gold evidence, so evidence is retrieved: Wikipedia pages whose title
matches a capitalised phrase in the claim (longest match first, undisambiguated title first, at
most 3 pages), then the single sentence sharing the most content words with the claim. Claims with
no matching page are excluded and counted; empty evidence is never used.

- **Unreviewed.** The retrieved evidence has not been human-reviewed; some retrieved sentences may
  in fact support or contradict the claim. A seeded 100-item review sheet with blank label columns is
  written by the notebook (`nei_evidence_review_sheet.csv`).
- **Possible shortcut.** NEI evidence is always one sentence, while gold evidence averages 1.12–1.20
  sentences; median word overlap is slightly lower for NEI (0.54 vs 0.57–0.67). A model could exploit
  this; check it before trusting any trained or tuned three-class model.
- **Gold evidence is given** for SUPPORTS/REFUTES, so retrieval quality is not tested for them.
- **Evidence text is verbatim FEVER text** with Penn Treebank tokens (`-LRB-` etc.) in about 30% of
  sentences; whether to normalise them is an open decision.

## Not yet done

| Item | Status |
|---|---|
| Human review of retrieved NEI evidence | Review sheet generated; needs reviewers. |
| RQ4 atomic claims vs sentences | Workflow, loader, validation and notebook ready; needs an independently reviewed paired dataset (`data/annotations/task_b_reviewed_pairs.jsonl`). No results exist. |
| RQ6 difficult subsets | Not started; needs the custom annotated set. |
| Fine-tuned model beyond two classes | Not done. No three-class fine-tuning, no seed repeats, no evaluation on retrieved evidence or custom data. |

## Reproduce (open the `NLP_PROJECT` repository folder in VS Code)

1. `notebooks/task_b_fever_baselines.ipynb` (prepares gold test and validation records; ~1–2 min)
2. `notebooks/task_b_embedding_nli.ipynb` (two-class embedding; NLI if the model is present)
3. `notebooks/task_b_fever_three_class.ipynb` (three-class; ~4–5 min, two extra Wikipedia scans)
4. `notebooks/task_b_atomic_vs_sentence.ipynb` only once reviewed paired data exists.
5. Two-class fine-tuning (needs steps 1–2 and a CUDA GPU; about 85 min on an 8 GB laptop GPU):
   ```bash
   python scripts/build_task_b_train_split.py --seed 42   # once; refuses to overwrite an existing split
   jupyter execute notebooks/task_b_fever_finetune_two_class.ipynb --timeout=14400
   ```
   Each run writes a new `outputs/task_b/fever_finetune/run_<UTC>/` folder. With the environment variable
   `TASK_B_SMOKE_TEST=1` the notebook runs only 200 steps and a 200-claim test subset into
   `smoke_run_<UTC>/`. That is an engineering check; never report it.

`archive/task_b_outdated_notebooks/task_b_fever_baselines_vscode.ipynb` is an archived outdated copy; do not use it.
