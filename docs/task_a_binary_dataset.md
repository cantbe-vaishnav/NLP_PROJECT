# Task A binary jailbreak dataset (WildGuardMix + JailbreakHub)

Status: dataset built and audited on 2026-10-21. No model has been trained on it.
Gate 1 status is unchanged (see `phase1_gate_report.md`); this document does not pass it.
Counts are in the generated audit, `results/data_audit/binary_jailbreak_audit.md`.

This task is separate from the four-label annotation pilot and does not use its labels.

## Task and labels

Binary jailbreak (source-adversarial) detection on the user prompt:

| Label | Name | Source rule |
|---|---|---|
| 1 | ADVERSARIAL | WildGuardMix `adversarial=True`; JailbreakHub `jailbreak_2023_12_25` |
| 0 | BENIGN | WildGuardMix `adversarial=False`; JailbreakHub `regular_2023_12_25` |

BENIGN means non-jailbreak under this task, not harmless: direct harmful requests are 0.
Labels are each source's own flag and are never edited. Each row keeps `source_dataset`,
`source_config`, `source_split`, `source_row`, `source_label` and source metadata. A
JailbreakHub row whose `jailbreak` column disagrees with its configuration stops the
build (none did). The four-label pilot audit found that the WildGuardMix flag only
partly matches the project's own ADVERSARIAL definition; results describe the source
flags.

## Sources

| Source | Revision | License | Raw location (Git-ignored) |
|---|---|---|---|
| allenai/wildguardmix (train, test) | `d29c47f4…` | ODC-BY; gated, terms accepted by the owner | `data/raw/wildguard_{train,test}.parquet` |
| TrustAIRLab/in-the-wild-jailbreak-prompts (`jailbreak_2023_12_25`, `regular_2023_12_25`) | `a10aab8e…` | MIT | `data/raw/jailbreakhub/<config>/train-00000-of-00001.parquet` |

Every raw file is checked against the SHA-256 in `configs/task_a_binary_dataset.json`
(the JailbreakHub values are the Hub's LFS hashes, recorded in
`results/data_audit/jailbreakhub_download.json`). The `datasets` library is not
installed; the download script fetches the same files `datasets.load_dataset` reads.

## Processing rules (in order)

1. **Invalid prompts** (not a string, or no letter/digit) are excluded.
2. **Official test protection.** The WildGuardMix test split is copied unchanged
   (verified row by row). Training-pool rows matching a test prompt exactly or after
   normalization are excluded.
3. **Duplicates.** Comparison key = NFC + casefold + whitespace collapse (matching only;
   model input is the original text). Within an exact or normalized group, the first
   row represents it (order: WildGuardMix train, JailbreakHub jailbreak, JailbreakHub
   regular) and the rest are excluded with `related_id`. A group whose binary labels
   disagree is excluded entirely; no label is chosen. Differing WildGuardMix
   `prompt_harm_label` sets `harm_label_conflict` and does not affect the binary label.
4. **Near-duplicate families.** Edges where word 1–2-gram TF-IDF cosine ≥ 0.8 or
   5-word-shingle Jaccard ≥ 0.85, computed over the pool and the official test
   together. Candidates come from rare-term vectors, plus an exhaustive pass for every
   official-test row and every text without rare terms. Families are connected
   components (threshold from the split-feasibility analysis, policy D).
5. **Near-duplicates of the official test.** Any pool row in a family containing an
   official-test row is excluded.
6. **Near-identical prompts with different labels** stay in one family and one split,
   and are flagged `mixed_label_near_duplicate_family`. They are not relabelled.
7. **Splits (seed 42).** Whole families are assigned in a seeded-hash order. WildGuardMix
   families: 10% validation. Families with any JailbreakHub member: 10% validation, 10%
   `test_jailbreakhub`, a held-out JailbreakHub evaluation that is **not** an official
   test set. Everything else is train; `test_official` is the unchanged WildGuardMix test.
