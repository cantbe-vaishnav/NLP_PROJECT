import unittest

from task_a.binary_metrics import binary_metrics, headline_metrics


class BinaryMetricsTests(unittest.TestCase):
    def test_known_confusion(self):
        gold = [1, 1, 1, 0, 0, 0, 0, 0]
        pred = [1, 1, 0, 1, 0, 0, 0, 0]
        m = binary_metrics(gold, pred)
        self.assertEqual(m["confusion_matrix"], {"tn": 4, "fp": 1, "fn": 1, "tp": 2})
        self.assertAlmostEqual(m["per_class"]["ADVERSARIAL"]["precision"], 2 / 3)
        self.assertAlmostEqual(m["per_class"]["ADVERSARIAL"]["recall"], 2 / 3)
        self.assertAlmostEqual(m["per_class"]["BENIGN"]["precision"], 4 / 5)
        self.assertAlmostEqual(m["fpr"], 1 / 5)
        self.assertAlmostEqual(m["fnr"], 1 / 3)
        self.assertAlmostEqual(m["accuracy"], 6 / 8)
        self.assertAlmostEqual(m["macro_f1"], (2 / 3 + 0.8) / 2)

    def test_missing_class_gives_none_not_invented_values(self):
        m = binary_metrics([0, 0], [0, 0])
        self.assertIsNone(m["per_class"]["ADVERSARIAL"]["recall"])
        self.assertIsNone(m["macro_f1"])
        self.assertEqual(m["fpr"], 0.0)

    def test_headline_metrics_order_and_values(self):
        m = binary_metrics([1, 1, 0, 0], [1, 0, 0, 1])
        h = headline_metrics(m)
        self.assertEqual(list(h), ["Accuracy", "Macro-F1", "Adversarial precision", "Adversarial recall",
                                   "Adversarial F1", "False-positive rate"])
        self.assertEqual(h["Adversarial recall"], m["per_class"]["ADVERSARIAL"]["recall"])
        self.assertEqual(h["False-positive rate"], m["fpr"])

    def test_invalid_input(self):
        with self.assertRaises(ValueError):
            binary_metrics([1], [])
        with self.assertRaises(ValueError):
            binary_metrics([2], [1])


if __name__ == "__main__":
    unittest.main()
