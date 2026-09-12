# Phase 0 validation — 2026-09-12

Environment: macOS, Python 3.14.5, local `.venv`, SafeLLM 0.1.0.

| Check | Observed outcome |
| --- | --- |
| `python -m pip install -r requirements.txt` | Editable package built and installed |
| `python -m unittest discover -s tests -v` | All 5 tests passed |
| `python -m pip check` | No broken requirements |
| `safellm doctor` | All four packages import; phase 0 reported |
| `safellm init-run --config configs/phase0.json --output-root /tmp/safellm-phase0-20260912` | Metadata record created; no research results |
| Directory integrity | All planned directories present (automated test) |
| Import from outside checkout | Passed using installed package in temporary working directory |

The first sandboxed installation could not resolve PyPI; an approved elevated
retry succeeded. Git initialization also required an approved elevated retry
because `.git` is protected by the workspace permissions.

Tests cover metadata preservation, refusal to overwrite existing run records,
unsafe identifier rejection, invalid seeds/metadata, nonfinite JSON values,
package imports and directory structure. They do not establish any NLP model
quality, dataset validity, or future ML dependency compatibility.

Phase 0 is complete. Phase 1 has not started. No Git remote is configured and no
push has been performed. Research-result folders remain empty.