8. **Suspicious-label flags** (kept, never relabelled): very short prompts, JailbreakHub
   BENIGN rows containing jailbreak cue words, short JailbreakHub ADVERSARIAL rows, and
   mixed-label families. Example IDs are listed in the audit JSON.

## Leakage checks run by the build

The build stops if any of these fail: official test unchanged; no family spans two
splits; no normalized prompt shared by the official test and train/validation; no
official-test row with TF-IDF cosine ≥ 0.8 to any train row (checked exhaustively). The
residual-similarity table in the audit reports the same check for validation and
`test_jailbreakhub`.

Limitations: the checks are lexical. Paraphrases, translations and shared parent
prompts (for example a vanilla prompt and its synthetic adversarial rewrite) are not
detectable, so leakage beyond these levels is not ruled out. JailbreakHub is dominated
by long jailbreak templates and short "regular" prompts, so length and style can act as
shortcuts; report results per source.

## Outputs

Git-ignored, under `data/processed/binary_jailbreak/`: `combined.parquet` (all splits,
single `label` column), `jailbreakhub_clean.parquet` (JailbreakHub after its own
invalid/duplicate/conflict handling), `exclusions.csv` (ID, reason, related ID),
`families.csv`, `near_duplicate_edges.csv`, `split_manifest.json` (IDs only).
Trackable: `results/data_audit/binary_jailbreak_audit.{json,md}`,
`results/data_audit/jailbreakhub_download.json`.

## Reproduce

Python 3.11 with pyarrow, numpy, scipy, scikit-learn and huggingface_hub (versions are
recorded in the audit). The venv currently lacks scikit-learn; the build was run with
the system interpreter.

```bash
python scripts/download_jailbreakhub.py          # only if data/raw/jailbreakhub is absent
PYTHONPATH=src python scripts/build_binary_dataset.py --config configs/task_a_binary_dataset.json
PYTHONPATH=src python -m pytest -q tests/test_binary_dataset.py tests/test_binary_metrics.py
```

Both scripts refuse to overwrite existing outputs. Two runs produced byte-identical
`combined.parquet`, `split_manifest.json`, `exclusions.csv` and `families.csv`.

## Version 2: reviewed JailbreakHub label corrections (2026-10-21)

`configs/task_a_binary_dataset_v2.json` rebuilds the dataset with the same pipeline plus a
correction manifest (`data/processed/binary_jailbreak/review/label_corrections_v1.csv`,
Git-ignored, SHA-256 checked by the build). The manifest comes from a
**full-text review** of 184 high-cue JailbreakHub `regular` prompts and a
40-row seed-42 sample of `jailbreak` prompts. The project owner personally verified the 174
applied corrections (stated 2026-10-22). The stored `reviewer_type` values, the v2 config
`version` string and the generated audits (`binary_jailbreak_v2_audit`, `label_review_report`)
predate that verification and still describe the review as not human-verified; they were left
unchanged so the build and its outputs stay reproducible.

- Corrections are applied after deduplication, by stable ID only. Each ID must be a
  retained JailbreakHub record whose text equals the raw source and whose binary label
  equals the manifest's source label, or the build stops.
- `source_label` and `source_binary_label` keep the original source labels.
  `corrected_label` is set only for reviewed rows, and `label` is the training target.
  Review status, reason, reviewer type and artifact path are stored per row.
- Results: 169 labels changed 0→1, 5 changed 1→0, 37 confirmed unchanged, and 13
  ambiguous rows excluded. The ambiguous rows are held in
  `data/processed/binary_jailbreak_v2/ambiguous_review_holdout.parquet`.
- Families and splits are recomputed (seed 42), so v1 and v2 split memberships differ.
  The official WildGuardMix test set is identical to v1 and to the raw file. Audit:
  `results/data_audit/binary_jailbreak_v2_audit.md`. v1 outputs are unchanged.
- Rows not in the review keep their source labels. The earlier audit estimates
  substantial remaining JailbreakHub label noise in unreviewed rows
  (`results/data_audit/label_review_report.md`).

```bash
PYTHONPATH=src python scripts/build_binary_dataset.py --config configs/task_a_binary_dataset_v2.json
```
