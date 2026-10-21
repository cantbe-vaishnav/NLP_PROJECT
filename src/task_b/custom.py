"""Load independently reviewed paired sentence/atomic examples."""

from __future__ import annotations

import json
from pathlib import Path

from .schema import parse_annotation, parse_claim_evidence


def _matching_source(claim, document_id: str, source_passage: str) -> None:
    if any(item.source_document_id != document_id or item.text not in source_passage
           for item in claim.evidence):
        raise ValueError("evidence must be verbatim text from the matching source passage")


def load_reviewed_pairs(path: str | Path):
    """Return two aligned evaluation lists; reject unfinished or AI-only reviews."""
    sentences, atoms = [], []
    with Path(path).open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            try:
                row = json.loads(line)
                for field in ("answer_id", "document_id", "source_passage", "original_sentence"):
                    if not isinstance(row[field], str) or not row[field].strip():
                        raise ValueError(f"missing {field}")
                sentence = parse_claim_evidence(row["sentence"])
                if sentence.claim != row["original_sentence"] or sentence.answer_id != row["answer_id"]:
                    raise ValueError("sentence does not match original sentence/answer")
                _matching_source(sentence, row["document_id"], row["source_passage"])
                review = parse_annotation(row["sentence_review"], claim=sentence)
                if review.annotator_kind != "human":
                    raise ValueError("sentence review must be independent human review")
                sentences.append((sentence, review.label, row["answer_id"], row["document_id"]))
                if not isinstance(row["atomic_claims"], list) or not row["atomic_claims"]:
                    raise ValueError("atomic_claims must be non-empty")
                for item in row["atomic_claims"]:
                    atom = parse_claim_evidence(item["claim"])
                    _matching_source(atom, row["document_id"], row["source_passage"])
                    atom_review = parse_annotation(item["review"], claim=atom)
                    if atom.answer_id != row["answer_id"] or atom_review.annotator_kind != "human":
                        raise ValueError("atom answer/review mismatch")
                    atoms.append((atom, atom_review.label, row["answer_id"], row["document_id"]))
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise ValueError(f"invalid reviewed pair at line {line_number}: {exc}") from exc
    if not sentences:
        raise ValueError("reviewed set is empty")
    return sentences, atoms
