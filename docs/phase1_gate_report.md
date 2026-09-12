# Phase 1 gate report — actual WildGuardMix source audit

Status: **Gate 1 NOT passed**. Access and local transfer are resolved. No model,
Task B, integration or UI work performed. No SafeLLM label mapping accepted yet.

## Sources and provenance

User supplied both official Parquet files in `data/` and `data/raw/`. Copies are
byte-identical; use `data/raw/`. All Parquet copies are ignored by Git, retained
locally without deletion. Full SHA-256 values and actual schemas are in
`results/data_audit/wildguard_source_inspection.json` and `wildguard_full_audit.json`.
The referenced upstream revision is d29c47f41c8b51348b5c8e8c81c039b3132b66d1.
Local hashes are recorded; they have not independently been compared to upstream
LFS hashes. The source card declares ODC-BY; the user accepted its access terms.
Source: https://huggingface.co/datasets/allenai/wildguardmix

WildGuardMix is selected for source/semantic audit, **not accepted as a labeled
training corpus**. Deepset remains a diagnostic candidate with context-dependent
labels. WildJailbreak is deferred for similar semantics and additional provenance
inspection. JBB/HarmBench behavior-only positive mappings are rejected because a
harmful goal alone does not establish manipulation; separate artifacts are not
ruled out. Role-play candidates from any source are retained, not discarded by form.

## Actual counts

| Measure | Official train | Official test |
| --- | ---: | ---: |
| Rows | 86,759 | 1,725 |
| Bytes | 53,744,450 | 2,258,878 |
| Source adversarial=true | 40,956 | 810 |
| Source adversarial=false | 45,803 | 915 |
| Source harmful | 46,216 | 754 |
| Source unharmful | 40,543 | 945 |
| Missing source harmfulness | 0 | 26 |
| Empty/invalid prompt rows | 14 | 0 |

These are source labels, **not SafeLLM labels**. All adversarial values are boolean;
prompt columns are strings with no nulls. Fourteen training strings are empty.
Train has 48,825 null responses, whereas refusal/harm labels have 48,783 nulls;
response fields are irrelevant to Task A inputs and remain untouched. Missing
harmfulness is not an automatic reason to reject a prompt's manipulation label.
All original text and metadata remain in the unchanged source artifacts.

No rows have yet been deleted or assigned final SafeLLM labels. Twenty sampled
training rows are pending human review, not twenty confirmed ambiguous examples.
The full corpus's ambiguity/quarantine count is not known.

## Duplicate, template and source findings

Among 88,470 nonempty rows, there are 49,576 distinct exact prompt strings and
38,894 duplicate excess rows in 18,914 repeated groups. The separate raw-file
inspection counts 38,907 training duplicate excess rows including repeated empty
strings; these definitions explain the difference. No exact-string cross-official-
split overlap and no exact/normalized groups with conflicting adversarial flags
were found. Other label disagreements are not evaluated by this conflict check.

NFC + casefold + whitespace comparison (never model-text preprocessing) leaves
49,527 keys. One key spans train/test: training row indices 3193, 3194 and 3367
match test index 675 up to capitalization (United Nations headquarters query).
Retain test membership and exclude these training copies before any modeling.
No changes to membership have been made at this gate.

The bounded adjacent-sorted comparison using 5-word shingles at Jaccard >= 0.85
found 133 near-duplicate candidate pairs. None of those representative pairs spans
train/test, but this is a low-recall diagnostic, NOT an exhaustive clearance.
Multiple group members can have different official memberships; representative
pair flags alone cannot certify group-level isolation. Broader template/family
checks remain required before final splits. Threshold is an audit parameter, not
an approved split/grouping rule. Pair IDs are saved in interim data.

Actual schema contains no source-corpus ID, parent prompt ID, template ID, or
attack-method category. `subcategory` is a risk topic and must not become an attack
category. Original component-source confounding cannot be measured directly from
this release's schema. Source/style shortcuts and repeated synthetic structures
remain risks; absence of metadata is not evidence of independence.

## Semantic audit and human-review gate

Using seed 42, sampled five training rows from each source adversarial/harmfulness
combination (20 total); full prompts were inspected by AI. Sampling is by source
row, so repeated prompt variants may bias it. This small diagnostic is not an
estimate of corpus-wide label error and is not independent human annotation.

Concrete source-true examples that challenge direct mapping:

- train:23270 asks for restrained creative writing and explicitly maintains ethical
  limits. No clear boundary override is present in the inspected text.
- train:27364 requests lawful journalistic research and explicitly respects limits.
- train:39554 requests a business-leadership persona exercise without a clear bypass.
- train:48490 explicitly asserts OpenAI policies do not apply: the boundary claim,
  not its fictional setting, is the relevant signal.
- train:15397 explicitly asks to disregard safeguards: adversarial intent is clear.
- train:51657 includes vague disregard for repercussions while requesting a public
  tourism website; retain for contextual review rather than force a label.

These are diagnostic judgments, not applied labels. The source flag cannot be
accepted wholesale under the user-approved definition. Do not fix this with a
keyword filter or blanket exclusion of role-play or source-unharmful rows.

**Recommended next decision:** authorize a human semantic-validation pilot before
accepting a mapping: sample 200 unique training prompts (50 per source-flag /
harmfulness stratum where available), have two team members independently apply
the already-approved policy, preserve ambiguity, and adjudicate disagreements.
Use findings to decide whether to curate/reannotate a manageable corpus or audit
an alternative. This would define a new annotation procedure, so it needs review.
The existing 20-row queue is a starting diagnostic, not this proposed pilot.

## Remaining deliverables

Final normalized corpus and SafeLLM distribution: not available. Train/validation/
test setup: not generated; official test remains untouched. Seed 42 is recorded.
Adapter/label normalization and split code remain deferred until semantic mapping
is defensible. Source inspection utilities do not constitute an accepted adapter.

Hard negatives: workflow exists; no examples automatically accepted or falsely
claimed human-reviewed. Some flagged benign-content candidates may eventually
qualify after review. Unseen formulations: no verified families yet, so not ready.
Unseen attack categories: not supported by the current risk-category metadata;
no category holdout constructed. Gate 1 is not satisfied by code tests alone.

## Files and validation

Added config, source-leakage helpers, full audit/verification scripts, five tests,
source/full JSON reports and locally ignored review/pair queues. Updated README,
experiment log, this report and Git ignore rules.

Exact routine commands executed:

```bash
.venv/bin/python scripts/inspect_wildguard_files.py --train data/raw/wildguard_train.parquet --test data/raw/wildguard_test.parquet --output results/data_audit/wildguard_source_inspection.json
.venv/bin/python scripts/audit_wildguard.py --config configs/task_a_full_audit.json
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m pip check
.venv/bin/safellm doctor
.venv/bin/python -m compileall -q src scripts tests
git diff --check
.venv/bin/python /tmp/safellm_verify_audit.py
```

The full audit initially failed on an incorrect `st_size()` call, which was fixed;
the same audit command was rerun successfully. **18 tests passed**, dependencies,
imports and syntax checks passed. Benign sandbox CPU/cache warnings were emitted.
A second full run in temporary paths reproduced statistics, sample queue and pairs
exactly. The verification code is retained as `scripts/verify_wildguard_audit.py`.
Inline Python also compared duplicate file hashes and printed sampled prompts and
cross-split overlap members. No linter is configured. No ML metrics were generated.

Commit subject: `feat(task-a): audit full source data and identify semantic review gate`.
The commit hash is reported in the task response. Prior checkpoint: d3965a4.
