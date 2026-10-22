# Task A feedback log

Owner instructions and feedback, newest last. Status: addressed / open / blocked / awaiting clarification.

| # | Date | Feedback | Phase | Status |
|---|---|---|---|---|
| F1 | 2026-10-22 | Secure and push Task A work to the matching origin branch; no force-push, no merge into `main`; preserve Task B scaffolding | 1 | Addressed (`0175bbd`) |
| F2 | 2026-10-22 | The 174 JailbreakHub label corrections were personally verified by the project owner; documentation must say so (supersedes the earlier "never claim human-verified" wording rule) | 2 | Addressed: results, dataset, error-analysis docs, experiment log and error-analysis notebook updated; build script, config, generated audits and training notebooks left as historical records (noted in `task_a_binary_dataset.md`) |
| F3 | 2026-10-22 | The 37 error-analysis candidates must not be described as human-verified; recommendations go in a separate auditable artifact; evaluation labels unchanged | 2 | Addressed: [task_a_label_review_report.md](task_a_label_review_report.md); no labels changed |
| F4 | 2026-10-22 | RQ3: stop for explicit approval before training or changing model selection | 4 | Addressed: approval received 2026-10-23 (F5) |
| F5 | 2026-10-23 | Approved: run RQ3 Experiments A and B with LogReg, SVM and DistilBERT-256; audit splits and leakage first; keep existing results unchanged; no Phase 5 seeds yet | 4 | Addressed: [task_a_rq3_report.md](task_a_rq3_report.md) |
| F6 | 2026-10-23 | Part B: publish completed Task B work on its own branch, separate from Task A; resolve the `task_b_fever_baselines.ipynb` path conflict preserving both versions; show branch, commit range, staged files, conflict resolution and tests before any push | B | Prepared on branch `task-b-claim-verification` (separate worktree); push awaiting owner approval |
| F7 | 2026-10-23 | Part C: report Phase 4 results, Task B branch and push status, RQ4 status, UI/integration status, remaining tests and deliverables; do not claim the project is finished | C | Open |
