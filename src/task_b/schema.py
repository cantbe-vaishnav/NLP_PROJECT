"""Small, strict Task B contracts for supplied-evidence verification.

These validators check structure, not whether evidence actually entails a claim.
They do not assign labels or convert FEVER's source labels.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any


LABELS = ("SUPPORTED", "CONTRADICTED", "UNSUPPORTED")
FLAGS = ("BAD_CLAIM", "NON_CLAIM")
ANNOTATOR_KINDS = ("human", "AI")


def _object(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or any(not isinstance(k, str) for k in value):
        raise ValueError(f"{name} must be an object with string keys")
    return value


def _fields(value: Mapping[str, Any], required: set[str], optional: set[str], name: str) -> None:
    missing = required - value.keys()
    extra = value.keys() - required - optional
    if missing:
        raise ValueError(f"{name} missing fields: {', '.join(sorted(missing))}")
    if extra:
        raise ValueError(f"{name} unknown fields: {', '.join(sorted(extra))}")


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _optional_text(value: object, name: str) -> str | None:
    return None if value is None else _text(value, name)


def _list(value: object, name: str) -> Sequence[Any]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{name} must be a list")
    return value


def _unique_texts(value: object, name: str, *, allowed: tuple[str, ...] | None = None) -> tuple[str, ...]:
    items = tuple(_text(item, f"{name} item") for item in _list(value, name))
    if len(items) != len(set(items)):
        raise ValueError(f"{name} contains duplicates")
    if allowed is not None and any(item not in allowed for item in items):
        raise ValueError(f"{name} contains an invalid value; allowed: {', '.join(allowed)}")
    return items


@dataclass(frozen=True, slots=True)
class EvidenceSentence:
    evidence_id: str
    text: str
    source_document_id: str | None = None

    def __post_init__(self) -> None:
        _text(self.evidence_id, "evidence_id")
        _text(self.text, "evidence text")
        _optional_text(self.source_document_id, "source_document_id")


@dataclass(frozen=True, slots=True)
class ClaimEvidence:
    claim_id: str
    claim: str
    evidence: tuple[EvidenceSentence, ...]
    answer_id: str | None = None
    claim_span: tuple[int, int] | None = None

    def __post_init__(self) -> None:
        _text(self.claim_id, "claim_id")
        _text(self.claim, "claim")
        if not isinstance(self.evidence, tuple) or not self.evidence:
            raise ValueError("evidence must contain at least one sentence")
        if any(not isinstance(item, EvidenceSentence) for item in self.evidence):
            raise ValueError("evidence entries must be EvidenceSentence objects")
        ids = [item.evidence_id for item in self.evidence]
        if len(ids) != len(set(ids)):
            raise ValueError("evidence_id values must be unique within a claim")
        _optional_text(self.answer_id, "answer_id")
        if self.claim_span is not None:
            span = self.claim_span
            if (not isinstance(span, tuple) or len(span) != 2
                    or any(type(point) is not int for point in span)
                    or span[0] < 0 or span[0] >= span[1]):
                raise ValueError("claim_span must be [start, end] with 0 <= start < end")


@dataclass(frozen=True, slots=True)
class Annotation:
    claim_id: str
    reviewer_id: str
    annotator_kind: str
    label: str
    rationale: str
    flags: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _text(self.claim_id, "claim_id")
        _text(self.reviewer_id, "reviewer_id")
        if self.annotator_kind not in ANNOTATOR_KINDS:
            raise ValueError(f"annotator_kind must be one of: {', '.join(ANNOTATOR_KINDS)}")
        if self.label not in LABELS:
            raise ValueError(f"label must be one of: {', '.join(LABELS)}")
        _text(self.rationale, "rationale")
        if not isinstance(self.flags, tuple):
            raise ValueError("flags must be a tuple")
        _unique_texts(self.flags, "flags", allowed=FLAGS)
        if not isinstance(self.evidence_ids, tuple):
            raise ValueError("evidence_ids must be a tuple")
        _unique_texts(self.evidence_ids, "evidence_ids")


def parse_claim_evidence(value: object) -> ClaimEvidence:
    """Validate a JSON-like record and return an immutable claim/evidence object."""
    row = _object(value, "claim record")
    _fields(row, {"claim_id", "claim", "evidence"}, {"answer_id", "claim_span"}, "claim record")
    evidence = []
    for index, item in enumerate(_list(row["evidence"], "evidence")):
        sentence = _object(item, f"evidence[{index}]")
        _fields(sentence, {"evidence_id", "text"}, {"source_document_id"}, f"evidence[{index}]")
        if "source_document_id" in sentence and sentence["source_document_id"] is None:
            raise ValueError("source_document_id must be a non-empty string when provided")
        evidence.append(EvidenceSentence(
            sentence["evidence_id"], sentence["text"],
            sentence.get("source_document_id"),
        ))
    raw_span = row.get("claim_span")
    if "answer_id" in row and row["answer_id"] is None:
        raise ValueError("answer_id must be a non-empty string when provided")
    if "claim_span" in row and raw_span is None:
        raise ValueError("claim_span must be [start, end] when provided")
    span = None if raw_span is None else tuple(_list(raw_span, "claim_span"))
    return ClaimEvidence(row["claim_id"], row["claim"], tuple(evidence), row.get("answer_id"), span)


def parse_annotation(value: object, *, claim: ClaimEvidence | None = None) -> Annotation:
    """Validate a completed annotation; optionally check its claim/evidence IDs."""
    row = _object(value, "annotation")
    _fields(row, {"claim_id", "reviewer_id", "annotator_kind", "label", "rationale"},
            {"flags", "evidence_ids"}, "annotation")
    annotation = Annotation(
        row["claim_id"], row["reviewer_id"], row["annotator_kind"],
        row["label"], row["rationale"],
        _unique_texts(row.get("flags", []), "flags", allowed=FLAGS),
        _unique_texts(row.get("evidence_ids", []), "evidence_ids"),
    )
    if claim is not None:
        if not isinstance(claim, ClaimEvidence):
            raise ValueError("claim must be a ClaimEvidence object")
        if annotation.claim_id != claim.claim_id:
            raise ValueError("annotation claim_id does not match the claim")
        known = {item.evidence_id for item in claim.evidence}
        if any(item not in known for item in annotation.evidence_ids):
            raise ValueError("annotation cites an unknown evidence_id")
    return annotation
