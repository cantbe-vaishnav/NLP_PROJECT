# Task B results: claim verification against evidence (FEVER)

Labels: SUPPORTED, CONTRADICTED, UNSUPPORTED. All numbers come from saved runs under
`outputs/task_b/` (Git-ignored; regenerate with the notebooks). Every cutoff was chosen on a
validation sample drawn from FEVER `train.jsonl`; the test set (FEVER `shared_task_dev.jsonl`) was
scored once per run. The NLI model (RoBERTa-MNLI) has not been run: its download is awaiting
approval, so NLI results do not exist yet.

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
| MiniLM embedding similarity | 0.65 (validation) | 0.602 | **0.601** | same |

## 2. Three-class evaluation (19,754 claims)

| Method | Cutoff (validation) | Accuracy | Macro-F1 | SUPPORTED F1 | CONTRADICTED F1 | UNSUPPORTED F1 |
|---|---|---|---|---|---|---|
| Majority | – | 0.334 | 0.167 | 0.501 | 0.000 | 0.000 |
| Lexical overlap | 0.6 | 0.405 | 0.324 | 0.502 | 0.000 | 0.470 |
| Lexical cues | 0.5 | 0.429 | **0.390** | 0.524 | 0.245 | 0.401 |
| MiniLM embedding similarity | 0.65 | 0.411 | 0.329 | 0.498 | 0.000 | 0.490 |

Run: `outputs/task_b/fever_three_class/run_20261022T010325Z`.

Three-class results are **not comparable** with the two-class diagnostic and must be reported
separately.

## Findings

- **Similarity is not support.** Embedding similarity and lexical overlap cannot output
  CONTRADICTED at all; contradicted claims share most of their words with the evidence, so these
  methods label them SUPPORTED or UNSUPPORTED. In the three-class setting their CONTRADICTED F1
  is 0. Only the negation/number cue baseline finds some contradictions (recall 0.149).
- **Validation-chosen cutoffs help in the two-class diagnostic** (embedding 0.523 → 0.601), mostly
  by calling more claims "not supported", not by detecting contradictions.
- The baselines are weak (0.39 three-class macro-F1), which is the expected motivation for the
  NLI verifier (RQ5).

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
| NLI (RoBERTa-MNLI) on the same claims, two- and three-class | Code ready in both notebooks; needs model download approval (about 1.43 GB, MIT). |
| Human review of retrieved NEI evidence | Review sheet generated; needs reviewers. |
| RQ4 atomic claims vs sentences | Workflow, loader, validation and notebook ready; needs an independently reviewed paired dataset (`data/annotations/task_b_reviewed_pairs.jsonl`). No results exist. |
| RQ6 difficult subsets | Not started; needs the custom annotated set. |

## Reproduce (open the `NLP_PROJECT_task_b` folder in VS Code)

1. `notebooks/task_b_fever_baselines.ipynb` (prepares gold test and validation records; ~1–2 min)
2. `notebooks/task_b_embedding_nli.ipynb` (two-class embedding; NLI if the model is present)
3. `notebooks/task_b_fever_three_class.ipynb` (three-class; ~4–5 min, two extra Wikipedia scans)
4. `notebooks/task_b_atomic_vs_sentence.ipynb` only once reviewed paired data exists.

`notebooks/task_b_fever_baselines_vscode.ipynb` is an outdated copy; do not use it.
