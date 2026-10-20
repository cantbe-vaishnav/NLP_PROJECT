# Task B B0 contract

Task B classifies a **claim against supplied evidence**, not against world truth. Its
only labels are `SUPPORTED`, `CONTRADICTED`, and `UNSUPPORTED`. `BAD_CLAIM` and
`NON_CLAIM` are separate annotation flags. No Task A labels or pilot data are used.

`parse_claim_evidence` accepts a JSON-like object with `claim_id` (string), `claim`
(original claim text), and a non-empty `evidence` list. Each evidence item has a
unique `evidence_id` and non-empty original `text`; `source_document_id` is optional.
`answer_id` and `claim_span` (`[start, end]`, end-exclusive character offsets into
the original answer) are optional claim provenance. The validator cannot check span
bounds without the original answer. It preserves text exactly, including whitespace.
It rejects missing/empty evidence rather than assigning an `UNSUPPORTED` label.

`parse_annotation` accepts a **completed** decision with `claim_id`, `reviewer_id`,
`annotator_kind` (`human` or `AI`), one Task B `label`, and a non-empty `rationale`.
Optional `flags` and `evidence_ids` are lists of unique strings; flags must be from
the two allowed flags. Passing the corresponding claim checks the claim ID and any
cited evidence IDs. Unknown fields and implicit string/label coercion are rejected,
so source metadata must be retained separately rather than silently dropped.
These are structural checks only; they do not decide whether evidence entails a
claim. Blank worksheets and adjudication are outside B0.
`contract.schema.json` documents the two JSON record shapes. The Python validator
also checks conditions JSON Schema cannot express here: unique evidence IDs per
claim, ordered span bounds, and cited evidence IDs belonging to the claim.

The owner has **revised the dependency** from the earlier Task B handoff: Task A
Gate 1 is no longer required to start independent B0. This does not change Gate 1
for Task A. B1 and later work retain their separate data, license, evidence-policy,
model-access, and evaluation approvals. RQ4 (atomic claim versus sentence-level
verification) remains a core Tier 1 question. FEVER and custom evaluations remain
separate; the FEVER NEI evidence and threshold-calibration policies are unresolved.
