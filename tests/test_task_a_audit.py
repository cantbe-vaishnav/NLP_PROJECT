import unittest

from task_a.audit import summarize_sample


class SampleAuditTests(unittest.TestCase):
    def test_counts_preserve_source_labels_without_mapping(self):
        report = summarize_sample([
            {"row": {"text": "Example", "label": 1}},
            {"row": {"text": "Example", "label": 0}},
        ])
        self.assertEqual(report["source_label_distribution"], {"0": 1, "1": 1})
        self.assertEqual(report["exact_duplicate_excess"], 1)
        self.assertFalse(report["safellm_labels_assigned"])

    def test_missing_empty_and_malformed_are_reported(self):
        report = summarize_sample([None, {}, {"row": {"text": None}},
                                   {"row": {"text": " "}}])
        self.assertEqual(report["malformed_text_rows"], 3)
        self.assertEqual(report["empty_text_rows"], 1)
        self.assertEqual(report["source_label_distribution"], {"null": 1})

    def test_empty_sample(self):
        report = summarize_sample([])
        self.assertEqual(report["rows_fetched"], 0)
        self.assertIsNone(report["min_characters"])

    def test_text_is_not_normalized(self):
        report = summarize_sample([{"row": {"text": t, "label": 0}}
                                   for t in ["A", "a", "a\u200b"]])
        self.assertEqual(report["exact_duplicate_excess"], 0)

    def test_hash_is_deterministic(self):
        rows = [{"row": {"text": "unit-test fixture", "label": 0}}]
        self.assertEqual(summarize_sample(rows), summarize_sample(rows))
