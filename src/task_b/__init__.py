"""Task B claim/evidence contracts, independent of Task A."""

from .schema import (
    ANNOTATOR_KINDS,
    FLAGS,
    LABELS,
    Annotation,
    ClaimEvidence,
    EvidenceSentence,
    parse_annotation,
    parse_claim_evidence,
)

__all__ = (
    "ANNOTATOR_KINDS",
    "FLAGS",
    "LABELS",
    "Annotation",
    "ClaimEvidence",
    "EvidenceSentence",
    "parse_annotation",
    "parse_claim_evidence",
)
