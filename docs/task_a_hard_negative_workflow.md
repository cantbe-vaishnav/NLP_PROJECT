# Task A hard-negative review workflow

Status: infrastructure only. No human-reviewed examples exist.

BENIGN means non-adversarial, not safe or harmless. A hard negative discusses,
analyzes or quotes attacks without attempting to redirect the current model's
instruction boundary. Do not assign labels from security keywords alone.

Use one JSON object per candidate with these fields:

```json
{
  "id": "unique-candidate-id",
  "prompt": null,
  "context": null,
  "source_url": null,
  "source_license": null,
  "source_harmfulness_label": null,
  "authorship": null,
  "reviews": [],
  "status": "pending",
  "label": null,
  "adjudication": null
}
```

This is a format example, not a data row. Record actual text and provenance when
collecting candidates; synthetic authorship must be explicitly identified.
Each review records actual reviewer ID, human/AI reviewer type, date, proposed
label (BENIGN/HARMFUL/ADVERSARIAL/QUARANTINE), context adequacy, and reasoning about what the
prompt asks the model to do. Unknown context or unresolved intent is labeled
QUARANTINE, one of the four canonical Task A labels (see
task_a_semantic_pilot_guidelines.md).

Do not mark AI review as human review. Keep original reviews and any adjudication
separately. Before accepting this evaluation set, the team must approve its
review/acceptance procedure and record completed reviews. No mandatory reviewer
count or agreement threshold is silently imposed here.

Retain parent/template references when known so quoted attacks and their source
templates can be checked against training data. Keep this diagnostic set separate
from training and standard test data. Do not generate labels or metadata merely
to fill missing fields.
