"""Synthetic fixtures only; these scores are never research findings."""

import json
from pathlib import Path
import tempfile
import unittest

from task_b.custom import load_reviewed_pairs
from task_b.fever import load_source_prior, prepare_fever, write_prepared
from task_b.models import nli_label_ids
from task_b.schema import parse_claim_evidence
from task_b.verification import (evaluate, fever_binary_proxy, lexical_cues,
                                 lexical_overlap, majority_prior)


class FeverTests(unittest.TestCase):
    def test_resolution_fallback_provenance_and_missing_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            wiki = base / "wiki-pages"
            wiki.mkdir()
            (wiki / "wiki-001.jsonl").write_text(json.dumps({
                "id": "Mars", "lines": "0\tMars is red.\tlink\n2\tMars has two moons.\n"}) + "\n")
            claims = [
                {"id": 1, "claim": "Mars is red.", "label": "SUPPORTS",
                 "evidence": [[[0, 0, "Missing", 0]], [[0, 1, "Mars", 0]]]},
                {"id": 2, "claim": "Mars has three moons.", "label": "REFUTES",
                 "evidence": [[[0, 2, "Mars", 2]]]},
                {"id": 3, "claim": "Unrelated", "label": "NOT ENOUGH INFO", "evidence": [[]]},
                {"id": 4, "claim": "No page", "label": "SUPPORTS",
                 "evidence": [[[0, 3, "Absent", 5]]]},
            ]
            path = base / "claims.jsonl"
            path.write_text("\n".join(json.dumps(row) for row in claims) + "\n")
            records, report = prepare_fever(path, wiki)
            self.assertEqual([row.gold_label for row in records], ["SUPPORTED", "CONTRADICTED"])
            self.assertEqual(records[0].selected_group, 1)
            self.assertEqual(records[0].claim.evidence[0].text, "Mars is red.")
            self.assertEqual(records[0].raw_evidence, claims[0]["evidence"])
            self.assertEqual((report["resolved"], report["unresolved"], report["skipped_nei"]), (2, 1, 1))
            self.assertTrue(any("unresolved" in issue for issue in report["issues"]))
            write_prepared(records, report, base / "out")
            saved = json.loads((base / "out/records.jsonl").read_text().splitlines()[0])
            self.assertEqual(saved["claim"]["evidence"][0]["text"], "Mars is red.")
            self.assertEqual(saved["raw_id"], 1)
            self.assertEqual(saved["selected_group"], 1)

    def test_prior_source_labels_and_binary_metrics(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "train.jsonl"
            path.write_text("\n".join(json.dumps({"label": value}) for value in
                                      ("SUPPORTS", "SUPPORTS", "REFUTES", "NOT ENOUGH INFO")))
            self.assertEqual(majority_prior(load_source_prior(path)), "SUPPORTED")
        self.assertEqual(fever_binary_proxy("UNSUPPORTED"), "CONTRADICTED")
        result = evaluate(["SUPPORTED", "CONTRADICTED"],
                          ["CONTRADICTED", "CONTRADICTED"],
                          ("SUPPORTED", "CONTRADICTED"), [0.1, 0.2])
        self.assertEqual(result["confusion_matrix"], [[0, 1], [0, 1]])
        self.assertEqual(result["accuracy"], 0.5)
        self.assertEqual(result["incorrect_supported"], 0)

    def test_lexical_limits_and_cues(self):
        record = parse_claim_evidence({"claim_id": "x", "claim": "Mars has 3 moons",
                                       "evidence": [{"evidence_id": "e", "text": "Mars has 2 moons"}]})
        self.assertNotEqual(lexical_overlap(record), "CONTRADICTED")
        self.assertEqual(lexical_cues(record), "CONTRADICTED")
        self.assertEqual(evaluate(["CONTRADICTED"], ["SUPPORTED"],
                                  ("SUPPORTED", "CONTRADICTED", "UNSUPPORTED"))
                         ["incorrect_supported"], 1)

    def test_nli_ids_use_config_names(self):
        class Config:
            id2label = {0: "neutral", 1: "entailment", 2: "contradiction"}
        self.assertEqual(nli_label_ids(Config()),
                         {"entailment": 1, "contradiction": 2, "neutral": 0})

    def test_unreviewed_custom_set_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "reviewed.jsonl"
            path.write_text(json.dumps({"answer_id": "a", "document_id": "d",
                                        "source_passage": "Some text", "original_sentence": "A claim."}) + "\n")
            with self.assertRaisesRegex(ValueError, "sentence"):
                load_reviewed_pairs(path)

    def test_reviewed_pair_uses_same_answer_and_passage(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "reviewed.jsonl"
            evidence = [{"evidence_id": "d:0", "text": "Mars has two moons.",
                         "source_document_id": "d"}]
            def review(claim_id):
                return {"claim_id": claim_id, "reviewer_id": "human-1",
                        "annotator_kind": "human", "label": "SUPPORTED",
                        "rationale": "The passage says so.", "evidence_ids": ["d:0"]}
            row = {"answer_id": "a", "document_id": "d",
                   "source_passage": "Mars has two moons.",
                   "original_sentence": "Mars has two moons.",
                   "sentence": {"claim_id": "s", "claim": "Mars has two moons.",
                                "answer_id": "a", "evidence": evidence},
                   "sentence_review": review("s"),
                   "atomic_claims": [{"claim": {"claim_id": "c", "claim": "Mars has two moons.",
                                                 "answer_id": "a", "evidence": evidence},
                                      "review": review("c")}]}
            path.write_text(json.dumps(row) + "\n")
            sentences, atoms = load_reviewed_pairs(path)
            self.assertEqual((len(sentences), len(atoms)), (1, 1))
            row["atomic_claims"][0]["claim"]["evidence"][0]["text"] = "Different text."
            path.write_text(json.dumps(row) + "\n")
            with self.assertRaisesRegex(ValueError, "verbatim"):
                load_reviewed_pairs(path)


if __name__ == "__main__":
    unittest.main()
