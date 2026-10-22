"""Preview (counts only) of the proposed RQ3 held-out splits. Builds no dataset and trains nothing.

Experiment A: hold out the WildGuardMix harm subcategory "cyberattack", plus every train/validation row (any source)
matching a strict cyber keyword list, so the topic is absent from training and model selection.
Experiment B: hold out the JailbreakHub source; train and select on WildGuardMix only.
Writes results/task_a_rq3_plan/split_preview.json.
"""

import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
HELD_OUT = "cyberattack"
KEYWORDS = re.compile(r"\b(?:hack(?:er|ers|ing|ed)?|malware|ransomware|phishing|keylogger|ddos|botnet|sql injection|"
                      r"backdoor|trojan|spyware|zero-day|brute.?force|password crack\w*|cyber ?attack\w*)\b", re.I)


def counts(frame):
    return {f"{s}|{l}": int(n) for (s, l), n in frame.groupby(["split", "label"]).size().items()}


def main():
    df = pd.read_parquet(ROOT / "data/processed/binary_jailbreak_v2/combined.parquet")
    df["subcategory"] = df["source_metadata"].map(lambda s: json.loads(s).get("subcategory"))
    pool = df["split"].isin(["train", "validation"])
    held = df["subcategory"] == HELD_OUT
    related = df["text"].str.contains(KEYWORDS) & ~held

    a = {"held_out_subcategory": HELD_OUT,
         "train_validation_after_removal": counts(df[pool & ~held & ~related]),
         "removed_from_training_held_out_category": counts(df[pool & held]),
         "removed_from_training_keyword_related": {f"{k[0]}|{k[1]}|{k[2]}": int(v) for k, v in
                                                   df[pool & related].groupby(["split", "source_dataset", "label"]).size().items()},
         "test_held_out_category_from_pool": counts(df[pool & held].assign(split="heldout_pool")),
         "test_held_out_category_official": counts(df[(df["split"] == "test_official") & held]),
         "reference_official_test_without_category": counts(df[(df["split"] == "test_official") & ~held]),
         "reference_jailbreakhub_test": counts(df[df["split"] == "test_jailbreakhub"]),
         "families_shared_between_held_out_and_kept_rows": int(len(set(df.loc[held, "family_id"]) & set(df.loc[~held, "family_id"]))),
         "held_out_rows_matching_keywords": round(float(df.loc[held, "text"].str.contains(KEYWORDS).mean()), 3)}
    sources = df.groupby("family_id")["source_dataset"].nunique()
    b = {"train_validation_wildguardmix_only": counts(df[pool & (df["source_dataset"] == "wildguardmix")]),
         "removed_from_training_jailbreakhub": counts(df[pool & (df["source_dataset"] == "jailbreakhub")]),
         "test_held_out_source_jailbreakhub_test": counts(df[df["split"] == "test_jailbreakhub"]),
         "reference_official_test": counts(df[df["split"] == "test_official"]),
         "mixed_source_families": int((sources > 1).sum()),
         "mixed_source_families_crossing_splits": int((df.groupby("family_id")["split"].nunique() > 1).sum())}
    out = ROOT / "results/task_a_rq3_plan"
    out.mkdir(parents=True, exist_ok=True)
    (out / "split_preview.json").write_text(json.dumps({"experiment_A": a, "experiment_B": b}, indent=2), encoding="utf-8")
    print(json.dumps({"experiment_A": a, "experiment_B": b}, indent=2))


if __name__ == "__main__":
    main()
