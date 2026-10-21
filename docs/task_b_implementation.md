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

Run in this order from the repository root in VS Code:

1. `notebooks/task_b_fever_baselines.ipynb`
2. Put complete local snapshots of `sentence-transformers/all-MiniLM-L6-v2`
   and `FacebookAI/roberta-large-mnli` at
   `models/task_b/all-MiniLM-L6-v2/` and
   `models/task_b/roberta-large-mnli/`, then run
   `notebooks/task_b_embedding_nli.ipynb`.
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
