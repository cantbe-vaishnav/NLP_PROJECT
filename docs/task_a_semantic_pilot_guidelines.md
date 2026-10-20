# Task A annotation guidelines and semantic-validation pilot

## Canonical schema

Task A uses one four-label schema. It is the only supported Task A annotation
schema; the earlier three-label guidelines (`ADVERSARIAL`, `BENIGN`, `QUARANTINE`)
are superseded and no three-label workflow is retained.

| Label | Meaning |
|---|---|
| `BENIGN` | Non-adversarial. Does not necessarily mean harmless. |
| `HARMFUL` | Harmful or problematic content without sufficiently evidenced attempts to manipulate or circumvent a higher-priority instruction or safety boundary. |
| `ADVERSARIAL` | An attempt to manipulate, override, or circumvent higher-priority instructions or safety boundaries, regardless of whether the requested content is harmful. |
| `QUARANTINE` | Insufficient context or genuine ambiguity prevents a reliable decision. |

Task B's `SUPPORTED`, `CONTRADICTED` and `UNSUPPORTED` labels are separate and
unchanged.

Guidance:

- Harmful subject matter alone never establishes `ADVERSARIAL`; a direct harmful
  request without evidenced manipulation is `HARMFUL`.
- `ADVERSARIAL` applies even when the manipulation seeks harmless content.
- Role-play, debate, simulation, personas, hypotheticals, creative writing,
  educational framing and security discussion are candidate content, not automatic
  labels. Decide whether the formulation actually functions as boundary
  manipulation. Quoted attacks are not automatically adversarial; consider what the
  current prompt asks the assistant to do with the quoted material.
- `QUARANTINE` must explain what missing context or ambiguity prevents judgment.
  Do not infer missing context, and do not use it merely because a prompt is long,
  disturbing, or difficult.
- Priority order is system over developer over user instructions; a claimed
  administrator role or fake system announcement does not raise a message's priority.
- The four labels are analysed separately. They are never collapsed (for example
  `HARMFUL` into `BENIGN` or `ADVERSARIAL`) to improve agreement.

## Pilot files

The pilot tests whether WildGuardMix's `adversarial` field matches SafeLLM's
input-safety target. It does not measure model performance. Three reviewers each
complete one file of 200 prompts (`configs/task_a_semantic_pilot.json`). Editable
columns:

- `safellm_label`: exactly one of the four labels above.
- `reviewer_id`: the same stable identifier (`1`, `2` or `3`) on all 200 rows; no
  names or email addresses in Git.
- `rationale`: one short prompt-specific reason identifying the requested action and
  whether it crosses an instruction or safety boundary.

Do not edit `pilot_id` or `prompt`, reorder, insert or delete rows. Reviewers should
not view the master file, source labels, or each other's decisions until all files
are complete. Completed annotation files are never modified by tooling.

## Analysis

The config lists the completed files under `analysis_reviewers` (by default
`data/annotations/`). The actual files currently live outside the repository, so pass
their paths explicitly (originals are only read, never moved or renamed). Reviewer 1
is a CSV; Reviewers 2 and 3 are XLSX:

```bash
.venv/bin/python scripts/analyze_task_a_semantic_pilot.py \
  --reviewer-file "1=<dir>/task_a_pilot_reviewer_1_FINAL.csv" \
  --reviewer-file "2=<dir>/reviewer2_corrected.xlsx" \
  --reviewer-file "3=<dir>/reviewer3_corrected.xlsx"
# optional: --output-dir DIR  --include-prompts  --source-crosstab (needs the local master)
```

Reviewer files may be `.csv` or `.xlsx` (the first sheet is read). The command
requires exactly three reviewers whose files contain exactly the expected 200 pilot
IDs (`pilot-001` to `pilot-200`, in order; `expected_items` in the config), identical
prompt text, valid labels, matching `reviewer_id` values and non-empty rationales, so
identically truncated files are rejected.
It reports pairwise Cohen's kappa and raw agreement, Fleiss' kappa, confusion
matrices, unanimous / two-versus-one / three-way counts, label distributions,
`QUARANTINE` usage and a per-item disagreement table (pilot ID, each reviewer's
label and rationale). Prompt text is omitted from the table unless
`--include-prompts` is given, because the prompts are licensed. It never overwrites
existing outputs and never adjudicates.

## Independence status

Reviewer independence is **owner-confirmed, not independently audited**. The project
owner confirms the three reviewers annotated independently, without seeing or
influencing one another's annotations. The repository cannot verify this. Reviewer 1's
rationales contain review-dialogue language, Reviewer 2's rationales are repeated
generic sentences, and file timestamps alone do not establish independence; these
observations are retained. Reported statistics are observed agreement among the
submitted annotations. Rationales must not be rewritten. Nothing here is adjudicated,
and no reviewer is treated as correct.

## Known limitations and provenance (recorded 2026-10-18)

- Reviewer 1's final file has 21 rationales containing "Agree with your label" and 3
  containing "Revised from my earlier ...". The owner confirms the file was produced
  independently; that confirmation is not audited, and the rationale language is
  preserved as recorded. Reviewer 2's rationales are four fixed sentences (one per label), so they
  hold no prompt-specific evidence; a fixed sentence per label does not satisfy the
  rationale requirement. Existing rationales are preserved unchanged.
- `task_a_pilot_master.jsonl` has been recovered locally at
  `data/annotations/task_a_pilot_master.jsonl`. It is untracked, Git-ignored (it holds
  raw licensed prompts) and excluded from commits. The source-label comparison and
  per-stratum disagreement table were run locally on 2026-10-20 as descriptive counts
  only. They are not committed to this repository, and source labels are not ground
  truth.
- File-version uncertainty: a Downloads file named `task_a_pilot_reviewer_2_completed
  (1).xlsx` has the same label sequence as `reviewer3_corrected.xlsx`, while
  `reviewer2_corrected.xlsx` and `reviewer3_corrected.xlsx` differ on 70 of 200 items
  (as does the pair uploaded elsewhere, per the project owner). These may be different
  versions of the files; the analysed files are identified only by SHA-256 (see
  `outputs/annotation_agreement_pilot/README.md`). Provenance is unresolved.
- Recommendation, if feasible: a blind re-annotation with prompt-specific rationales
  and no reviewer able to see another's labels. The pipeline does not wait for it.

## Source labels

Source-dataset labels are not ground truth for the SafeLLM scheme. Any comparison is
separate from inter-annotator agreement; see
[task_a_source_label_comparison.md](task_a_source_label_comparison.md).

Annotation files are ignored by Git because they contain licensed prompt text.
Configuration, generator, analysis code, tests and aggregate results can be
versioned. Do not commit prompt text unless licensing and repository policy are
explicitly reviewed.
