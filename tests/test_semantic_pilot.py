import csv
from pathlib import Path
import tempfile
import unittest

from task_a.semantic_pilot import analyze, cohens_kappa, read_annotations, sample_unique_strata


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

    def test_kappa(self):
        self.assertEqual(cohens_kappa(["BENIGN", "ADVERSARIAL"],
                                     ["BENIGN", "ADVERSARIAL"]), 1.0)
        self.assertAlmostEqual(cohens_kappa(["BENIGN", "BENIGN", "ADVERSARIAL", "ADVERSARIAL"],
                                           ["BENIGN", "ADVERSARIAL", "BENIGN", "ADVERSARIAL"]), 0.0)

    def test_annotation_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "review.csv"
            with path.open("w", newline="") as output:
                writer = csv.DictWriter(output, fieldnames=["pilot_id", "prompt",
                    "safellm_label", "reviewer_id", "rationale"])
                writer.writeheader(); writer.writerow({"pilot_id": "p1", "prompt": "fixture",
                    "safellm_label": "benign", "reviewer_id": "member-1", "rationale": "No redirect."})
            result = read_annotations(path, ["p1"], "member-1")
            self.assertEqual(result["p1"]["label"], "BENIGN")

    def test_analysis_queues_disagreement_and_quarantine(self):
        master = [
            {"pilot_id": "p1", "prompt": "a", "source_adversarial": False,
             "sampling_stratum": "false__unharmful"},
            {"pilot_id": "p2", "prompt": "b", "source_adversarial": True,
             "sampling_stratum": "true__harmful"},
        ]
        a = {"p1": {"label": "BENIGN", "rationale": "x"},
             "p2": {"label": "QUARANTINE", "rationale": "x"}}
        b = {"p1": {"label": "BENIGN", "rationale": "y"},
             "p2": {"label": "ADVERSARIAL", "rationale": "y"}}
        result, queue = analyze(master, a, b)
        self.assertEqual(result["agreement_rate"], 0.5)
        self.assertEqual(result["adjudication_queue_rows"], 1)
        self.assertEqual(len(queue), 1)


if __name__ == "__main__":
    unittest.main()
