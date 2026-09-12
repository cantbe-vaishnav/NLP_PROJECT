# Task A semantic-validation pilot guidelines

## Purpose and independence

This pilot tests whether WildGuardMix's `adversarial` field matches SafeLLM's
input-safety target. It does not measure model performance. Reviewer 1 completes
`data/annotations/task_a_pilot_reviewer_1.csv`; reviewer 2 independently completes
`data/annotations/task_a_pilot_reviewer_2.csv`. Reviewers must not view the master
file, source labels, or each other's decisions until both files are complete.

Every CSV contains 200 prompts and these editable columns:

- `safellm_label`: exactly `ADVERSARIAL`, `BENIGN`, or `QUARANTINE`.
- `reviewer_id`: use the same stable team identifier on all 200 rows, such as
  `member-1` or `member-2`; do not put names or email addresses in Git.
- `rationale`: one short prompt-specific reason identifying the requested action
  and whether it crosses an instruction or safety boundary.

Do not edit `pilot_id` or `prompt`, reorder rows, insert rows, or delete rows.
Spreadsheet applications may alter CSV punctuation or encoding; save as UTF-8
CSV and verify that multiline prompts remain one record.

## Labels

`ADVERSARIAL` means the prompt attempts to bypass safeguards or redirect an
established instruction or trust boundary. Clear examples include asking the
model to ignore prior instructions, disable or evade safeguards, reveal protected
instructions, or use framing as a mechanism to obtain otherwise restricted action.

`BENIGN` means non-adversarial for Task A. It does not mean harmless, ethical,
accurate, or permissible. A direct harmful request without manipulation can be
BENIGN under this specific task definition. The project may apply a separate
harmfulness guardrail later.

`QUARANTINE` means the available prompt does not provide enough context for a
defensible binary decision, or its relationship to an established boundary is
genuinely ambiguous. Explain what missing context or ambiguity prevents judgment.
Do not use QUARANTINE merely because a prompt is long, disturbing, or difficult.

Role-play, debate, simulation, personas, hypotheticals, creative writing,
educational framing and security discussion are candidate content, not automatic
labels. Decide whether the formulation actually functions as boundary manipulation.
Quoted attacks are not automatically adversarial; consider what the current prompt
asks the assistant to do with the quoted material. Harmful subject matter alone
never establishes ADVERSARIAL.

## Completion and analysis

Each reviewer must label all 200 rows independently. The analysis command requires
two distinct reviewer IDs and rejects missing IDs, labels, rationales, duplicates,
or changed ID sets. It calculates three-class agreement and Cohen's kappa,
per-stratum disagreement, and a cross-tab between source adversarial status and
agreed human labels. It queues every disagreement and any QUARANTINE decision for
human adjudication without resolving it.

After both reviewers finish, the engineering workflow runs:

```bash
.venv/bin/python scripts/analyze_task_a_semantic_pilot.py \
  --reviewer-1-id member-1 --reviewer-2-id member-2
```

Reviewer IDs in the command must exactly match the CSV values. The analysis does
not itself decide direct, curated, or rejected use of WildGuardMix. That research
decision follows review of the measurements and systematic mismatch examples.

Annotation files are ignored by Git because they contain licensed prompt text.
The configuration, generator, analysis code, tests and aggregate results can be
versioned. Do not commit prompt text unless licensing and repository policy are
explicitly reviewed.
