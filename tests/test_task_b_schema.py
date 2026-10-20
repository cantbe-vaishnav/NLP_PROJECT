"""Synthetic contract fixtures only; no research observations or model outputs."""

from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import unittest

from task_b import FLAGS, LABELS, parse_annotation, parse_claim_evidence
from task_b.schema import Annotation, ClaimEvidence, EvidenceSentence


class TaskBContractTests(unittest.TestCase):
    def setUp(self):
        self.claim = {
            "claim_id": "claim-1",
            "claim": "  The launch was in 2020.  ",
            "evidence": [
                {"evidence_id": "doc-1:3", "text": "The launch was in 2020.",
                 "source_document_id": "doc-1"},
                {"evidence_id": "doc-2:7", "text": "A second source agrees."},
            ],
            "answer_id": "answer-1",
            "claim_span": [12, 35],
        }
        self.annotation = {
            "claim_id": "claim-1",
            "reviewer_id": "reviewer-1",
            "annotator_kind": "human",
            "label": "SUPPORTED",
            "rationale": "Evidence doc-1:3 states the date.",
            "flags": [],
            "evidence_ids": ["doc-1:3"],
        }

    def test_claim_preserves_text_and_provenance(self):
        record = parse_claim_evidence(self.claim)
        self.assertEqual(record.claim, self.claim["claim"])
        self.assertEqual(record.answer_id, "answer-1")
        self.assertEqual(record.claim_span, (12, 35))
        self.assertEqual(record.evidence[0].source_document_id, "doc-1")
        with self.assertRaises(FrozenInstanceError):
            record.claim = "changed"

    def test_missing_or_empty_evidence_is_invalid(self):
        for evidence in (None, [], "a sentence", [{}], [{"evidence_id": "x", "text": " "}]):
            with self.subTest(evidence=evidence), self.assertRaises(ValueError):
                raw = dict(self.claim)
                raw["evidence"] = evidence
                parse_claim_evidence(raw)
        raw = dict(self.claim)
        del raw["evidence"]
        with self.assertRaisesRegex(ValueError, "missing fields: evidence"):
            parse_claim_evidence(raw)

    def test_duplicate_ids_and_invalid_spans_are_rejected(self):
        raw = dict(self.claim)
        raw["evidence"] = [self.claim["evidence"][0], self.claim["evidence"][0]]
        with self.assertRaisesRegex(ValueError, "unique"):
            parse_claim_evidence(raw)
        for span in ([0, 0], [-1, 3], [True, 2], [1], "1,2"):
            with self.subTest(span=span), self.assertRaises(ValueError):
                raw = dict(self.claim, claim_span=span)
                parse_claim_evidence(raw)

    def test_unknown_fields_and_malformed_input_are_rejected(self):
        for raw in (None, [], {1: "not a string key"}, dict(self.claim, source_label="SUPPORTS")):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                parse_claim_evidence(raw)
        raw = dict(self.claim)
        raw["evidence"] = [{"evidence_id": "x", "text": "ok", "unexpected": 1}]
        with self.assertRaisesRegex(ValueError, "unknown fields"):
            parse_claim_evidence(raw)
        for key in ("answer_id", "claim_span"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                parse_claim_evidence(dict(self.claim, **{key: None}))
        raw = dict(self.claim)
        raw["evidence"] = [{"evidence_id": "x", "text": "ok", "source_document_id": None}]
        with self.assertRaises(ValueError):
            parse_claim_evidence(raw)

    def test_exactly_three_labels_and_flags_are_not_labels(self):
        self.assertEqual(LABELS, ("SUPPORTED", "CONTRADICTED", "UNSUPPORTED"))
        self.assertEqual(FLAGS, ("BAD_CLAIM", "NON_CLAIM"))
        claim = parse_claim_evidence(self.claim)
        for label in LABELS:
            with self.subTest(label=label):
                annotation = parse_annotation(dict(self.annotation, label=label), claim=claim)
                self.assertEqual(annotation.label, label)
        for label in ("BAD_CLAIM", "NON_CLAIM", "REFUTES", "supported", "", None):
            with self.subTest(label=label), self.assertRaisesRegex(ValueError, "label"):
                parse_annotation(dict(self.annotation, label=label))

    def test_flags_and_annotator_kind_are_structural_fields(self):
        valid = parse_annotation(dict(self.annotation, flags=["BAD_CLAIM", "NON_CLAIM"],
                                      annotator_kind="AI"))
        self.assertEqual(valid.flags, ("BAD_CLAIM", "NON_CLAIM"))
        self.assertEqual(valid.annotator_kind, "AI")
        for flags in (["UNKNOWN"], ["BAD_CLAIM", "BAD_CLAIM"], "BAD_CLAIM"):
            with self.subTest(flags=flags), self.assertRaises(ValueError):
                parse_annotation(dict(self.annotation, flags=flags))
        with self.assertRaisesRegex(ValueError, "annotator_kind"):
            parse_annotation(dict(self.annotation, annotator_kind="bot"))

    def test_completed_annotation_requires_rationale_and_valid_references(self):
        claim = parse_claim_evidence(self.claim)
        for changed in (
            {"rationale": " "}, {"reviewer_id": ""},
            {"claim_id": "different"}, {"evidence_ids": ["unknown:0"]},
            {"evidence_ids": ["doc-1:3", "doc-1:3"]},
        ):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                parse_annotation(dict(self.annotation, **changed), claim=claim)
        raw = dict(self.annotation)
        del raw["label"]
        with self.assertRaisesRegex(ValueError, "missing fields: label"):
            parse_annotation(raw)

    def test_direct_typed_records_also_validate(self):
        with self.assertRaises(ValueError):
            EvidenceSentence("", "text")
        with self.assertRaises(ValueError):
            ClaimEvidence("claim", "text", ())
        with self.assertRaises(ValueError):
            Annotation("claim", "reviewer", "human", "BAD_CLAIM", "rationale")

    def test_declarative_schema_uses_same_labels_and_flags(self):
        schema_path = Path(__file__).resolve().parents[1] / "src/task_b/contract.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        annotation = schema["$defs"]["annotation"]
        self.assertEqual(tuple(annotation["properties"]["label"]["enum"]), LABELS)
        self.assertEqual(tuple(annotation["properties"]["flags"]["items"]["enum"]), FLAGS)


if __name__ == "__main__":
    unittest.main()
