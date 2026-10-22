# Task A status report

Updated: 2026-10-22. Branch `task-a-binary-dataset` (pushed; not merged into `main`).

## Completed and measured (backed by saved evaluation outputs)

- RQ1: four models on dataset v2, both test sets scored once ([task_a_results.md](task_a_results.md)).
- RQ7: validation-chosen thresholds ([task_a_results.md](task_a_results.md), threshold notebook).
- Error analysis and proxy slices ([task_a_error_analysis.md](task_a_error_analysis.md)).
- RQ2 on a frozen hard-negative benchmark ([task_a_rq2_report.md](task_a_rq2_report.md)): measured FPR,
  precision/recall/F1, AUROC and per-category rates. Inference reproduces the saved RQ1 predictions exactly.

## Completed but not independently validated

- RQ2 synthetic benchmark labels: LLM-authored and LLM-labelled; no independent human review.
- NotInject labels: its authors' (LLM-generated with manual filtering, per its paper); not re-checked here.
- Review of the 37 JailbreakHub label candidates: model-assisted recommendations (11 retain, 22 correct,
  4 ambiguous), not applied ([task_a_label_review_report.md](task_a_label_review_report.md)).
- Most JailbreakHub labels are unreviewed source labels. The 174 applied corrections were verified by the
  project owner.

## Partially completed

- RQ3: similarity-bin proxy only. A held-out experiment is designed but not run
  ([task_a_rq3_plan.md](task_a_rq3_plan.md)).

## Awaiting owner approval

- RQ3 Experiments A (unseen harm category `cyberattack`) and B (unseen source); about 1–1.5 h of compute.
- Optional: apply any of the 22 recommended label corrections as a dataset v3.
- Optional: human review of the synthetic RQ2 items (CLS/ROL/META and the 80 attacks).

## Optional extensions (Phase 5, not started)

- Repeated seeds. TF-IDF models are deterministic (liblinear), so seeds add nothing there. DistilBERT-256 with
  3 extra seeds costs about 1 hour on the RTX 4060. That would put error bars on RQ1's small official-test
  differences (1–4 errors between models) and on the RQ3 degradation. Worth doing after RQ3 if time allows;
  not started without approval.

## Records

Work queue [task_a_work_queue.md](task_a_work_queue.md) · feedback [task_a_feedback_log.md](task_a_feedback_log.md)
· progress [task_a_progress_log.md](task_a_progress_log.md) · Phase 1 [task_a_phase1_commit_report.md](task_a_phase1_commit_report.md)
