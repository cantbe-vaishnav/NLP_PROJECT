import json
import unittest

from task_a.baseline import (
    SMOKE_BANNER, cross_validate, duplicate_groups, grouped_stratified_folds,
    per_class_metrics, split_manifest, unanimous_records, validate_label)
from task_a.semantic_pilot import LABELS


def master_rows(n):
    return [{"pilot_id": f"p{i}", "prompt": f"unique prompt number {i} about topic {i * 7}"}
            for i in range(n)]


def reviews_for(master, labels_by_reviewer):
    return {r: [{"pilot_id": m["pilot_id"], "prompt": m["prompt"], "label": label, "rationale": "x"}
                for m, label in zip(master, labels)]
            for r, labels in labels_by_reviewer.items()}


def records(label_counts):
    out = []
    for label, n in label_counts.items():
        out += [{"id": f"{label[:3]}{i}", "prompt": f"{label} sample {i} text {i * 13}", "label": label}
                for i in range(n)]
    return out


class LabelAndEligibilityTests(unittest.TestCase):
    def test_label_validation_is_exact(self):
        for label in LABELS:
            self.assertEqual(validate_label(label), label)
        for bad in ("benign", "SAFE", "", None, "UNSAFE"):
            with self.assertRaises(ValueError):
                validate_label(bad)

    def test_only_unanimous_items_and_no_vote_resolution(self):
        master = master_rows(4)
        reviews = reviews_for(master, {
            "1": ["BENIGN", "HARMFUL", "ADVERSARIAL", "QUARANTINE"],
            "2": ["BENIGN", "HARMFUL", "ADVERSARIAL", "BENIGN"],
            "3": ["BENIGN", "BENIGN", "HARMFUL", "ADVERSARIAL"]})
        got = unanimous_records(master, reviews)
        self.assertEqual([(r["id"], r["label"]) for r in got], [("p0", "BENIGN")])

    def test_exclusions_are_explicit_and_unknown_ids_fail(self):
        master = master_rows(2)
        same = reviews_for(master, {r: ["BENIGN", "HARMFUL"] for r in "123"})
        self.assertEqual([r["id"] for r in unanimous_records(master, same, ["p0"])], ["p1"])
        with self.assertRaises(ValueError):
            unanimous_records(master, same, ["nope"])

    def test_invalid_reviewer_label_fails(self):
        master = master_rows(1)
        with self.assertRaises(ValueError):
            unanimous_records(master, reviews_for(master, {r: ["maybe"] for r in "123"}))

    def test_prompt_mismatch_fails_unless_excluded(self):
        master = master_rows(1)
        reviews = reviews_for(master, {r: ["BENIGN"] for r in "123"})
        for rows in reviews.values():
            rows[0]["prompt"] = "garbled"
        with self.assertRaises(ValueError):
            unanimous_records(master, reviews)
        self.assertEqual(unanimous_records(master, reviews, ["p0"]), [])

    def test_model_input_is_master_prompt(self):
        master = master_rows(1)
        reviews = reviews_for(master, {r: ["HARMFUL"] for r in "123"})
        self.assertEqual(unanimous_records(master, reviews)[0]["prompt"], master[0]["prompt"])


class SplitTests(unittest.TestCase):
    def test_duplicates_share_a_group(self):
        recs = [{"id": "a", "prompt": "How do I bake  a cake today?", "label": "BENIGN"},
                {"id": "b", "prompt": "how do i bake a cake today?", "label": "BENIGN"},
                {"id": "c", "prompt": "completely different words entirely here now", "label": "HARMFUL"}]
        groups = duplicate_groups(recs)
        self.assertEqual(groups["a"], groups["b"])
        self.assertNotEqual(groups["a"], groups["c"])

    def test_near_duplicate_is_grouped(self):
        base = "please explain in detail how the water cycle works for students"
        recs = [{"id": "a", "prompt": base, "label": "BENIGN"},
                {"id": "b", "prompt": base + " today", "label": "BENIGN"},
                {"id": "c", "prompt": "unrelated question about tax filing deadlines next year", "label": "BENIGN"}]
        groups = duplicate_groups(recs, threshold=0.6)
        self.assertEqual(groups["a"], groups["b"])
        self.assertNotEqual(groups["a"], groups["c"])

    def test_folds_are_deterministic_and_keep_groups_together(self):
        recs = records({"BENIGN": 20, "HARMFUL": 10, "ADVERSARIAL": 10})
        groups = {r["id"]: f"g{i // 2}" for i, r in enumerate(recs)}  # pairs share a group
        first = grouped_stratified_folds(recs, groups, k=5, seed=1)
        self.assertEqual(first, grouped_stratified_folds(recs, groups, k=5, seed=1))
        self.assertEqual(set(first), {r["id"] for r in recs})
        by_group = {}
        for rid, fold in first.items():
            by_group.setdefault(groups[rid], set()).add(fold)
        self.assertTrue(all(len(f) == 1 for f in by_group.values()))
        self.assertEqual(set(first.values()), set(range(5)))

    def test_every_present_class_appears_in_every_fold(self):
        recs = records({"BENIGN": 15, "HARMFUL": 10, "ADVERSARIAL": 10})
        groups = {r["id"]: r["id"] for r in recs}
        folds = grouped_stratified_folds(recs, groups, k=5)
        for fold in range(5):
            self.assertEqual({r["label"] for r in recs if folds[r["id"]] == fold},
                             {"BENIGN", "HARMFUL", "ADVERSARIAL"})

    def test_too_few_groups_fails(self):
        recs = records({"BENIGN": 3})
        with self.assertRaises(ValueError):
            grouped_stratified_folds(recs, {r["id"]: "g" for r in recs}, k=2)

    def test_manifest_is_id_only(self):
        recs = records({"BENIGN": 5, "HARMFUL": 5})
        groups = {r["id"]: r["id"] for r in recs}
        manifest = split_manifest(grouped_stratified_folds(recs, groups, 2), groups, 2)
        text = json.dumps(manifest)
        for r in recs:
            self.assertNotIn(r["prompt"], text)
        self.assertEqual(set(manifest), {"k", "folds", "group_of"})
        self.assertFalse(any(label in text for label in LABELS))
        self.assertEqual(sorted(i for ids in manifest["folds"].values() for i in ids),
                         sorted(r["id"] for r in recs))


