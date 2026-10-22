# Experiment log

## 2026-09-12 — Phase 0 infrastructure

- Engineering requirement: reproducible repository setup and run metadata.
- Initial state: empty directory; no Git repository, tests or requirements.
- Added packaging, task-package skeletons, JSON configuration, metadata recorder,
  directory integrity checks and documentation.
- No datasets ingested, models trained, research predictions or metrics produced.
- `configs/phase0.json` is an engineering check, not a research experiment.
- Validation evidence is recorded in `docs/phase0_validation.md` after execution.

## 2026-09-12 — Phase 1 preliminary audit (research gate)

- Reviewed public primary-source cards/documentation for WildGuardMix,
  Deepset prompt-injections, WildJailbreak, JailbreakBench and HarmBench.
- Found a material label-policy distinction: non-adversarial is not synonymous
  with harmless; context can determine injection status.
- Recorded candidate limitations and proposed policy in `task_a_dataset_audit.md`.
- No ingestion, split, hard-negative annotations, models or research results.
- Stopped for label-policy review under the user's autonomous-engineering /
  human-research-gates workflow. Phase 1 remains incomplete.

## Future experiment entry template

## 2026-09-12 — Approved policy; source access audit

- User approved non-adversarial BENIGN, boundary-manipulation ADVERSARIAL,
  separate harmfulness metadata and quarantine for ambiguity.
- Verified public source metadata and downloaded only a 100-row Deepset preview.
- Pinned WildGuardMix access probe returned HTTP 401; local HF credentials absent.
- Added configurable audit probe, descriptive statistics, five new tests and
  hard-negative review workflow. All 10 tests pass; no corpus accepted or split.
- See `phase1_access_gate_report.md` and generated `results/data_audit/source_probe_summary.json`.
- Phase 1 remains incomplete. No research metrics or model results produced.

### Future experiment fields

- Unique identifier and date:
- Research question and hypothesis:
- Dataset source/version, license, split and benchmark/custom designation:
- Baseline and proposed method:
- Model/checkpoint, parameters and seed:
- Code revision and environment record:
- Validation-based selection procedure:
- Raw predictions, metrics and error artifact paths:
- Measured result (pending until execution):
- Error analysis, limitations and next decision:

Do not report initialized or failed runs as completed experiments. Keep benchmark
and custom runs separately identifiable and retain failures/negative results.

## Authenticated browser checkpoint

Browser access is confirmed, but dataset downloads did not become available to
local tools. Added pinned Parquet inspection dependency, offline source inspector,
and three engineering tests; all 13 tests pass. No dataset mapping or splits.
See the latest section of phase1_gate_report.md for checks and exact blocker.

## Actual full-source audit

Local WildGuardMix files verified: 86,759 train and 1,725 test rows. Ran source,
exact/normalized duplicate and bounded near-duplicate audits. Inspected a seed-42
20-row stratified training sample, finding source-adversarial flags that do not
unambiguously match SafeLLM's definition. No automatic relabeling. Saved pending
human review queue. Eighteen tests and deterministic full-audit rerun passed.
Current gate is semantic validation/annotation procedure, not authentication.
See phase1_gate_report.md for counts, commands, limitations and proposed decision.

## Approved 200-prompt semantic pilot

*Historical; superseded by the four-label entry below.*

- Generated 50 normalized-unique training prompts from each of four source
  adversarial × harmfulness strata with seed 42; no stratum shortfall.
- Preserved source labels only in a local master; created two blind independent
  reviewer CSVs with no prefilled SafeLLM decisions.
- Added strict annotation validation, agreement/kappa, source cross-tab,
  per-stratum disagreement and adjudication-queue tooling.
- No human annotations, pilot metrics or source-use recommendation yet.
- Phase 1 remains at the human semantic-validation gate.

## Four-label Task A schema made canonical

- Decision: Task A uses BENIGN, HARMFUL, ADVERSARIAL, QUARANTINE as its sole schema;
  the three-label schema above is superseded. Task B labels unchanged.
- Pilot tooling now supports three reviewers (CSV or XLSX), pairwise Cohen's kappa,
  Fleiss' kappa, confusion matrices, agreement patterns and per-item disagreement
  tables. Adjudication-queue generation and the binary source-mismatch rate were
  removed; source comparison is a separate, descriptive cross-tab.
- Reviewer independence is owner-confirmed, not independently audited; see the
  guidelines.
- No annotation files were modified. No models, splits or Task B work.

## Binary jailbreak dataset (WildGuardMix + JailbreakHub)

- Downloaded JailbreakHub `jailbreak_2023_12_25` and `regular_2023_12_25` at revision
  `a10aab8e…` (MIT); SHA-256 verified against the Hub. Raw files Git-ignored.
- Built the merged binary dataset with `scripts/build_binary_dataset.py`: invalid,
  duplicate, label-conflict and official-test-overlap exclusions; near-duplicate
  families; seed-42 grouped splits; official WildGuardMix test unchanged.
- Audit: `results/data_audit/binary_jailbreak_audit.md`; method: `task_a_binary_dataset.md`.
- No model trained. Gate 1 status unchanged.

## Binary dataset v2 (reviewed JailbreakHub corrections)

- Applied the full-text review corrections (not human-verified): 169 labels 0→1, 5 labels 1→0,
  13 ambiguous rows excluded and held out. Built `data/processed/binary_jailbreak_v2/`
  with recomputed families and splits; all leakage checks passed; official test unchanged.
- Audit: `results/data_audit/binary_jailbreak_v2_audit.md`. v1 retained unchanged. No model trained.

## Task A models on dataset v2 (RQ1)

- Notebooks: `task_a_binary_tfidf_baseline_v2`, `task_a_binary_tfidf_linear_svm_v2`, `task_a_binary_distilbert_v2`.
  Selection on validation only; both test sets scored once. Latest runs: LogReg `run_20261021T022858Z`,
  SVM `run_20261021T022904Z`, DistilBERT `run_20261021T024649Z` (see each `metrics.json`).
- Test macro-F1, official / JailbreakHub: LogReg 0.994 / 0.793, SVM 0.995 / 0.820, DistilBERT 0.998 / 0.811.
- Truncation measured on the full data (DistilBERT tokenizer): JailbreakHub test prompts over 256 tokens 44.0%,
  over 512 tokens 24.7%; official test 7.0% and 0.2%. An earlier "55%" figure came from a small smoke-test
  sample and is wrong.
- Error analysis: `docs/task_a_error_analysis.md`. Prepared, not run: `task_a_binary_distilbert_512_v2`.
- Task B: plan and first baseline scaffold in `docs/task_b_plan.md`; no Task B data or results yet.
