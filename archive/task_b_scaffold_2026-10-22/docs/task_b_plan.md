# Task B plan: claim-level faithfulness verification

Roadmap Phase 5 ("Task B FEVER baseline": FEVER loading, embedding baseline, NLI baseline), owned
by Member 2. Gate 2 requires this baseline before substantial transformer work on Task B.

## Current state (2026-10-22)

- `src/task_b/` held only a placeholder; `experiments/task_b/` is empty. No Task B data, model or result exists.
- No FEVER data is present locally, and the `datasets` package is not installed.
- Cached locally: `sentence-transformers/all-MiniLM-L6-v2` (embedding baseline). No NLI checkpoint
  (e.g. RoBERTa-MNLI) is cached.
- Added: the input format and loader (`src/task_b/data.py`, tested), `configs/task_b_fever_baselines.json`
  and `notebooks/task_b_fever_baselines.ipynb` (not run; it needs the data below).

## Task and labels

Input: one claim and the evidence text it is checked against. Output:

| Label | Meaning | FEVER verdict |
|---|---|---|
| SUPPORTED | the evidence entails the claim | SUPPORTS |
| CONTRADICTED | the evidence entails the claim's negation | REFUTES |
| UNSUPPORTED | the evidence does not settle the claim | NOT ENOUGH INFO |

High similarity between claim and evidence is not support: a contradicted claim usually shares most
of its words with the evidence.

## Step 1: prepare the data (next concrete step)

Write three files to `data/processed/task_b_fever/` (Git-ignored), one JSON object per line:
`{"id": ..., "claim": ..., "evidence": ..., "label": "SUPPORTED" | "CONTRADICTED" | "UNSUPPORTED"}`.

Decisions for Member 2 before downloading anything:

1. **Source and licence.** FEVER 1.0 (claims plus Wikipedia evidence), or a FEVER-derived release that
   already pairs every claim with evidence text. Record the source, version and licence.
2. **Evidence for UNSUPPORTED claims.** FEVER's NOT ENOUGH INFO claims have no annotated evidence.
   They need real retrieved sentences from a related page. Never use empty or placeholder evidence:
   the model would learn "no evidence = UNSUPPORTED" without verifying anything. The notebook
   prints evidence length per label to expose this.
3. **Splits.** Use the labelled FEVER development set as the test set (the official test labels are
   not public). Hold out about 10% of the FEVER training claims as validation. Many claims are
   rewrites of the same Wikipedia sentence, so keep claims that share an evidence sentence in the
   same split. The notebook checks that no claim text repeats across splits.

## Step 2: baselines (`notebooks/task_b_fever_baselines.ipynb`)

1. Majority class: the floor.
2. Claim only (TF-IDF + Logistic Regression, evidence ignored): measures how much the claim wording
   alone reveals. A verifier must clearly beat it.
3. Embedding similarity (roadmap baseline): MiniLM cosine similarity between claim and evidence,
   mapped to a label by logistic regression.

Every C is chosen on validation macro-F1; test is scored once. Reported: per-class precision, recall
and F1, macro-F1, accuracy, and test confusion matrices. Runs are saved to `results/task_b_fever_baselines/`.

## Step 3: NLI verifier (proposed method)

A pretrained NLI model (RoBERTa-MNLI or equivalent) maps entailment to SUPPORTED, contradiction to
CONTRADICTED and neutral to UNSUPPORTED. Evaluate it zero-shot on the same splits first, then decide
on fine-tuning using validation results only. This requires downloading a checkpoint (owner approval).

## Later phases (roadmap)

Phase 6: custom LLM answers decomposed into atomic claims with double annotation and Cohen's kappa.
Phase 7: sentence-level vs atomic-claim verification (RQ4) and difficult subsets (RQ6).
Phase 8: similarity vs NLI, with an optional LLM judge (RQ5).
