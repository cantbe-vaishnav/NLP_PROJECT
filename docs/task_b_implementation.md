# Task B faithfulness verification: B1–B3

## Inputs and execution

The notebooks use the existing B0 `ClaimEvidence` and annotation validators. They
do not fetch data or weights. The FEVER baselines notebook uses only the Python
standard library and finds `src/task_b` from the open project folder, so it does
not need `pandas` or a package install. For the later notebooks, install
`requirements-task-b.txt` in the VS Code kernel yourself; it declares the local
package plus `pandas`, `sentence-transformers`, `transformers`, and `torch`.
Runtime library versions and exact local model snapshot hashes are saved with
model runs.

Place the official FEVER files at these paths, or edit the first code cell:

- `data/raw/fever/train.jsonl` — prior labels only; never the evaluation file.
- `data/raw/fever/shared_task_dev.jsonl` — SUPPORTS/REFUTES evaluation claims.
- `data/raw/fever/wiki-pages/*.jsonl` — official Wikipedia page JSONL files, each
  with `id` and `lines` containing `sentence_id<TAB>sentence_text<TAB>...`.

The resolver matches page IDs exactly and parses the sentence text from `lines`.
It chooses the first **fully resolved** valid gold evidence group, retaining the
original evidence groups and selected original group index. Partially resolved
groups and rows with no resolved group are excluded and logged in
`outputs/task_b/fever_baselines/prepared/resolution_report.json`. NEI rows are
counted separately and excluded. No NEI evidence policy is implied here. Original
raw files are never changed. The prepared JSONL retains source file, line, FEVER
ID, source label, all original references, selected group, and resolved text.

Run in this order in VS Code (the notebooks find the project root themselves):

1. `notebooks/task_b_fever_baselines.ipynb`
2. `notebooks/task_b_embedding_nli.ipynb`. MiniLM is read from
   `models/task_b/all-MiniLM-L6-v2/` if present, otherwise from the existing Hugging Face
   cache (`local_files_only`, never downloaded). The NLI step runs only if a complete
   `FacebookAI/roberta-large-mnli` snapshot exists at `models/task_b/roberta-large-mnli/`;
   otherwise it is skipped and says so.
3. After an independently reviewed paired custom set exists at
   `data/annotations/task_b_reviewed_pairs.jsonl`, run
   `notebooks/task_b_atomic_vs_sentence.ipynb`.

FEVER here is a **two-class gold-evidence diagnostic**, not end-to-end evidence
retrieval. Raw Task B predictions are saved. For this particular diagnostic,
`UNSUPPORTED` is projected to the negative `CONTRADICTED` class so all methods
can be compared on the SUPPORTS/REFUTES split; its count is reported. This
projection does **not** mean the model detected a contradiction. The majority
prior uses only the separate training file. Lexical overlap emits only SUPPORTED
or UNSUPPORTED, so it cannot find contradictions. Fixed negation and number cues
are shallow and can misread scope, paraphrases, dates and multi-sentence evidence.
Embedding cosine similarity also cannot reliably detect contradictions. Its
0.5 cutoff and the baselines' 0.5 overlap cutoffs are fixed starting settings,
not thresholds tuned on evaluation labels.

NLI passes each evidence sentence as **premise** and the claim as **hypothesis**.
It reads class IDs from `model.config.id2label`. Each sentence's highest class
wins locally; among sentences whose local winner is entailment or contradiction,
the largest winning probability decides the claim label. If every sentence's
winner is neutral, the claim is UNSUPPORTED. This is a **project-specific**
aggregation rule, not an established published method. Truncation can discard
important text. Results under `outputs/task_b/` contain separate configs,
predictions, scores, latency and confusion matrices. FEVER and custom results
are never pooled.

## Validation split, thresholds and run folders

- **Test:** resolved SUPPORTS/REFUTES claims of `shared_task_dev.jsonl`. Scored once per run.
- **Validation:** `write_validation_sample` draws a seeded (42), balanced sample of 2,000
  SUPPORTS and 2,000 REFUTES claims from `train.jsonl`, skipping any claim whose text (case and
  spacing ignored) also occurs in the dev file, then resolves its evidence the same way. It is
  balanced because the test claims are balanced. Its manifest is saved with the prepared data.
- **Thresholds:** the lexical-overlap, lexical-cue and embedding-cosine cutoffs are chosen by
  validation macro-F1 on the same two-class diagnostic (`choose_threshold`, ties to the lower
  cutoff). Each method is also reported at the original fixed 0.5 cutoff for comparison.
  The majority prior uses only training labels.
