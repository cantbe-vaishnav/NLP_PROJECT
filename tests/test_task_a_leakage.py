import unittest
from task_a.leakage import comparison_key, duplicate_summary, adjacent_near_duplicates


def record(i, text, split="train", flag=False):
    return dict(id=str(i), prompt=text, split=split, adversarial=flag)


class LeakageTests(unittest.TestCase):
    def test_cross_split_conflicts(self):
        rows = [record(1, "text"), record(2, "text", "test", True)]
        summary = duplicate_summary(rows)
        self.assertEqual(summary["cross_official_split_groups"], 1)
        self.assertEqual(summary["conflicting_adversarial_rows"], 2)

    def test_normalized_comparison_is_separate(self):
        rows = [record(1, "Role PLAY"), record(2, "role  play")]
        self.assertEqual(duplicate_summary(rows)["duplicate_excess"], 0)
        self.assertEqual(duplicate_summary(rows, True)["duplicate_excess"], 1)
        self.assertEqual(rows[0]["prompt"], "Role PLAY")

    def test_empty_is_not_a_leakage_group(self):
        self.assertEqual(duplicate_summary([record(1, " "), record(2, "")])[
            "unique_nonempty_prompts"], 0)

    def test_near_diagnostic_detects_small_edit(self):
        rows = [record(1, "one two three four five six seven eight nine ten a"),
                record(2, "one two three four five six seven eight nine ten b", "test")]
        pairs = list(adjacent_near_duplicates(rows, 2, 0.8))
        self.assertEqual(len(pairs), 1)
        self.assertTrue(pairs[0]["cross_official_split"])

    def test_invalid_threshold(self):
        with self.assertRaises(ValueError):
            list(adjacent_near_duplicates([], threshold=2))
