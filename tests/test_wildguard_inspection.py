"""Synthetic engineering fixtures only; not research data or annotations."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
except ImportError:
    pa = None


@unittest.skipIf(pa is None, "Install requirements-data.txt for Parquet checks")
class InspectionTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location(
            "inspection", Path(__file__).resolve().parents[1] /
            "scripts/inspect_wildguard_files.py")
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def test_source_labels_and_roleplay_are_preserved(self):
        rows = [dict(prompt="Pretend to be a debater.", adversarial=True,
                     prompt_harm_label="unharmful"),
                dict(prompt="Pretend to be a debater.", adversarial=False,
                     prompt_harm_label="harmful")]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixture.parquet"
            pq.write_table(pa.Table.from_pylist(rows), path)
            report = self.module.inspect_file(path)
            self.assertEqual(report["rows"], 2)
            self.assertEqual(report["exact_prompt_duplicate_excess"], 1)
            self.assertEqual(report["source_adversarial_counts"], {"true": 1, "false": 1})
            self.assertFalse(report["safellm_labels_assigned"])
            self.assertEqual(pq.read_table(path).to_pylist(), rows)

    def test_schema_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixture.parquet"
            pq.write_table(pa.table({"prompt": ["fixture"]}), path)
            with self.assertRaises(ValueError):
                self.module.inspect_file(path)

    def test_nulls_remain_visible(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixture.parquet"
            pq.write_table(pa.table({"prompt": [None, " "],
                                     "adversarial": [None, True],
                                     "prompt_harm_label": [None, "unharmful"]}), path)
            report = self.module.inspect_file(path)
            self.assertEqual(report["empty_or_invalid_prompts"], 2)
            self.assertEqual(report["invalid_adversarial_values"], 1)
