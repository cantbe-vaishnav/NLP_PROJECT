"""Build the balanced two-class FEVER training split for Task B fine-tuning.

Inputs (never modified): data/raw/fever/train.jsonl, data/raw/fever/shared_task_dev.jsonl, data/raw/fever/wiki-pages/,
and the existing prepared validation and test sets under outputs/task_b/fever_prepared/.
Outputs (a new folder; an existing one is never overwritten), Git-ignored under outputs/task_b/:
  outputs/task_b/fever_train/two_class_balanced_seed42/
    eligible_claims.jsonl   SUPPORTS/REFUTES training rows left after the claim-text exclusions (unchanged rows)
    resolution_report.json  gold-evidence resolution of the eligible rows (same resolver as validation and test)
    records.jsonl           the balanced split: every resolved REFUTES row + an equal seeded sample of SUPPORTS rows
    split_manifest.json     source hashes, seed, exclusion counts, final counts and leakage checks
Exclusions, by claim_key text (case and spacing ignored, as for the validation sample): any dev/test claim text,
any validation claim text (all 4,000 sampled rows, whatever their id), then texts with conflicting training labels.
"""

import argparse
import hashlib
import json
import subprocess
import sys
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from task_b.fever import balanced_sample, claim_key, prepare_fever, select_training_claims, write_prepared  # noqa: E402

FEVER = ROOT / "data/raw/fever"
PREPARED = ROOT / "outputs/task_b/fever_prepared"
VALIDATION_DIR = PREPARED / "validation_seed42_n2000"


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def directory_sha256(directory):
    """One hash over every *.jsonl file name and its contents, in sorted order."""
    digest = hashlib.sha256()
    files = sorted(Path(directory).glob("*.jsonl"))
    for path in files:
        digest.update(path.name.encode("utf-8"))
        digest.update(bytes.fromhex(sha256(path)))
    return digest.hexdigest(), len(files)


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def nfc_key(text):
    """Task A's comparison_key (NFC first), used only as a robustness check of the claim_key exclusions."""
    return " ".join(unicodedata.normalize("NFC", text).casefold().split())


def git_state():
    def git(*args):
        try:
            return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
        except (OSError, subprocess.CalledProcessError):
            return None
    status = git("status", "--porcelain")
    return {"commit": git("rev-parse", "HEAD"), "dirty": None if status is None else bool(status)}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/task_b/fever_train/two_class_balanced_seed42")
    args = parser.parse_args()

    train_path, dev_path, wiki_dir = FEVER / "train.jsonl", FEVER / "shared_task_dev.jsonl", FEVER / "wiki-pages"
    validation_claims, validation_records = VALIDATION_DIR / "claims.jsonl", VALIDATION_DIR / "records.jsonl"
    test_records = PREPARED / "test/records.jsonl"
    dev_rows, validation_rows = read_jsonl(dev_path), read_jsonl(validation_claims)
    exclusions = {"dev_test_claim_text": {claim_key(row["claim"]) for row in dev_rows},
                  "validation_claim_text": {claim_key(row["claim"]) for row in validation_rows}}

    eligible, selection = select_training_claims(train_path, exclusions)
    args.output.mkdir(parents=True, exist_ok=False)  # refuses to reuse an existing split folder
    eligible_path = args.output / "eligible_claims.jsonl"
    eligible_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in eligible), encoding="utf-8")
    print("Resolving gold evidence for", len(eligible), "eligible rows; the Wikipedia scan takes several minutes.")
    resolved, resolution = prepare_fever(eligible_path, wiki_dir)
    split = balanced_sample(resolved, args.seed)
    write_prepared(split, resolution, args.output)

    # Leakage checks on the written split, against every validation and test text and id.
    train_out = read_jsonl(args.output / "records.jsonl")
    texts = [row["claim"]["claim"] for row in train_out]
    others = {"dev_test_source_all_labels": [row["claim"] for row in dev_rows],
              "test_records": [row["claim"]["claim"] for row in read_jsonl(test_records)],
              "validation_claims_4000": [row["claim"] for row in validation_rows],
              "validation_records": [row["claim"]["claim"] for row in read_jsonl(validation_records)]}
    overlap = {name: {"claim_key": len({claim_key(t) for t in texts} & {claim_key(t) for t in other}),
                      "nfc_claim_key": len({nfc_key(t) for t in texts} & {nfc_key(t) for t in other})}
               for name, other in others.items()}
    train_ids = [str(row["raw_id"]) for row in train_out]
    id_overlap = {"validation": len(set(train_ids) & {str(row["id"]) for row in validation_rows}),
                  "dev_test": len(set(train_ids) & {str(row["id"]) for row in dev_rows})}
    labels_per_text = {}
    for row in train_out:
        labels_per_text.setdefault(claim_key(row["claim"]["claim"]), set()).add(row["source_label"])
    checks = {"claim_text_overlap": overlap, "id_overlap": id_overlap,
              "duplicate_ids_in_split": len(train_ids) - len(set(train_ids)),
              "conflicting_label_texts_in_split": sum(len(labels) > 1 for labels in labels_per_text.values()),
              "duplicate_claim_texts_in_split": len(texts) - len(labels_per_text)}
    failed = [name for name, counts in overlap.items() if any(counts.values())]
    if failed or any(id_overlap.values()) or checks["duplicate_ids_in_split"] or checks["conflicting_label_texts_in_split"]:
        raise AssertionError(f"leakage checks failed: {checks}")

    resolved_by_label = Counter(record.gold_label for record in resolved)
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(), "builder": "scripts/build_task_b_train_split.py",
        "git": git_state(), "seed": args.seed, "python": sys.version.split()[0],
        "design": "every resolved REFUTES row + an equal seeded random.Random(seed).sample of resolved SUPPORTS rows",
        "label_mapping": {"SUPPORTS": "SUPPORTED", "REFUTES": "CONTRADICTED"},
        "sources": {"train": {"path": str(train_path.relative_to(ROOT)), "sha256": sha256(train_path)},
                    "dev_test_source": {"path": str(dev_path.relative_to(ROOT)), "sha256": sha256(dev_path)},
                    "validation_claims": {"path": str(validation_claims.relative_to(ROOT)), "sha256": sha256(validation_claims)},
                    "validation_records": {"path": str(validation_records.relative_to(ROOT)), "sha256": sha256(validation_records)},
                    "test_records": {"path": str(test_records.relative_to(ROOT)), "sha256": sha256(test_records)},
                    "wiki_pages": dict(zip(("sha256_of_file_hashes", "files"), directory_sha256(wiki_dir)),
                                       path=str(wiki_dir.relative_to(ROOT)))},
        "selection": selection,
        "resolution": {"eligible_rows": len(eligible), "resolved": resolution["resolved"],
                       "unresolved": resolution["unresolved"], "resolved_by_label": dict(resolved_by_label)},
        "split": {"rows": len(split), "by_label": dict(Counter(record.gold_label for record in split)),
                  "supported_not_sampled": resolved_by_label["SUPPORTED"] - len(split) // 2},
        "checks": checks,
        "outputs": {name: sha256(args.output / name) for name in ("eligible_claims.jsonl", "records.jsonl")},
    }
    (args.output / "split_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({key: manifest[key] for key in ("selection", "resolution", "split", "checks")}, indent=2))
    print("Saved to", args.output.relative_to(ROOT))


if __name__ == "__main__":
    main()
