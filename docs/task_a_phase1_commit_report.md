# Task A Phase 1: commit and publish report

Date: 2026-10-22. Branch: `task-a-binary-dataset`.

## State before acting

- Repository root `NLP_PROJECT`, HEAD `47b38c8`. The local branch tracked `origin/main` (2 commits ahead); no
  `task-a-binary-dataset` branch existed on origin, so `11176fc` and `47b38c8` had never been pushed.
- Working tree: 3 modified files, 6 untracked paths (one of them a folder holding 3 files). Matches the earlier report.
- Other worktrees (`NLP_PROJECT_task_b` on `codex/task-b-faithfulness`, `NLP_PROJECT_integration` on
  `integration-pipeline`) were not touched.

## Committed (`0175bbd`)

| File | Notes |
|---|---|
| `notebooks/task_a_error_analysis_v2.ipynb` | Figures plus interpretation cells; executed top to bottom, no error outputs; outputs are aggregate tables and PNGs, no prompt text |
| `notebooks/task_a_threshold_analysis_v2.ipynb` | RQ7 figures; same checks |
| `src/task_a/plotting.py` | Shared colors, model names, Matplotlib style |
| `docs/task_a_results.md` | Figure index |
| `.gitignore` | Adds `outputs/annotation_agreement_pilot/source_crosstab/disagreement_table.csv` (reviewer rationales, same rule as `recomputed/`) |

The two earlier unpushed commits were checked before pushing: 87 files in total; the only CSVs are aggregate
metric tables; no datasets, prediction dumps, model weights or credentials.

## Excluded (left untracked, unchanged)

| Path | Reason |
|---|---|
| `outputs/annotation_agreement_pilot/source_crosstab/` (report, JSON, CSV) | `outputs/annotation_agreement_pilot/README.md` records that source-label comparison results are run locally and not committed; CSV holds reviewer rationales |
| `configs/task_b_fever_baselines.json`, `docs/task_b_plan.md`, `src/task_b/data.py`, `tests/test_task_b_data.py` | Task B scaffolding; not on the Task B branch; belongs with Task B, not this branch |
| `notebooks/task_b_fever_baselines.ipynb` | Task B; **a different file with the same path exists on `codex/task-b-faithfulness`**, so committing it here would conflict on merge |

## Push

`git push -u origin task-a-binary-dataset` created the new remote branch (no force, no divergence possible).
`origin/task-a-binary-dataset` = `0175bbd7c2c8c7c1d869505155eb3608a0435902` = local HEAD. The local branch now
tracks `origin/task-a-binary-dataset` instead of `origin/main`. Nothing was merged into `main`.

## Tests

| Interpreter | Command | Result |
|---|---|---|
| `.venv` (Python 3.10) | `pytest` on the 9 Task A test files | 72 passed, 3 skipped (scikit-learn not installed in `.venv`) |
| System Python 3.11 (the notebooks' kernel) | `PYTHONPATH=src pytest tests/` excluding the Task B test | 77 passed, 1 failed: `test_installed_cli_and_imports`, because `safellm` is not pip-installed in that interpreter (environment, not code) |

`task_a.plotting` imports and applies its style under Python 3.11.

## Risks and follow-ups

- `matplotlib` and `scikit-learn` are used by Task A code but are not declared in `requirements.txt`; the analysis
  only runs in the system Python 3.11 environment. Not changed here.
- The Task B notebook path collision (above) needs resolving when Task B work is consolidated.
- The analysis notebooks contain markdown interpretation cells; they were kept as written.
