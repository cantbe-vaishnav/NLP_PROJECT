# Task A source-label comparison: mapping and limitations

Status: documented before use. Not reported in any result yet; the local master
JSONL needed to run it was not available when this was written.

## Source labels

WildGuardMix provides a boolean `adversarial` flag and a `prompt_harm_label`
(`harmful` / `unharmful`). These were defined by the dataset authors for their own
purposes. They are **not ground truth** for the SafeLLM four-label scheme.

## No implicit mapping

`HARMFUL` is **not** treated as non-adversarial, and no four-label to boolean
collapse is applied. A binary mapping would force a choice about `HARMFUL` and
`QUARANTINE` that the project has not made, and any such choice changes the result.

## What is implemented

`task_a.semantic_pilot.source_label_crosstab` (enabled with `--source-crosstab`)
produces a descriptive table only: for each reviewer, the count of each of the four
labels within source `adversarial = true` and `adversarial = false`. It computes no
mismatch rate, no accuracy, and no "agreement with source".

## Limitations

- The pilot is 50 prompts per source adversarial × harmfulness stratum, so its
  marginal rates do not estimate corpus-wide rates.
- A reviewer disagreeing with the source flag is not evidence the flag is wrong.
- Reviewer independence is owner-confirmed, not independently audited, so cross-tab
  counts inherit that limitation.
- Any later binary comparison needs an explicitly documented, approved mapping for
  `HARMFUL` and `QUARANTINE` (including reporting results under each alternative)
  before it is implemented or reported.