- **Runs:** every notebook run writes to a new `run_<UTC timestamp>/` folder and `save_run`
  refuses to overwrite an existing folder. Prepared records are rebuilt deterministically
  under `outputs/task_b/fever_prepared/` (`test/` and `validation_seed42_n2000/`).

## Coverage, smoke mode and the earlier 20-claim pilots

- **Pilot diagnostics only:** the embedding and NLI runs reported in
  `task_b_handoff_2026-10-22.md` covered 20 claims each. They are pilot diagnostics, not model
  evaluations, and must not be compared with the 13,202-claim baselines. Their artifacts were
  never committed, and no committed version of any notebook or module contains a 20-claim limit
  (the notebooks were added once, in `cb6c6a1`), so the cause of the limit cannot be established
  from the repository.
- **Full evaluation path:** `task_b_embedding_nli.ipynb` scores every resolved record in each
  split. It checks that its test claims are exactly those of the latest baseline run, prints a
  coverage table (eligible, processed, skipped, failed per split and model), stops if any claim
  fails to score, and saves the coverage in each run's `config.json`.
- **Smoke mode:** set `SMOKE_TEST = True` in the first cell to score only the first
  `SMOKE_LIMIT` (20) claims per split. Smoke runs are written to `smoke_run_<timestamp>/`
  folders and labelled "smoke test (not an evaluation)"; never report them.

## Known limitations of the FEVER diagnostic

- **Not three-class.** NOT ENOUGH INFO claims have no gold evidence and are excluded from the
  two-class diagnostic, so it has no UNSUPPORTED gold label. The separate three-class evaluation
  (`notebooks/task_b_fever_three_class.ipynb`, `retrieve_nei_evidence` in `fever.py`) gives NEI
  claims retrieved, unreviewed evidence; its policy, shortcut check and results are in
  [task_b_results.md](task_b_results.md).
- **Gold evidence is given,** so retrieval is not tested.
- **Evidence text is verbatim FEVER text,** which keeps Penn Treebank tokens such as `-LRB-`,
  `-RRB-` and doubled backquotes (about 30% of sentences in a 3,000-page sample). Claims are
  plain text. Whether to map these tokens back to brackets and quotes is an open decision.
- **Train and dev claims may cite the same Wikipedia pages;** only exact claim-text overlap is
  excluded. Validation is used solely for choosing cutoffs, never for fitting models.

## Independently reviewed custom set

`docs/task_b_annotation_template.csv` is an empty review worksheet.
It contains no examples or gold labels. For the experiment notebook, convert
completed reviews to one JSONL object per original sentence with this shape:

```json
{
  "answer_id": "<id>",
  "document_id": "<id>",
  "source_passage": "<verbatim passage>",
  "original_sentence": "<verbatim generated sentence>",
  "sentence": {
    "claim_id": "<sentence id>", "claim": "<same original sentence>",
    "answer_id": "<same answer id>",
    "evidence": [{"evidence_id": "<id>", "text": "<verbatim evidence from passage>",
                  "source_document_id": "<same document id>"}]
  },
  "sentence_review": {
    "claim_id": "<same sentence id>", "reviewer_id": "<human id>",
    "annotator_kind": "human", "label": "<B0 label>",
    "rationale": "<review rationale>", "evidence_ids": ["<cited evidence id>"]
  },
  "atomic_claims": [
    {"claim": {"claim_id": "<atom id>", "claim": "<atomic claim>",
               "answer_id": "<same answer id>",
               "evidence": [{"evidence_id": "<id>",
                             "text": "<verbatim evidence from same passage>",
                             "source_document_id": "<same document id>"}]},
     "review": {"claim_id": "<same atom id>", "reviewer_id": "<human id>",
                "annotator_kind": "human", "label": "<B0 label>",
                "rationale": "<review rationale>", "evidence_ids": ["<cited id>"]}}
  ]
}
```

The angle-bracket values are placeholders, not observations. The loader rejects
missing reviews, AI-only reviews, mismatched answer/document IDs, evidence text
outside the passage and invalid B0 references. Sentence and atomic predictions
use the same fixed `lexical_cues` verifier and source passage, but their
metrics are computed separately because the unit of analysis differs. No custom
result is valid until the annotations have been independently reviewed.

## Scope limits

The named research brief was not present in the supplied attachment or checkout,
so this implementation follows the pasted Task B requirements and the B0
contract. B0's existing review report identifies optional-null serialization and
annotation-reference limitations; this pipeline omits absent optional fields
when serializing and always passes the claim to `parse_annotation` for reviewed
custom data. It does not rewrite the B0 contract or decide its broader approval.
