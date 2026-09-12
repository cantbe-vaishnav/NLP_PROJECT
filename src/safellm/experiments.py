"""Small, explicit experiment recorder; no training or metric computation."""

import json
import platform
import re
import subprocess
from datetime import datetime, timezone
from importlib.metadata import distributions
from pathlib import Path


def read_config(path):
    """Read and validate the metadata required to identify a run."""
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_config(config)
    return config


def validate_config(config):
    if not isinstance(config, dict):
        raise ValueError("Configuration must be an object")
    for key in ("experiment_id", "research_question", "hypothesis"):
        if not isinstance(config.get(key), str) or not config[key].strip():
            raise ValueError(f"Missing or invalid {key}")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", config["experiment_id"]):
        raise ValueError("experiment_id must be a safe directory name")
    if type(config.get("seed")) is not int or not 0 <= config["seed"] < 2**32:
        raise ValueError("seed must be an integer in [0, 2**32)")
    for section, keys in (("dataset", ("name", "version", "kind")),
                          ("model", ("name", "checkpoint"))):
        value = config.get(section)
        if not isinstance(value, dict) or any(
            not isinstance(value.get(key), str) or not value[key].strip() for key in keys
        ):
            raise ValueError(f"Missing or invalid {section} metadata")
    if config["dataset"]["kind"] not in {"benchmark", "custom", "engineering"}:
        raise ValueError("dataset.kind must be benchmark, custom, or engineering")
    if not isinstance(config.get("parameters"), dict):
        raise ValueError("parameters must be an object")
    json.dumps(config, allow_nan=False)


def _git_metadata():
    def git(*args):
        try:
            return subprocess.check_output(
                ["git", *args], stderr=subprocess.DEVNULL, text=True
            ).strip()
        except (OSError, subprocess.CalledProcessError):
            return None
    commit = git("rev-parse", "HEAD")
    status = git("status", "--porcelain")
    return {"commit": commit, "dirty": None if status is None else bool(status)}


def create_run(config, output_root):
    """Create a new record. Refuse collisions; never invent results or predictions.

    This records the requested seed; model code must actually apply it later.
    Git metadata describes the caller's current checkout.
    """
    validate_config(config)
    manifest = {
        "status": "initialized",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "git": _git_metadata(),
        "packages": sorted(
            f"{d.metadata['Name']}=={d.version}" for d in distributions()
            if d.metadata.get("Name")
        ),
        "artifacts": {"metrics": None, "predictions": None, "errors": None},
    }
    run = Path(output_root) / config["experiment_id"]
    run.mkdir(parents=True, exist_ok=False)
    for name, value in (("config.json", config), ("manifest.json", manifest)):
        (run / name).write_text(
            json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
    (run / "notes.md").write_text(
        "# Run notes\n\nInitialized only. No experiment has been executed.\n\n"
        + str(config.get("notes", "")) + "\n", encoding="utf-8"
    )
    return run
