# Task A work queue

Updated: 2026-10-22.

| Phase | Task | Status |
|---|---|---|
| 1 | Commit and push outstanding Task A work | Done: `0175bbd` pushed to `origin/task-a-binary-dataset` ([report](task_a_phase1_commit_report.md)) |
| 2 | Review the 37 flagged JailbreakHub label candidates; record owner verification of the 174 corrections | Done: 11 retain, 22 recommend correction, 4 ambiguous; not applied ([report](task_a_label_review_report.md)) |
| 3 | RQ2 curated hard-negative benchmark and evaluation | Done: set frozen `d91b7f4`, evaluated ([report](task_a_rq2_report.md)); synthetic labels not independently validated |
| 4 | RQ3 held-out-category plan | **In progress (planning only)**; owner approval required before any training |
| 5 | Repeated-seed robustness (cost/benefit estimate first) | Optional, not started |

## Blockers and approvals needed

- Phase 4: approval of the held-out-category experiment plan before training.
- Phase 3 (optional): a human review of the synthetic CLS/ROL/META items and the 80 adversarial items would let the per-category RQ2 results be cited as validated.
- Phase 2 (optional): whether to apply any of the 22 recommended corrections as a v3 dataset. Not needed for Phase 3.

## Feedback

See [task_a_feedback_log.md](task_a_feedback_log.md). Open items: F4 (RQ3 approval gate, applies in Phase 4).
