# SafeLLM

**NLP-Based Detection of Adversarial Prompts and Faithfulness Verification of LLM Outputs**

SafeLLM is a university NLP/ML study of adversarial-prompt detection and
evidence-grounded verification. The intended contribution is a systematic
combination and evaluation of established methods, including robustness,
verification granularity, and legitimate utility. It does not claim to invent
jailbreak detection or detect all hallucinations.

**Current status: Phase 0 infrastructure only. No datasets, trained models,
research predictions, or measured research results exist.**

Phase 1 has begun with a [preliminary dataset audit](docs/task_a_dataset_audit.md).
The label policy is approved. Work is paused at an
[access/source-selection gate](docs/phase1_access_gate_report.md); no dataset has
been accepted or split and Phase 1 is not complete.

## Installation and checks

Python 3.11+ is required for this infrastructure. Phase 0 is tested locally with
Python 3.14.5; this does not establish compatibility with the future ML stack.
Reassess the interpreter and lock ML dependencies before adding them.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
python -m unittest discover -s tests -v
safellm doctor
```

The build uses setuptools 80.9.0; initial installation needs access to a package
index or a locally cached copy. There are no third-party runtime dependencies in
Phase 0. Tests use `unittest`. Future phases add scikit-learn, pandas/Datasets,
PyTorch/Transformers and an embedding encoder as needed. Streamlit is deferred.

## Research questions

| RQ | Planned comparison or investigation |
| --- | --- |
| 1 | TF-IDF + Logistic Regression versus fine-tuned DistilBERT |
| 2 | Hard negatives discussing attacks without performing them |
| 3 | Unseen formulations and, where metadata permits, unseen categories |
| 4 | Sentence-level versus atomic-claim verification |
| 5 | Embedding similarity versus NLI; optional LLM judge |
| 6 | Numerical, partial-evidence, multi-hop, implicit and decomposition errors |
| 7 | Detector recall versus false-positive rate across thresholds |
| 8 | Guardrails OFF versus ON: attacks, faithfulness, legitimate utility |

## Planned architecture

```text
Prompt -> detector -> BENIGN: allow -> LLM -> response
                   -> ADVERSARIAL: block or flag for policy handling
Response -> sentence / atomic-claim decomposition
Claims + evidence -> similarity baseline / NLI verifier
                  -> SUPPORTED / CONTRADICTED / UNSUPPORTED -> accept or flag
```

A blocked prompt must not automatically proceed to the LLM. An LLM judge is an
optional experimental comparison, never a core dependency. NLI label mapping and
decomposition limitations require explicit documentation in their phases.

## Repository structure

```text
configs/                      Versioned JSON configuration
data/{raw,interim,processed,annotations}/
src/safellm/                  CLI and experiment metadata recording
src/task_a/                   Future detector implementation (member 1)
src/task_b/                   Future verification implementation (member 2)
src/pipeline/                 Future integration (member 3)
experiments/{task_a,task_b,end_to_end}/
models/                      Reproducible model artifacts, ignored by Git
results/{metrics,predictions,figures,error_analysis}/
app/                         Reserved; no demo yet
tests/                       Phase 0 automated checks
docs/                        Audit, experiment log, annotation status, report
```

This checkout is the repository root; a second nested `safellm/` directory is
unnecessary. Future modeling filenames will be added when implemented rather
than filled with nonfunctional stubs.

## Dataset setup, training and evaluation

Not implemented in Phase 0. Phase 1 starts with dataset research and audit:
record sources, licenses, schemas, label semantics, class balance, category
metadata and leakage risks before ingestion or splitting. Do not treat generic
harmfulness as equivalent to adversarial manipulation. Deduplicate and inspect
template/source leakage before splits. No dataset download is currently needed.

Training and evaluation commands will be documented only when operational.
Use validation data for thresholds, hyperparameters and checkpoint selection;
reserve test data for final evaluation. Keep benchmark and custom data separate.
No fabricated examples may be represented as collected research data.

## Experiment records and reproducibility

To check metadata recording without running any model:

```bash
safellm init-run --config configs/phase0.json --output-root /tmp/safellm-runs
```

This creates `phase0_smoke/config.json`, `manifest.json` and `notes.md`.
Repeating the same run identifier in that location fails to prevent overwriting.
The manifest records UTC time, interpreter, platform, installed package versions,
and the caller's Git commit/dirty state. Execute real experiments from a clean
checkout. A dirty flag alone cannot reproduce uncommitted code.

The recorder stores the requested seed but does not set RNG state or enforce
training determinism. Each future training implementation must do that explicitly.
Metrics, predictions and errors remain absent until actually produced. This is
initialization infrastructure, not yet a complete experiment runner.

Future runs must follow RQ → hypothesis → dataset → baseline → proposed method →
metrics → measured results → error analysis. Preserve raw predictions, model
references, config, seed, metrics and errors; derive tables/figures from those
artifacts. Review run artifacts for privacy and licensing before committing them.
See [experiment log](docs/experiment_log.md).

## Scope and gates

Phase 0 stops after environment, packaging, tests and documentation. Phase 1
audits data before implementation. Gate 1 requires clean, documented splits
before modeling. Gate 2 requires both Task A TF-IDF and Task B FEVER baselines
before substantial transformer work, despite the numeric phase ordering.

Tier 1: RQ1, RQ4, RQ8, core errors and eventual demo. Tier 2: RQ2/RQ3 and human
annotation. Tier 3: RQ5/RQ7, additional ablations and LLM judge. Core baseline
components remain required even where extended comparisons are optional. Freeze
scope at the week 6–7 gate if core results lag. Build the UI after reproducibility.

## Limitations and citations

All research hypotheses remain untested. There is no safety guarantee, trained
detector, verifier or end-to-end pipeline. Human annotation and independent
double labeling have not occurred. See [annotation status](docs/annotation_guidelines.md).

The supplied technical report provides planning context; the pasted user request
controls this implementation. Literature mentioned there is not a verified
bibliography. Citation verification and dataset licensing research are deferred
to the relevant research phase; no unverified publication metadata is asserted.

## GitHub workflow

Use logical commits and keep credentials, raw data and checkpoints out of Git.
No remote URL has been supplied. The local repository can be connected to a
user-owned GitHub repository once its actual URL is known; no push is performed
to an unknown remote. A project license has not yet been selected by the owner.
