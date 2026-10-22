"""Download the two JailbreakHub configurations used by Task A binary detection.

Fetches exactly the Parquet files that `datasets.load_dataset(
"TrustAIRLab/in-the-wild-jailbreak-prompts", <config>)` reads (the card's `data_files`),
at a pinned revision, through the Hugging Face Hub API. Verifies each file against the
Hub's LFS SHA-256 and records provenance. Refuses to overwrite existing files.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

REPO = "TrustAIRLab/in-the-wild-jailbreak-prompts"
CONFIGS = ("jailbreak_2023_12_25", "regular_2023_12_25")


def sha256(path):
    with open(path, "rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", default="a10aab8eff1c73165a442d4464dce192bd28b9c5")
    parser.add_argument("--output-dir", default="data/raw/jailbreakhub")
    parser.add_argument("--provenance", default="results/data_audit/jailbreakhub_download.json")
    args = parser.parse_args()

    from huggingface_hub import HfApi, hf_hub_download
    import pyarrow.parquet as pq

    out = Path(args.output_dir)
    if Path(args.provenance).exists():
        raise FileExistsError(f"{args.provenance} exists; refusing to overwrite")
    info = HfApi().dataset_info(REPO, revision=args.revision, files_metadata=True)
    lfs = {s.rfilename: s.lfs.sha256 for s in info.siblings if s.lfs}
    record = {"repo": REPO, "revision": info.sha, "license": (info.card_data or {}).get("license"),
              "gated": info.gated, "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
              "method": "huggingface_hub.hf_hub_download of the config data_files "
                        "(same files datasets.load_dataset reads)", "configs": {}}
    for config in CONFIGS:
        name = f"{config}/train-00000-of-00001.parquet"
        target = out / name
        if target.exists():
            raise FileExistsError(f"{target} exists; refusing to overwrite")
        local = hf_hub_download(REPO, name, repo_type="dataset", revision=args.revision,
                                local_dir=out)
        digest = sha256(local)
        if digest != lfs[name]:
            raise ValueError(f"{name}: SHA-256 {digest} != Hub LFS {lfs[name]}")
        table = pq.read_table(local)
        record["configs"][config] = {"file": str(Path(local).as_posix()), "sha256": digest,
                                     "bytes": Path(local).stat().st_size, "rows": table.num_rows,
                                     "columns": table.schema.names}
    Path(args.provenance).parent.mkdir(parents=True, exist_ok=True)
    Path(args.provenance).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
