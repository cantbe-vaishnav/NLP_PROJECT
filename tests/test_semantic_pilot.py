import csv
from pathlib import Path
import tempfile
import unittest

from task_a.semantic_pilot import (
    LABELS, analyze_agreement, cohens_kappa, confusion_matrix, fleiss_kappa, load_reviews,
    expected_pilot_ids, read_annotations, render_report, sample_unique_strata,
    source_label_crosstab, stratum_disagreement)

FIELDS = ["pilot_id", "prompt", "safellm_label", "reviewer_id", "rationale"]


def write_review(path, reviewer, labels, prompts=None):
    with Path(path).open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=FIELDS)
        writer.writeheader()
        for i, label in enumerate(labels):
            writer.writerow({"pilot_id": f"p{i}", "prompt": (prompts or {}).get(i, f"prompt {i}"),
                             "safellm_label": label, "reviewer_id": reviewer,
                             "rationale": f"reason {reviewer}-{i}"})


def reviews_from(labels_by_reviewer):
    return {r: [{"pilot_id": f"p{i}", "prompt": f"prompt {i}", "label": l,
                 "rationale": f"reason {r}-{i}"} for i, l in enumerate(ls)]
            for r, ls in labels_by_reviewer.items()}


class SemanticPilotTests(unittest.TestCase):
    def test_stratified_sampling_is_unique_and_deterministic(self):
        rows = []
        for flag in [False, True]:
            for harm in ["harmful", "unharmful"]:
                for index in range(4):
                    rows.append({"prompt": f"{flag} {harm} item {index}",
                                 "adversarial": flag, "prompt_harm_label": harm,
                                 "subcategory": "fixture"})
        rows.append({**rows[0], "prompt": rows[0]["prompt"].upper()})
        first, summary = sample_unique_strata(rows, quota=3, seed=42)
        second, _ = sample_unique_strata(rows, quota=3, seed=42)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 12)
        self.assertEqual(len({row["prompt"].casefold() for row in first}), 12)
        self.assertEqual(summary["false__harmful"]["duplicate_candidates_skipped"], 1)

    def test_shortfall_is_not_duplicated(self):
        rows = [{"prompt": "only", "adversarial": False,
                 "prompt_harm_label": "harmful", "subcategory": "fixture"}]
        selected, summary = sample_unique_strata(rows, quota=2)
        self.assertEqual(len(selected), 1)
        self.assertEqual(summary["false__harmful"]["shortfall"], 1)

    def test_schema_is_exactly_four_labels(self):
        self.assertEqual(LABELS, ("BENIGN", "HARMFUL", "ADVERSARIAL", "QUARANTINE"))

    def test_kappa(self):
        self.assertEqual(cohens_kappa(["BENIGN", "HARMFUL"], ["BENIGN", "HARMFUL"]), 1.0)
        self.assertAlmostEqual(cohens_kappa(["BENIGN", "BENIGN", "HARMFUL", "HARMFUL"],
                                           ["BENIGN", "HARMFUL", "BENIGN", "HARMFUL"]), 0.0)

    def test_fleiss_kappa_hand_computed(self):
        self.assertAlmostEqual(fleiss_kappa([["BENIGN", "BENIGN"], ["BENIGN", "BENIGN"],
                                             ["BENIGN", "HARMFUL"]]), -0.2)
        same = ["BENIGN", "HARMFUL", "ADVERSARIAL", "QUARANTINE"]
        self.assertEqual(fleiss_kappa([same, same, same]), 1.0)

    def test_confusion_matrix_keeps_four_labels_separate(self):
        matrix = confusion_matrix(["BENIGN", "HARMFUL"], ["BENIGN", "ADVERSARIAL"])
        self.assertEqual(matrix["HARMFUL"]["ADVERSARIAL"], 1)
        self.assertEqual(matrix["HARMFUL"]["BENIGN"], 0)
        self.assertEqual(set(matrix), set(LABELS))

    def test_annotation_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "review.csv"
            write_review(path, "1", ["benign", "harmful"])
            result = read_annotations(path, "1", ["p0", "p1"])
            self.assertEqual([r["label"] for r in result], ["BENIGN", "HARMFUL"])

    def test_annotation_validation_rejects_bad_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "review.csv"
            for labels, reviewer in ((["Q"], "1"), (["B"], "1"), ([""], "1"), (["BENIGN"], "2")):
                write_review(path, reviewer, labels)
                with self.subTest(labels=labels, reviewer=reviewer):
                    with self.assertRaises(ValueError):
                        read_annotations(path, "1")
                path.unlink()

    def test_reads_xlsx_with_numeric_reviewer_id(self):
        from openpyxl import Workbook
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "review.xlsx"
            book = Workbook()
            sheet = book.active
            sheet.append(FIELDS)
            sheet.append(["p0", "prompt 0", "ADVERSARIAL", 2, "reason"])
            book.save(path)
            self.assertEqual(read_annotations(path, "2")[0]["label"], "ADVERSARIAL")

    def test_load_reviews_requires_same_ids_and_prompts(self):
        with tempfile.TemporaryDirectory() as tmp:
            files = {}
            for r in "123":
                files[r] = Path(tmp) / f"r{r}.csv"
                write_review(files[r], r, ["BENIGN", "HARMFUL"])
            ids = ["p0", "p1"]
            self.assertEqual(len(load_reviews(files, ids)), 3)
            write_review(files["3"], "3", ["BENIGN", "HARMFUL"], {1: "changed"})
            with self.assertRaises(ValueError):
                load_reviews(files, ids)
            with self.assertRaises(ValueError):
                load_reviews({"1": files["1"], "2": files["2"]}, ids)

    def test_identically_truncated_files_fail_the_200_item_check(self):
        self.assertEqual(expected_pilot_ids()[0], "pilot-001")
        self.assertEqual(expected_pilot_ids()[-1], "pilot-200")
        with tempfile.TemporaryDirectory() as tmp:
            files = {}
            for r in "123":
                files[r] = Path(tmp) / f"r{r}.csv"
                with files[r].open("w", newline="", encoding="utf-8") as output:
                    writer = csv.DictWriter(output, fieldnames=FIELDS)
                    writer.writeheader()
                    for i in range(1, 199):  # pilot-001..pilot-198, identical in all three
                        writer.writerow({"pilot_id": f"pilot-{i:03d}", "prompt": f"p{i}",
                                         "safellm_label": "BENIGN", "reviewer_id": r,
                                         "rationale": "x"})
            with self.assertRaises(ValueError):
                load_reviews(files)  # default expectation: exactly pilot-001..pilot-200
            with self.assertRaises(ValueError):
                load_reviews(files, expected_pilot_ids(198)[::-1])  # wrong order also fails
            self.assertEqual(len(load_reviews(files, expected_pilot_ids(198))), 3)

    def test_stratum_disagreement_and_category(self):
        reviews = reviews_from({"1": ["BENIGN", "HARMFUL"], "2": ["BENIGN", "HARMFUL"],
                                "3": ["BENIGN", "ADVERSARIAL"]})
        master = [{"pilot_id": "p0", "sampling_stratum": "a"},
                  {"pilot_id": "p1", "sampling_stratum": "b"}]
        self.assertEqual(stratum_disagreement(master, reviews)["b"]["items_with_any_disagreement"], 1)
        self.assertEqual(stratum_disagreement(master, reviews)["a"]["items_with_any_disagreement"], 0)
        _, rows = analyze_agreement(reviews)
        self.assertEqual(rows[0]["category"], "majority HARMFUL (2/3); dissent: 3=ADVERSARIAL")

    def test_agreement_analysis_patterns_and_disagreements(self):
        reviews = reviews_from({
            "1": ["BENIGN", "BENIGN", "HARMFUL", "QUARANTINE"],
            "2": ["BENIGN", "HARMFUL", "ADVERSARIAL", "QUARANTINE"],
            "3": ["BENIGN", "HARMFUL", "BENIGN", "QUARANTINE"]})
        result, rows = analyze_agreement(reviews)
        patterns = result["agreement_patterns"]
        self.assertEqual(patterns["unanimous"]["pilot_ids"], ["p0", "p3"])
        self.assertEqual(patterns["two_vs_one"]["pilot_ids"], ["p1"])
        self.assertEqual(patterns["three_way"]["pilot_ids"], ["p2"])
        self.assertEqual([r["pilot_id"] for r in rows], ["p1", "p2"])
        self.assertEqual(rows[1]["reviewer_2_label"], "ADVERSARIAL")
        self.assertEqual(rows[1]["reviewer_3_rationale"], "reason 3-2")
        self.assertNotIn("prompt", rows[0])
        self.assertEqual(result["pairwise"]["1-2"]["raw_agreement_count"], 2)
        self.assertEqual(result["label_distributions"]["1"]["quarantine_count"], 1)
        self.assertFalse(result["independence_verified"])
        self.assertIn("independence has not been verified", render_report(result).lower())
        result["inputs"] = {"location": "external to the repository",
                            "files": {"1": {"name": "f.csv", "sha256": "abc"}}}
        self.assertIn("cannot be reproduced from the repository alone", render_report(result))
        _, with_prompts = analyze_agreement(reviews, include_prompts=True)
        self.assertEqual(with_prompts[0]["prompt"], "prompt 1")

    def test_source_crosstab_is_descriptive_and_keeps_labels_separate(self):
        reviews = reviews_from({"1": ["HARMFUL", "BENIGN"], "2": ["HARMFUL", "BENIGN"],
                                "3": ["HARMFUL", "BENIGN"]})
        master = [{"pilot_id": "p0", "source_adversarial": False},
                  {"pilot_id": "p1", "source_adversarial": True}]
        table = source_label_crosstab(master, reviews)["1"]
        self.assertEqual(table["false"]["HARMFUL"], 1)
        self.assertEqual(table["true"]["BENIGN"], 1)
        with self.assertRaises(ValueError):
            source_label_crosstab(master[:1], reviews)


if __name__ == "__main__":
    unittest.main()
