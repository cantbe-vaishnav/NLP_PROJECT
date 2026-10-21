# SafeLLM Task B handoff — 22 October 2026

## Project state

- Repository: `cantbe-vaishnav/NLP_PROJECT`.
- Working branch: `codex/task-b-faithfulness`, pushed to GitHub. Task B implementation commit: `cb6c6a1`.
- B0 contract commit: `a7ba239`. Task B remains independent of Task A Gate 1.
- No Task A source, data, experiment, or Git branch was changed during this work. No PR was opened or merged.

## Implemented

1. **B0 claim/evidence contract reused.** `src/task_b/schema.py` defines the three labels (`SUPPORTED`, `CONTRADICTED`, `UNSUPPORTED`), typed claim/evidence records, and structural validators. New code adapts FEVER to these records and passes the claim when validating custom reviews.
2. **B1 FEVER preparation.** `src/task_b/fever.py` reads official-style FEVER claim JSONL and `wiki-pages/*.jsonl`, resolves page/sentence references to actual text, selects the first fully resolved gold evidence group, and retains raw references, IDs, source labels, file/line paths, and the selected group index. Missing or invalid evidence is reported rather than replaced. NEI remains excluded pending an evidence policy.
3. **B2 baselines and evaluation utilities.** `src/task_b/verification.py` has a training-file majority prior, lexical overlap, fixed negation/numeric cues, deterministic metrics, latency timing, and run artifact writing. Lexical overlap cannot identify contradictions. The FEVER two-class diagnostic maps a raw `UNSUPPORTED` prediction to the negative class only for scoring; raw predictions and their count remain saved.
4. **B3 model infrastructure.** `src/task_b/models.py` supports local MiniLM cosine similarity and local RoBERTa MNLI. MNLI passes evidence as premise and claim as hypothesis, reads label IDs from the model configuration, and uses a documented project-specific sentence aggregation rule. Local model snapshots are fingerprinted in run configs. No weights were added to Git.
5. **RQ4 preparation.** `src/task_b/custom.py`, `docs/task_b_annotation_template.csv`, and `notebooks/task_b_atomic_vs_sentence.ipynb` support an independently reviewed, paired sentence/atomic-claim set using matching answer IDs and source passages. No custom gold labels were invented.
6. **Notebooks.** `notebooks/task_b_fever_baselines.ipynb`, `notebooks/task_b_embedding_nli.ipynb`, and `notebooks/task_b_atomic_vs_sentence.ipynb` are Python-code-only notebooks. A second `task_b_fever_baselines_vscode.ipynb` copy was created to bypass a stale VS Code editor tab. The FEVER notebook now uses only the Python standard library for setup and results tables, finds the project root from either the root or `notebooks/` directory, and does not require pandas.

## Local inputs and run artifacts

- FEVER files are present locally under `data/raw/fever/` (about 8.7 GB); model snapshots are under `models/task_b/` (about 1.4 GB). Both are ignored by Git and were not uploaded.
- Local outputs under `outputs/task_b/` are ignored by Git and were not uploaded. Saved notebook outputs were backed up under `outputs/task_b/local_notebook_backups/` before clean notebooks were committed.
- The FEVER resolution report records **13,202 resolved** SUPPORTS/REFUTES claims, **130 unresolved** claims, and **6,666 NEI** rows excluded. Baseline run artifacts cover 13,202 resolved claims.
- Embedding and NLI artifacts each cover **20 claims**. These are small pilot diagnostics, not the completed model evaluation and not directly comparable to the 13,202-claim baseline runs.
- Each local run directory contains a config, predictions, and results. The FEVER scores are **gold-evidence diagnostics**; they do not measure retrieval or the full three-class Task B problem. FEVER and future custom-set metrics must remain separate.

## Verification and known limits

- The B0 and new Task B focused tests passed (15 tests). All 47 repository tests passed when the available bundled `openpyxl` was added to the test environment; the plain project virtual environment lacked `openpyxl` for one pre-existing Task A test.
- All Task B notebooks were checked for code-only cells and Python syntax. The FEVER notebook's full cell flow passed with a temporary synthetic fixture; those fixture scores are not research findings.
- `docs/task_b_implementation.md` documents input paths, notebook execution order, methods, output structure, and the independently reviewed custom-set format.
- The separate local, untracked `docs/task_b_b0_review_report.md` identifies unresolved B0 review issues concerning optional-field serialization, annotation reference checks without a claim, and broader provenance. The new pipeline omits absent optional fields and passes claims when validating completed custom reviews; it does not change or approve the B0 contract itself.
- The research decision brief named in the original Task B request was not available in the supplied attachment or checkout. The implementation followed the pasted request and existing B0 contract.

## Next notebook order

1. `notebooks/task_b_fever_baselines.ipynb` (or the `*_vscode.ipynb` copy if VS Code still shows the stale tab).
2. `notebooks/task_b_embedding_nli.ipynb` with local model snapshots and the prepared FEVER records.
3. `notebooks/task_b_atomic_vs_sentence.ipynb` only after an independently reviewed custom paired set exists.

## Remaining

Complete the evaluation, including the full model evaluation, and the atomic-claims-versus-sentences comparison.
