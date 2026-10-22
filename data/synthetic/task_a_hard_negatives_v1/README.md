# Task A synthetic hard negatives v1 (source files)

Project-authored evaluation prompts for RQ2. **Synthetic and LLM-authored** (written by Claude, an AI model,
during a delegated Task A session on 2026-10-22); not naturally occurring, not independently human-annotated.
Evaluation only: never used for training, model selection or threshold choice.

One file per category. Each item starts with a header line:

```
=== <id> | <category> | <structure> | <label> | <paired id or ->
<prompt text, one or more lines>
```

Labels: 0 = BENIGN (hard negative), 1 = ADVERSARIAL (matched counterpart). Labelling rules, categories and
checks: `docs/task_a_rq2_report.md`. Build: `scripts/build_hard_negative_set.py`.
