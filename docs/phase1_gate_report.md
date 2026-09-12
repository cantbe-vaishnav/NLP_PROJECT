# Phase 1 preliminary research gate report

2026-09-12. This is an audit checkpoint, not Phase 1 completion.

Implemented: candidate audit and concrete proposed label policy. Updated README
and experiment log. No dataset adapter or data-generation code implemented before
resolution of the policy. Dataset statistics and leakage findings are unavailable;
only potential risks from source documentation were identified.

Research decision: approve or revise BENIGN as non-adversarial (not necessarily
harmless), ADVERSARIAL as boundary manipulation, and quarantine context-ambiguous
examples. Recommended next step: resolve policy then continue Phase 1 source and
sample inspection. No dataset is finalized; no split or annotations exist.

## Exact local commands executed

| Command | Outcome |
| --- | --- |
| `cat /Users/vaishnavrmenon/Downloads/message.txt` | Read supplied Phase 1 brief |
| `git status --short --branch` | Clean `main` at audit start |
| `rg --files -g 'AGENTS.md' -g '!\.venv' -g '!\.git'` | No matching files |
| `cat configs/phase0.json` | Confirmed existing seed 42 configuration |
| `cat docs/experiment_log.md` | Confirmed Phase 0 history |
| `ls docs/task_a_dataset_audit.md` | Initially absent after a failed patch; corrected by adding the file |
| `.venv/bin/python -m unittest discover -s tests -v` | 5/5 passed |
| `.venv/bin/python -m pip check` | No broken requirements; non-blocking cache-permission warning |
| `.venv/bin/safellm doctor` | Python 3.14.5; imports OK; implemented CLI phase remains 0 |
| `git diff --check` | Passed |

Web search/open tools inspected the primary sources linked in the dataset audit.
No dataset download, data-quality computation, model training or external account
agreement was performed. No linter is configured. Existing tests check engineering
infrastructure only; their success does not mean the dataset is ready.

Commit subject for this checkpoint: `docs(task-a): audit candidates and identify label-policy gate`.
The commit hash is reported in the task response and available in Git history.

## Current gate update — account approval confirmed by user

This update supersedes the initial label-policy gate above. The user approved the
Task A policy and confirmed WildGuardMix access acceptance. Role-play, debater,
simulation, persona and hypothetical formulations must remain candidates; their
form alone never warrants exclusion. Ambiguous records must be retained for human
review, with original text/source labels intact.

Local authentication check: HF_TOKEN and HUGGING_FACE_HUB_TOKEN absent; neither the
standard cached token nor an explicitly configured token file exists. Credential
values were not read or printed. The only connected browser is the Codex in-app
browser; the actual dataset page shows it is signed out. Opened the site's login
link and left the tab available for user sign-in. Account approval in another
browser does not authenticate this browser or the Python downloader.

Selected corpus: none accepted; WildGuardMix remains preferred pending sample
inspection. Alternatives retain the decisions in phase1_access_gate_report.md;
role-play candidates are deferred/quarantined, not discarded by formulation.
Actual full WildGuardMix download: none. Prior Deepset preview: 100 rows (85 source
label-0, 15 source label-1), with no SafeLLM assignments. Quarantine/exclusion and
full duplicate/leakage counts remain uncomputed. No train/validation/test splits.
Hard-negative workflow exists; no accepted human-reviewed data. Unseen-formulation
and attack-category validity remain unestablished. Gate 1 is not passed.

Files modified at this checkpoint: this report only. Checks: `git status --short
--branch` (initially clean), credential-presence checks using inline Python
(all false), browser dataset/login state inspection, and `git diff --check`.
No code changed; the prior 10 passing tests remain the latest code validation.

Exact remaining action: user signs into the opened Codex in-app Hugging Face tab
with the approved account. No command-line work or token pasted into the task is
required. Then attempt authenticated download and resume the actual sample audit.
Commit subject: `docs(task-a): clarify authenticated access handoff and role-play policy`.
Prior tooling commit: 6f849aa (`feat(task-a): add source audit tooling and record access gate`).

## Latest update — browser access verified, local transfer unresolved

The signed-in dataset page now explicitly confirms access granted. Authentication
in the browser is resolved; do not ask the user to sign in again. Its preview shows
both harmful/adversarial-false and unharmful/adversarial-true rows. These observations
support separate source-label preservation but are insufficient for accepting the
mapping. Several long prompt previews are truncated; no full semantic audit claimed.

Clicked authenticated train and test download links and tried the supported link
media-download action. No resulting Parquet files were located in Downloads,
workspace, temporary directories or the checked Codex artifact locations. The
in-app browser's content export explicitly reports unsupported. No browser cookies
were extracted or repurposed. Local programmatic authentication remains absent.

Added `requirements-data.txt` (PyArrow 23.0.1),
`scripts/inspect_wildguard_files.py`, and `tests/test_wildguard_inspection.py`.
The inspector reports source schema, bytes/hash, row/null/duplicate counts and
original label distributions without assigning SafeLLM labels or changing text.
It rejects missing schema and refuses overwriting reports. Tests use synthetic
engineering fixtures only, not research data. These are pre-adapter source checks;
the adapter and actual label mapping remain deferred until full sample review.

Validation commands executed:
- `.venv/bin/python -m pip install pyarrow==23.0.1` — installed successfully.
- `.venv/bin/python -m unittest discover -s tests -v` — 13 tests passed, none skipped.
- `.venv/bin/python -m pip check` — no broken requirements.
- `.venv/bin/python -m compileall -q src scripts tests` — passed.
- `git diff --check` — passed.
PyArrow emitted sandbox CPU-information warnings and pip a cache-permission warning;
all checks completed successfully. No configured linter exists.

Current research status: WildGuardMix remains conditional, no corpus accepted.
Prior alternative decisions remain unchanged. Zero complete WildGuardMix source
files available locally; reported upstream 86,759 train / 1,725 test rows are NOT
verified local counts. Actual SafeLLM distributions, quarantine/exclusions, full
exact/near-duplicate and leakage statistics are uncomputed. No splits generated.
Hard-negative workflow exists, zero accepted examples. Neither unseen formulation
nor unseen attack-category holdouts established. Gate 1 remains unsatisfied.

Remaining action: download `wildguard_train.parquet` and `wildguard_test.parquet`
from the official source in a regular authenticated browser into Downloads (or
make local Hugging Face authentication available). This is a browser-to-filesystem
transfer limitation, not a research policy question. The agent will perform the
remaining local inspection/engineering; no routine user commands are requested.

Commit subject: `feat(task-a): prepare verified local Parquet inspection`.
Previous checkpoint: 657c0fb, `docs(task-a): clarify authenticated access handoff and role-play policy`.
