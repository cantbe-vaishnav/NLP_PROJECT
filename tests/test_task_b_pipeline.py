"""Synthetic fixtures only; these scores are never research findings."""

import json
from pathlib import Path
import tempfile
import unittest

from task_b.custom import load_reviewed_pairs
from task_b.fever import (claim_key, claim_phrases, load_source_prior, prepare_fever, retrieve_nei_evidence,
                          title_key, write_prepared, write_validation_sample)
from task_b.models import embedding_similarities, nli_label_ids
from task_b.schema import parse_claim_evidence
from task_b.verification import (choose_threshold, evaluate, fever_binary_proxy, lexical_cues,
                                 lexical_overlap, majority_prior, overlap_score, save_run)


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

    def test_validation_sample_is_reproducible_and_disjoint(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            rows = [{"id": i, "claim": f"Claim {i}", "label": label, "evidence": []}
                    for i, label in enumerate(["SUPPORTS"] * 6 + ["REFUTES"] * 6 + ["NOT ENOUGH INFO"] * 3)]
            (base / "train.jsonl").write_text("\n".join(json.dumps(row) for row in rows) + "\n")
            excluded = {claim_key("  CLAIM 0 ")}
            first = write_validation_sample(base / "train.jsonl", base / "a.jsonl", 2, 42, excluded)
            write_validation_sample(base / "train.jsonl", base / "b.jsonl", 2, 42, excluded)
            sample = [json.loads(line) for line in (base / "a.jsonl").read_text().splitlines()]
            self.assertEqual((base / "a.jsonl").read_text(), (base / "b.jsonl").read_text())
            self.assertEqual(sorted(row["label"] for row in sample), ["REFUTES"] * 2 + ["SUPPORTS"] * 2)
            self.assertNotIn("Claim 0", [row["claim"] for row in sample])
            self.assertEqual(first["skipped_overlapping_with_evaluation"], 1)
            with self.assertRaises(ValueError):
                write_validation_sample(base / "train.jsonl", base / "c.jsonl", 9, 42, set())

    def test_threshold_choice_scores_and_no_overwrite(self):
        record = parse_claim_evidence({"claim_id": "x", "claim": "Mars has two moons",
                                       "evidence": [{"evidence_id": "e", "text": "Mars has moons"}]})
        self.assertEqual(overlap_score(record), 0.75)
        scores, gold = [0.2, 0.4, 0.6, 0.8], ["CONTRADICTED", "CONTRADICTED", "SUPPORTED", "SUPPORTED"]
        best, search = choose_threshold(
            gold, lambda t: ["SUPPORTED" if s >= t else "UNSUPPORTED" for s in scores], [0.3, 0.5, 0.7])
        self.assertEqual(best, 0.5)
        self.assertEqual(len(search), 3)
        with self.assertRaises(ValueError):
            choose_threshold(gold, lambda t: gold, [0.7, 0.3])

        class FakeEncoder:  # unit vectors keyed by text, so cosines are known
            vectors = {"c1": (1.0, 0.0), "c2": (0.0, 1.0), "e1": (1.0, 0.0), "e2": (0.6, 0.8), "e3": (0.0, 1.0)}
            def encode(self, texts, batch_size, normalize_embeddings):
                import numpy
                return numpy.array([self.vectors[t] for t in texts])
        records = [parse_claim_evidence({"claim_id": "1", "claim": "c1", "evidence": [
                       {"evidence_id": "a", "text": "e2"}, {"evidence_id": "b", "text": "e1"}]}),
                   parse_claim_evidence({"claim_id": "2", "claim": "c2", "evidence": [
                       {"evidence_id": "a", "text": "e3"}]})]
        self.assertEqual([round(s, 6) for s in embedding_similarities(FakeEncoder(), records)], [1.0, 1.0])
        with tempfile.TemporaryDirectory() as temp:
            save_run(Path(temp) / "run", {}, [], {})
            with self.assertRaises(FileExistsError):
                save_run(Path(temp) / "run", {}, [], {})

    def test_nei_evidence_is_retrieved_never_empty(self):
        self.assertEqual(title_key("Gladiator_-LRB-2000_film-RRB-"), "gladiator")
        self.assertEqual(title_key("Guns_N'_Roses"), "guns n roses")
        self.assertIn("mars rover", claim_phrases("The Mars Rover landed in 2004."))
        self.assertNotIn("the", claim_phrases("The Mars Rover landed in 2004."))
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            wiki = base / "wiki-pages"
            wiki.mkdir()
            pages = [{"id": "Mars", "lines": "0\tMars is the fourth planet.\n1\tMars has two moons named Phobos and Deimos.\n"},
                     {"id": "Mars_-LRB-band-RRB-", "lines": "0\tMars is a band.\n"},
                     {"id": "Venus", "lines": "0\tVenus is hot.\n"}]
            (wiki / "wiki-001.jsonl").write_text("\n".join(json.dumps(p) for p in pages) + "\n")
            claims = [{"id": 7, "claim": "Mars has a moon called Phobos.", "label": "NOT ENOUGH INFO", "evidence": [[[1, 2, None, None]]]},
                      {"id": 8, "claim": "nobody knows this.", "label": "NOT ENOUGH INFO", "evidence": [[[1, 3, None, None]]]},
                      {"id": 9, "claim": "Mars is red.", "label": "SUPPORTS", "evidence": [[[1, 4, "Mars", 0]]]}]
            path = base / "claims.jsonl"
            path.write_text("\n".join(json.dumps(c) for c in claims) + "\n")
            records, report = retrieve_nei_evidence(path, wiki)
            self.assertEqual((report["nei_claims"], report["retrieved"], report["no_matching_page"]), (2, 1, 1))
            record = records[0]
            self.assertEqual((record.gold_label, record.evidence_source, record.selected_group), ("UNSUPPORTED", "retrieved", -1))
            self.assertEqual(record.claim.evidence[0].source_document_id, "Mars")  # undisambiguated page first
            self.assertEqual(record.claim.evidence[0].text, "Mars has two moons named Phobos and Deimos.")
            self.assertEqual(record.to_dict()["evidence_source"], "retrieved")
            self.assertEqual(load_source_prior(path, include_nei=True), ["UNSUPPORTED", "UNSUPPORTED", "SUPPORTED"])

    def test_three_class_threshold_scores_unsupported_as_itself(self):
        gold = ["SUPPORTED", "UNSUPPORTED", "UNSUPPORTED"]
        scores = [0.9, 0.4, 0.2]
        best, _ = choose_threshold(gold, lambda t: ["SUPPORTED" if s >= t else "UNSUPPORTED" for s in scores],
                                   [0.3, 0.5], labels=("SUPPORTED", "CONTRADICTED", "UNSUPPORTED"))
        self.assertEqual(best, 0.5)

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
