import json
import tempfile
import unittest
from pathlib import Path

from task_b.data import LABELS, load_claims, map_fever_label


def write_jsonl(records):
    handle = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
    handle.write("\n".join(json.dumps(r) for r in records) + "\n")
    handle.close()
    return Path(handle.name)


# Format fixtures only: not research data.
VALID = {"id": "a", "claim": "claim text", "evidence": "evidence text", "label": "SUPPORTED"}


class TaskBDataTests(unittest.TestCase):
    def test_fever_mapping(self):
        self.assertEqual(map_fever_label("SUPPORTS"), "SUPPORTED")
        self.assertEqual(map_fever_label("REFUTES"), "CONTRADICTED")
        self.assertEqual(map_fever_label("NOT ENOUGH INFO"), "UNSUPPORTED")
        with self.assertRaises(ValueError):
            map_fever_label("MAYBE")

    def test_load_valid_file(self):
        path = write_jsonl([VALID, {**VALID, "id": "b", "label": "UNSUPPORTED"}])
        records = load_claims(path)
        self.assertEqual([r["label"] for r in records], ["SUPPORTED", "UNSUPPORTED"])
        self.assertTrue(set(r["label"] for r in records) <= set(LABELS))

    def test_rejects_bad_records(self):
        for bad in ({**VALID, "label": "SUPPORTS"}, {**VALID, "evidence": "  "},
                    {k: v for k, v in VALID.items() if k != "claim"}):
            with self.assertRaises(ValueError):
                load_claims(write_jsonl([bad]))
        with self.assertRaises(ValueError):
            load_claims(write_jsonl([VALID, VALID]))  # duplicate id


if __name__ == "__main__":
    unittest.main()
