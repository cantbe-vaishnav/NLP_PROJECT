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
