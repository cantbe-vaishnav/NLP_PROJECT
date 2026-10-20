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
