# SafeLLM

**NLP-Based Detection of Adversarial Prompts and Faithfulness Verification of LLM Outputs**

SafeLLM is a university NLP/ML study of adversarial-prompt detection (Task A) and evidence-grounded
claim verification (Task B). The intended contribution is a systematic combination and evaluation of
established methods, including robustness, verification granularity, and legitimate utility. It does not
claim to invent jailbreak detection or detect all hallucinations.

**This branch (`task-b-claim-verification`) carries the Task B work.** Task A detectors and their results
live on the `task-a-binary-dataset` branch; the Task A material here is the Phase 1 audit and the
four-label pilot only. The Task A → Task B filtering pipeline is not on this branch.

## Task B status (2026-10-23)

Claim verification against evidence on FEVER, labels SUPPORTED / CONTRADICTED / UNSUPPORTED. Every number
comes from a saved run named in [docs/task_b_results.md](docs/task_b_results.md).

| Result | Value | Notes |
|---|---|---|
| Two-class diagnostic, zero-shot RoBERTa-MNLI | macro-F1 **0.811** | 13,202 FEVER test claims, gold evidence; best similarity/lexical baseline 0.601 |
| Two-class, **fine-tuned** RoBERTa-MNLI | macro-F1 **0.956** | Same 13,202 claims and same per-sentence inference as the zero-shot row; one run, one seed |
| Three-class, zero-shot RoBERTa-MNLI | macro-F1 0.699 | 19,754 claims (NOT ENOUGH INFO with retrieved, unreviewed evidence); best baseline 0.390 |

Implemented: FEVER preparation with gold-evidence resolution and a validation split disjoint from test;
majority, lexical-overlap, lexical-cue and MiniLM embedding-similarity baselines with validation-chosen
cutoffs; zero-shot NLI (`FacebookAI/roberta-large-mnli`); a leakage-checked balanced training split
(53,378 pairs); and two-class fine-tuning with checkpoint selection on validation and a single test pass.

### Limitations of the fine-tuned model

- **Two-class only** (SUPPORTED vs CONTRADICTED). NOT ENOUGH INFO / UNSUPPORTED claims were not in training
  or in its evaluation; there is no fine-tuned three-class model. Three-class results use the zero-shot model.
- **Gold evidence is given.** Retrieval is not evaluated, so 0.956 is not an end-to-end verification score.
- **One run, one seed.** No repeat runs; training and test claims can share Wikipedia pages (claim texts are
  disjoint, pages are not).
- It does **not** complete the three-class verifier, the RQ4 atomic-claim comparison, or an end-to-end
  pipeline. The project has no answer-generation stage, so no LLM output has been verified.

### Not yet done (Task B)

Human review of the retrieved NOT ENOUGH INFO evidence; RQ4 (sentence vs atomic-claim verification), which
needs an independently reviewed paired dataset; RQ6 difficult subsets; any fine-tuning beyond two classes.

## Setup

Tested with Python 3.11.9, torch 2.6.0+cu124 and transformers 5.3.0 on Windows with an 8 GB NVIDIA laptop
GPU (fine-tuning needs CUDA; the other notebooks run on CPU, more slowly).

```bash
python -m venv .venv
.venv\Scripts\activate                     # Windows; on Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements-task-b.txt
python -m unittest discover -s tests -v
```

Local inputs, **none of which are in Git**:

| Path | Contents |
|---|---|
| `data/raw/fever/` | FEVER `train.jsonl`, `shared_task_dev.jsonl` and `wiki-pages/*.jsonl` (download separately; see the FEVER licence) |
| `models/task_b/roberta-large-mnli/` | Complete `FacebookAI/roberta-large-mnli` snapshot (MIT); the notebooks never download it and verify its hash |
| `models/task_b/all-MiniLM-L6-v2/` | Optional; otherwise read from an existing Hugging Face cache |

Outputs go to `outputs/task_b/` (Git-ignored): prepared records, run folders, the training split and the
fine-tuned checkpoint.

**The fine-tuned checkpoint is stored locally only** at
`outputs/task_b/fever_finetune/run_20261022T191303Z/model/` (about 1.4 GB, folder fingerprint SHA-256
`a3cf1622…`, recorded in that run's `run.json`). It is not in Git and is not published; anyone without that
folder must retrain it with the steps below.

## Reproduce Task B

Run from the repository root (details and expected outputs: [docs/task_b_results.md](docs/task_b_results.md)).

1. `notebooks/task_b_fever_baselines.ipynb` — prepares gold test and validation records, runs the baselines.
2. `notebooks/task_b_embedding_nli.ipynb` — embedding similarity and zero-shot NLI (two-class).
3. `notebooks/task_b_fever_three_class.ipynb` — three-class evaluation.
4. Two-class fine-tuning (after steps 1–2; the reported run took 63 minutes end to end on the GPU above):
   ```bash
   python scripts/build_task_b_train_split.py --seed 42   # once; refuses to overwrite an existing split
   jupyter execute notebooks/task_b_fever_finetune_two_class.ipynb --timeout=14400
   ```
   Each run writes a new `outputs/task_b/fever_finetune/run_<UTC>/`. `TASK_B_SMOKE_TEST=1` runs a short
   engineering check into `smoke_run_<UTC>/`; never report it.
5. `notebooks/task_b_atomic_vs_sentence.ipynb` — RQ4, only once reviewed paired data exists.

## Research questions

| RQ | Comparison | Status on this branch |
|---|---|---|
| 1–3, 7 | Task A detectors, hard negatives, unseen data, thresholds | On `task-a-binary-dataset` |
| 4 | Sentence-level vs atomic-claim verification | Workflow ready; blocked on reviewed data |
| 5 | Embedding similarity vs NLI | Done for FEVER (two- and three-class) |
| 6 | Numerical, partial-evidence, multi-hop, implicit and decomposition errors | Not started |
| 8 | Guardrails OFF vs ON | Not on this branch |

## Repository structure

```text
configs/                 Versioned JSON configuration (incl. task_b_fever_finetune_two_class.json)
data/raw/fever/          FEVER source files (Git-ignored)
models/task_b/           Local model snapshots (Git-ignored)
src/task_b/              FEVER loading, evidence resolution, baselines, NLI, verification utilities
src/task_a/              Task A Phase 1 audit and pilot code
scripts/                 Command-line steps (incl. build_task_b_train_split.py)
notebooks/               Task B experiment notebooks
outputs/task_b/          Task B runs, prepared records, training split, checkpoint (Git-ignored)
archive/                 Superseded files kept for provenance (early Task B scaffold, outdated notebook)
tests/                   Automated checks
docs/                    Task B implementation and results; Task A audit and pilot documents
```

## Limitations and data policy

There is no safety guarantee and no end-to-end pipeline on this branch. Results are FEVER-only and use
Wikipedia evidence; behaviour on real LLM answers is untested. Keep credentials, raw data, checkpoints and
prediction dumps out of Git. A project licence has not yet been selected by the owner.