class MetricsTests(unittest.TestCase):
    def test_known_confusion_and_metrics(self):
        gold = ["BENIGN"] * 4 + ["HARMFUL"] * 2 + ["ADVERSARIAL"] * 2
        pred = ["BENIGN", "BENIGN", "BENIGN", "HARMFUL", "HARMFUL", "HARMFUL", "ADVERSARIAL", "BENIGN"]
        m = per_class_metrics(gold, pred)
        c = m["per_class"]
        self.assertEqual(c["BENIGN"]["support"], 4)
        self.assertAlmostEqual(c["BENIGN"]["precision"], 3 / 4)
        self.assertAlmostEqual(c["BENIGN"]["recall"], 3 / 4)
        self.assertAlmostEqual(c["HARMFUL"]["precision"], 2 / 3)  # 3 predicted HARMFUL, 2 correct
        self.assertAlmostEqual(c["HARMFUL"]["recall"], 1.0)
        self.assertAlmostEqual(c["ADVERSARIAL"]["recall"], 1 / 2)
        self.assertEqual(m["confusion_matrix"]["counts"]["BENIGN"]["HARMFUL"], 1)
        self.assertEqual(m["confusion_matrix"]["rows_gold_cols_pred"], list(LABELS))
        f1s = [c[label]["f1"] for label in ("BENIGN", "HARMFUL", "ADVERSARIAL")]
        self.assertAlmostEqual(m["macro_f1"], sum(f1s) / 3)
        self.assertAlmostEqual(m["accuracy"], 6 / 8)  # 3 BENIGN + 2 HARMFUL + 1 ADVERSARIAL

    def test_absent_class_is_reported_not_fabricated(self):
        m = per_class_metrics(["BENIGN", "HARMFUL"], ["BENIGN", "HARMFUL"])
        q = m["per_class"]["QUARANTINE"]
        self.assertTrue(q["absent_from_gold"])
        self.assertEqual((q["support"], q["precision"], q["recall"], q["f1"]), (0, None, None, None))
        self.assertIn("QUARANTINE", m["absent_classes"])
        self.assertNotIn("QUARANTINE", m["macro_f1_classes"])
        self.assertEqual(m["macro_f1"], 1.0)

    def test_predicting_an_absent_class_is_a_false_positive(self):
        m = per_class_metrics(["BENIGN", "BENIGN"], ["BENIGN", "QUARANTINE"])
        q = m["per_class"]["QUARANTINE"]
        self.assertEqual((q["precision"], q["recall"], q["f1"]), (0.0, None, None))
        self.assertNotIn("QUARANTINE", m["macro_f1_classes"])

    def test_invalid_labels_and_length_mismatch_fail(self):
        with self.assertRaises(ValueError):
            per_class_metrics(["BENIGN"], ["safe"])
        with self.assertRaises(ValueError):
            per_class_metrics(["BENIGN"], [])

    def test_banner_declares_smoke_test(self):
        self.assertIn("SMOKE TEST ONLY", SMOKE_BANNER)
        self.assertIn("Not a research result", SMOKE_BANNER)


class CrossValidationTests(unittest.TestCase):
    def test_out_of_fold_only(self):
        recs = records({"BENIGN": 10, "HARMFUL": 10})
        groups = {r["id"]: r["id"] for r in recs}
        assignment = grouped_stratified_folds(recs, groups, 5)
        seen = []

        def spy(train_x, train_y, test_x, seed, params):
            seen.append((set(train_x), set(test_x)))
            return ["BENIGN"] * len(test_x)

        preds, info = cross_validate(recs, assignment, 5, fit_predict=spy)
        self.assertEqual(set(preds), {r["id"] for r in recs})
        for train, test in seen:
            self.assertFalse(train & test)
        self.assertEqual(sum(i["eval_items"] for i in info), len(recs))

    def test_model_returning_invalid_label_fails(self):
        recs = records({"BENIGN": 4, "HARMFUL": 4})
        groups = {r["id"]: r["id"] for r in recs}
        assignment = grouped_stratified_folds(recs, groups, 2)
        with self.assertRaises(ValueError):
            cross_validate(recs, assignment, 2, fit_predict=lambda a, b, c, s, p: ["junk"] * len(c))

    def test_real_tfidf_logreg_runs_when_sklearn_is_available(self):
        try:
            import sklearn  # noqa: F401
        except ImportError:
            self.skipTest("scikit-learn not installed in this interpreter")
        recs = records({"BENIGN": 10, "HARMFUL": 10})
        groups = {r["id"]: r["id"] for r in recs}
        assignment = grouped_stratified_folds(recs, groups, 5)
        preds, _ = cross_validate(recs, assignment, 5)
        self.assertTrue(set(preds.values()) <= set(LABELS))


if __name__ == "__main__":
    unittest.main()
