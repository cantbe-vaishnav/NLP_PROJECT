# Task A annotation agreement pilot

Two sets of artifacts, both derived from the same three reviewer files:

- `prior_analysis/` — **verbatim copy** (15 files, SHA-256 verified) of the existing
  analysis folder found at `Desktop/Aadit/N025/prac/NLP/Project/outputs/annotation_agreement_pilot/`.
  Produced by a separate session; kept for reference and not edited. The whole folder
  is Git-ignored: its `disagreement_table.csv` contains licensed prompt excerpts, and it
  holds a standalone analysis script and an earlier proposed diff that are not part of
  this repository's pipeline and were not applied. The later `proposed_schema_update_v3.diff`
  and `VERIFICATION_v3.md` remain untouched in the original folder and were reconciled
  against this branch rather than applied.
- `recomputed/` — produced by this repository's `scripts/analyze_task_a_semantic_pilot.py`:
  `agreement_results.json` and `agreement_report.md` (aggregate), plus
  `disagreement_table.csv` (pilot ID, pattern, category, each reviewer's label and
  rationale; no prompt text). The table is Git-ignored because rationales are annotation
  content; remove the ignore entry only with explicit authorization.

The repository script's statistics equal the prior analysis exactly (see below).

## Inputs (read only, not modified)

| Reviewer | File | SHA-256 |
|---|---|---|
| 1 | `Desktop/Aadit/N025/prac/NLP/Project/task_a_pilot_reviewer_1_FINAL.csv` | `be6ac33ee823fd7a6dbbea11854f15cf5d9039a0e650a4920dbac38e7fe3f35e` |
| 2 | `Desktop/Aadit/N025/prac/NLP/Project/reviewer2_corrected.xlsx` | `34b8fdac00becf607a41a1306ba34829c58c78dad1b245ec0a472eb73f72f6c3` |
| 3 | `Desktop/Aadit/N025/prac/NLP/Project/reviewer3_corrected.xlsx` | `18d26d52563e61db2b25b303f09655fb495a479ba8bd436d5b7ea7348515eef0` |

200 rows each, identical pilot IDs, row order and prompt text.

## Label schema

Four labels, kept separate: `BENIGN`, `HARMFUL`, `ADVERSARIAL`, `QUARANTINE`
(see `docs/task_a_semantic_pilot_guidelines.md`). Nothing is collapsed.

## Methods

Pairwise Cohen's kappa and raw agreement, Fleiss' kappa, 4x4 confusion matrices,
unanimous / two-versus-one / three-way counts, label distributions and `QUARANTINE`
usage. Regenerate with `scripts/analyze_task_a_semantic_pilot.py`.

## Limitations

- **Reviewer independence is owner-confirmed, not independently audited.** The project
  owner confirms the three reviewers annotated independently, without seeing or
  influencing one another's annotations; the repository cannot verify this.
  Observations that remain: Reviewer 1's rationales contain
  review-dialogue language (21 say "Agree with your label"; 3 say "Revised from my
  earlier ..."), Reviewer 2's rationales are repeated generic sentences (4 distinct
  across 200 rows), and file timestamps alone do not establish independence. Results
  are observed agreement among the submitted annotations.
- No disagreement has been adjudicated; no annotations were generated or edited.
- The source-label comparison and per-stratum disagreement table were run locally on
  2026-10-20 as descriptive counts only. They are not committed to this repository, and
  source labels are not ground truth (`docs/task_a_source_label_comparison.md`). The
  agreement figures in this folder were produced without the master, which is recovered
  locally at `data/annotations/task_a_pilot_master.jsonl` (untracked, Git-ignored,
  excluded from commits).
- 200 prompts stratified by source label; rates do not estimate corpus rates.
- File-version provenance of Reviewers 2/3 is unresolved (see the guidelines).

## Reproduce

See the exact command in `docs/task_a_semantic_pilot_guidelines.md`. The run produced
here used the three paths in the table above via `--reviewer-file`.
