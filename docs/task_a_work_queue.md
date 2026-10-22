# Task A work queue

Updated: 2026-10-23.

| Phase | Task | Status |
|---|---|---|
| 1 | Commit and push outstanding Task A work | Done: `0175bbd` pushed to `origin/task-a-binary-dataset` ([report](task_a_phase1_commit_report.md)) |
| 2 | Review the 37 flagged JailbreakHub label candidates; record owner verification of the 174 corrections | Done: 11 retain, 22 recommend correction, 4 ambiguous; not applied ([report](task_a_label_review_report.md)) |
| 3 | RQ2 curated hard-negative benchmark and evaluation | Done: set frozen `d91b7f4`, evaluated ([report](task_a_rq2_report.md)); synthetic labels not independently validated |
| 4 | RQ3 held-out experiments | Done: A and B, 3 models each ([report](task_a_rq3_report.md)) |
| 5 | Repeated-seed robustness | Estimate given in [task_a_status_report.md](task_a_status_report.md); not started |

## Blockers and approvals needed

- Phase 5: repeated seeds (DistilBERT RQ1 + RQ3, about 2 h) need approval; not started.
- Phase 3 (optional): a human review of the synthetic CLS/ROL/META items and the 80 adversarial items would let the per-category RQ2 results be cited as validated.
- Phase 2 (optional): whether to apply any of the 22 recommended corrections as a v3 dataset. Not needed for Phase 3.

## Feedback

See [task_a_feedback_log.md](task_a_feedback_log.md). Open items: F6 (Task B publication, awaiting the owner's push approval), F7 (final report).
