# Task A pilot: prompt-encoding audit (draft, untracked)

Read-only audit of the five pilot prompts whose text differs between the local master
(`data/annotations/task_a_pilot_master.jsonl`, SHA-256 `0ea00e6e…81f01`) and the three
reviewer files. No prompt text is reproduced here. No reviewer file, label or rationale
was edited.

## Result

| Pilot ID | Non-ASCII chars in master | Sampling stratum | Reviewer labels (R1/R2/R3) |
|---|---|---|---|
| pilot-059 | 38 of 38 | false__unharmful | BENIGN / BENIGN / BENIGN |
| pilot-061 | 1 of 49 | false__unharmful | BENIGN / BENIGN / BENIGN |
| pilot-092 | 2 of 361 | false__unharmful | ADVERSARIAL / ADVERSARIAL / ADVERSARIAL |
| pilot-161 | 42 of 2173 | true__unharmful | QUARANTINE / ADVERSARIAL / ADVERSARIAL |
| pilot-183 | 7 of 622 | true__unharmful | ADVERSARIAL / ADVERSARIAL / QUARANTINE |

## Findings

- **Corruption type: mojibake (double encoding).** In each of the five reviewer-file
  prompts, re-reading the text as Windows-1252 bytes and decoding those bytes as UTF-8
  reproduces the master prompt exactly. This holds for all three reviewer files, and the
  reviewer-file text is identical across them. Affected content is non-ASCII characters
  only (accented Latin letters, a curly apostrophe, emoji, CJK text, mathematical-script
  letters).
- **Scope.** These five are the only prompts in the 200-item master that contain any
  non-ASCII character. All 195 other prompts are pure ASCII and match exactly. No
  mojibake pattern occurs in any rationale or in the other 195 prompts.
- **Origin.** The original blank worksheet (`task_a_pilot_reviewer_1.csv`, Downloads,
  dated 2026-09-13) matches the master on all 200 prompts, including these five, so the
  corruption was introduced after the worksheet was generated. The mechanism (for
  example a spreadsheet opening a UTF-8 CSV without a BOM) is consistent with the
  evidence but not proven. Reviewer 1's CSV has no BOM and contains the double-encoded
  bytes literally.

## Effect on labels: uncertain

Reviewers most likely saw the corrupted text for these five items, as the corrupted
text is what is stored in their files. Labels are stored as valid four-label values and
were not altered by this audit. Whether corruption changed any label cannot be
determined from the files:

- pilot-059, -061, -092: unanimous across three reviewers; the corrupted characters may
  have been unreadable (CJK or emoji), but the agreement suggests limited impact.
  This is an inference, not a verified result.
- pilot-161 and pilot-183: reviewers disagree, and the prompts contain the most
  corrupted text (42 and 7 characters). Corruption may have contributed. Not
  determinable.

These five items are 2.5% of the pilot (5 of 200). Agreement statistics were computed
from the reviewer files as submitted and were not recomputed on corrected text.

## Not done

No reviewer file, label or master prompt was changed. No corrected reviewer files were
produced, and no sensitivity analysis excluding these items was run.
