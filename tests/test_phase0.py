"""Engineering tests only. No test fixture represents research observations."""

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from safellm.experiments import create_run, read_config, validate_config

ROOT = Path(__file__).resolve().parents[1]


class PhaseZeroTests(unittest.TestCase):
    def setUp(self):
        self.config = read_config(ROOT / "configs/phase0.json")

    def test_installed_cli_and_imports(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = subprocess.check_output(
                [sys.executable, "-m", "safellm", "doctor"], cwd=tmp, text=True
            )
        self.assertEqual(json.loads(output)["imports"], "ok")

    def test_run_preserves_metadata_and_does_not_invent_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = create_run(self.config, tmp)
            self.assertEqual(json.loads((run / "config.json").read_text()), self.config)
            manifest = json.loads((run / "manifest.json").read_text())
            self.assertEqual(manifest["status"], "initialized")
            self.assertTrue(manifest["python"])
            self.assertTrue(all(v is None for v in manifest["artifacts"].values()))
            self.assertFalse((run / "metrics.json").exists())
            with self.assertRaises(FileExistsError):
                create_run(self.config, tmp)

    def test_rejects_unsafe_run_names_and_invalid_metadata(self):
        for key, value in (("experiment_id", "../escape"), ("seed", True),
                           ("seed", -1), ("dataset", {}), ("model", {}),
                           ("parameters", []), ("hypothesis", "")):
            with self.subTest(key=key, value=value):
                config = copy.deepcopy(self.config)
                config[key] = value
                with self.assertRaises(ValueError):
                    validate_config(config)

    def test_rejects_nonfinite_config(self):
        self.config["parameters"]["threshold"] = float("nan")
        with self.assertRaises(ValueError):
            validate_config(self.config)

    def test_planned_directories_exist(self):
        for folder in ("configs", "data/raw", "data/interim", "data/processed",
                       "data/annotations", "src/task_a", "src/task_b", "src/pipeline",
                       "experiments/task_a", "experiments/task_b", "experiments/end_to_end",
                       "models", "results/metrics", "results/predictions", "results/figures",
                       "results/error_analysis", "app", "docs/report"):
            with self.subTest(folder=folder):
                self.assertTrue((ROOT / folder).is_dir())


if __name__ == "__main__":
    unittest.main()
