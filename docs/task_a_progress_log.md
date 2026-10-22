# Task A progress log

## 2026-10-22

- Phase 1 complete. Committed figures, plotting module and results-doc figure index (`0175bbd`); pushed
  `task-a-binary-dataset` (new remote branch, including the previously unpushed `11176fc` and `47b38c8`).
  Task B scaffolding and source-label crosstab outputs left untracked. Report:
  [task_a_phase1_commit_report.md](task_a_phase1_commit_report.md).
- Phase 2 complete. Docs now state the 174 corrections were verified by the project owner. The 37 error-analysis
  candidates were reviewed (model-assisted, not human-verified): 11 retain, 22 recommend correction (16 attack→benign,
  mostly FlowGPT character cards; 6 benign→attack, DAN/NRAF-style templates), 4 ambiguous. Nothing applied.
  Report: [task_a_label_review_report.md](task_a_label_review_report.md).
- Phase 3 complete. Built a hard-negative benchmark: 240 synthetic benign + 80 matched synthetic attacks (LLM-authored,
  8 categories, pilot then scale-up, not independently validated) and NotInject (339, MIT). Frozen before scoring
  (`d91b7f4`); inference reproduced saved predictions exactly. Benign FPR 4–6% (1–3% without cues, 17–33% for quoted
  attacks); matched-attack recall 25–49%. Report: [task_a_rq2_report.md](task_a_rq2_report.md).
- Phase 4 plan saved, stopped for approval. Metadata supports an unseen *harm-topic* split (WildGuardMix subcategory)
  and an unseen *source* split, not an unseen attack-technique split. Proposed: hold out `cyberattack` with keyword
  closure (533 held-out rows) plus a WildGuardMix-only companion run. Plan: [task_a_rq3_plan.md](task_a_rq3_plan.md).

## 2026-10-23

- Phase 4 complete (approved). Run in a separate worktree of `task-a-binary-dataset` (the main checkout is on the
  owner's `consolidation` branch). A (unseen `cyberattack` topic): recall 1.000 for all models; FPR on harmful
  direct requests 5.2–5.5% TF-IDF, 24.5% DistilBERT. B (no JailbreakHub in training): JailbreakHub test macro-F1
  0.79–0.82 → 0.46–0.47. About 40 min of compute. Existing results verified unchanged.
  Report: [task_a_rq3_report.md](task_a_rq3_report.md).
