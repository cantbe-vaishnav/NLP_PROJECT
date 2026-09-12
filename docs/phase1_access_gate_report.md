# Phase 1 access and source-selection gate — 2026-09-12

Gate 1 is NOT satisfied. Approved label definitions remain in force. No training,
Task B or UI work performed. This report supersedes the prior label-policy gate.

## Source and sample observations

| Candidate | Current decision and observed evidence |
| --- | --- |
| WildGuardMix | Preferred, not accepted: public metadata HTTP 200, `gated=auto`; pinned training file HEAD returns HTTP 401. No `HF_TOKEN`, standard cached token, or `HF_HOME` configured. Cannot inspect actual rows yet. Card declares ODC-BY and requires user agreement/contact information. |
| Deepset | Deferred as primary: public preview retrieved, actual schema `text:string`, `label:int64`. Multiple positive examples are context-dependent under approved policy. Do not force mapping or use as a convenient substitute. Metadata declares Apache-2.0. |
| WildJailbreak | Deferred: metadata confirms gated access; label-type semantics and parent/tactic leakage still require actual sample audit. ODC-BY declaration recorded. |
| JBB-Behaviors | Behavior-only positive mapping rejected: harmful goals do not establish manipulation. Separate jailbreak artifacts remain unaudited. |
| HarmBench | Behavior-only mapping rejected; generated artifacts remain deferred pending provenance/schema audit. |

See `task_a_dataset_audit.md` for primary-source links. Actual representative
sample audits of gated candidates have NOT occurred. No dataset label mapping
has been accepted. This audit does not claim every possible alternative exhausted.

## Actual downloaded material and statistics

Only public metadata and a bounded Deepset preview were retrieved, not full
corpora. The preview contains 100 training rows in 14,511 response bytes. Source
labels: 85 label-0 / 15 label-1; these are NOT SafeLLM labels. No missing/empty text
or exact duplicate excess among these 100 rows. Character lengths range 14–448.
The first-rows API is not revision-pinned and its first 100 rows are not a random
or representative population sample. Response and row hashes are saved. This
preview cannot be used as a reproducible final corpus or as a class-balance estimate.

AI inspection covered all 15 positive preview rows and 12 negative rows (indices
0, 1, 7, 15, 19, 23, 31, 50, 65, 83, 94, 99). Concrete problematic positive indices:
42 (ordinary debater role), 78 (terminal simulation), 89 (brand role-play), and
10/38/43/69 (topic/role changes without supplied boundary context). These are
quarantine candidates, not relabeled negatives. Positive indices 4/70/80 contain
explicit redirection/disclosure wording. Label-0 index 19 illustrates why source
non-injection must not be represented as harmlessness. No human review claimed.

Potential template similarity is visible at indices 4 and 80. Near-duplicate,
family and cross-split leakage checks on the full corpus have NOT been performed.
No claim of leakage-free data is made.

Final normalized size and SafeLLM label distribution: unavailable. Train,
validation and test splits: not generated. Official test rows have not been moved.
Hard negatives: review format/workflow documented, zero accepted examples.
Unseen formulations: unestablished pending parent/template inspection.
Unseen categories: unestablished; risk topics are not attack categories.

## Engineering delivered and checks

- Configurable public source probe, pinned WildGuard access URL, snapshot hashes,
  actual schema/statistics and raw-preview storage under Git-ignored interim data.
- Sample audit utility that preserves source labels and text, plus five tests.
- Hard-negative workflow with null labels, explicit reviewer identity/type and
  quarantine; final acceptance procedure remains a later human research decision.
- README, approved-policy audit and experiment log updated.

Commands executed:

| Command | Result |
| --- | --- |
| `git status --short --branch` | Initially clean main |
| `cat docs/task_a_dataset_audit.md` | Read prior audit |
| `cat pyproject.toml` | Read installed package setup |
| `.venv/bin/python /tmp/safellm_probe.py` | First probe encountered certificate errors; no TLS bypass used |
| `.venv/bin/python scripts/audit_task_a_sources.py` | Initial retry used system CA bundle and retrieved metadata/preview; observed 401 |
| `.venv/bin/python scripts/audit_task_a_sources.py --ca-file /etc/ssl/cert.pem` | Final configurable probe succeeded; recorded 401 as an access observation |
| `.venv/bin/python -m unittest discover -s tests -v` | All 10 tests passed |
| `.venv/bin/python -m pip check` | No broken requirements; nonblocking pip cache warning |
| `.venv/bin/safellm doctor` | Imports OK, Python 3.14.5; CLI implementation remains Phase 0 |
| `.venv/bin/python -m compileall -q src scripts tests` | Passed |
| `git diff --check` | Passed |

Additional inline Python inspection printed selected preview rows and source-label
counts and checked credential presence as booleans only. No secrets were printed.
Statistics are regenerated by the saved probe. No linter is configured. The
recorded 401 is not a dataset-quality pass and does not satisfy Gate 1.

## Required next action

The user must accept access conditions for `allenai/wildguardmix` on Hugging Face
and make authorized access available locally, or explicitly select an ungated
alternative audit direction. Do not send tokens in task messages. I cannot accept
personal attestations or supply the user's affiliation/contact details for them.
After access, inspect actual samples before accepting the candidate; then proceed
with adapters, cleaning, grouping and splits. These remain incomplete rather than
implemented against unverified assumptions.

Commit subject: `feat(task-a): add source audit tooling and record access gate`.
Hash is reported in the task response and Git history.
