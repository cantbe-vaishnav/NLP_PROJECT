"""Build and validate the Task A RQ2 hard-negative evaluation set (synthetic v1 + external NotInject).

Inputs: project-authored source files in data/synthetic/task_a_hard_negatives_v1/*.txt (synthetic, LLM-authored)
and the NotInject parquet files (MIT, pinned revision) in data/raw/notinject/. Outputs:
  data/processed/task_a_hard_negatives_v1/hard_negatives.parquet  (Git-ignored)
  results/task_a_rq2_hard_negatives/build_manifest.json, validation.json, validation.md  (counts and hashes only)
Checks: schema, unique IDs, pair links, exact/normalised duplicates, near-duplicates (dataset thresholds),
overlap with every split of dataset v2, TF-IDF similarity to training, cue coverage. No model is run here.
"""

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from task_a.cue_audit import CUES, review_priority  # noqa: E402
from task_a.leakage import comparison_key  # noqa: E402

SOURCE_DIR = ROOT / "data/synthetic/task_a_hard_negatives_v1"
NOTINJECT_DIR = ROOT / "data/raw/notinject"
NOTINJECT_REVISION = "847ae76cf8fea5ed325429e569ae8cfef022d2e0"
DATASET = ROOT / "data/processed/binary_jailbreak_v2/combined.parquet"
CATEGORIES = {
    "EDU": "Educational explanations of jailbreaks and prompt injection",
    "SEC": "Cybersecurity research and threat analysis",
    "CLS": "Quoting or classifying malicious prompts for defensive purposes",
    "POL": "Safety-policy and AI-governance discussion",
    "MIT": "Requests to detect, test or mitigate attacks",
    "DOC": "Benign documentation containing suspicious phrases",
    "ROL": "Role-play and personas without any rule override",
    "META": "Transparent questions about the assistant's own rules",
}
HEADER = re.compile(r"^=== (\S+) \| (\S+) \| (\S+) \| ([01]) \| (\S+)\s*$")
COSINE, JACCARD = 0.8, 0.85  # near-duplicate thresholds used by dataset v2


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def parse_sources():
    """One record per '=== id | category | structure | label | pair' block."""
    rows = []
    for path in sorted(SOURCE_DIR.glob("*.txt")):
        current = None
        for line in path.read_text(encoding="utf-8").splitlines():
            match = HEADER.match(line)
            if match:
                current = dict(zip(["example_id", "category", "structure", "label", "pair_id"], match.groups()))
                current.update(label=int(current["label"]), lines=[], source_file=path.name)
                rows.append(current)
            elif current is None:
                raise ValueError(f"{path.name}: text before the first header")
            else:
                current["lines"].append(line)
    for r in rows:
        r["text"] = "\n".join(r.pop("lines")).strip()
        r["pair_id"] = None if r["pair_id"] == "-" else r["pair_id"]
    return pd.DataFrame(rows)


def load_notinject():
    parts = []
    for subset in ["one", "two", "three"]:
        d = pd.read_parquet(NOTINJECT_DIR / f"NotInject_{subset}.parquet")
        parts.append(pd.DataFrame({
            "example_id": [f"notinject:{subset}:{i}" for i in range(len(d))], "text": d["prompt"], "label": 0,
            "category": "NotInject " + d["category"], "structure": f"trigger_words_{subset}",
            "trigger_words": d["word_list"].map(list).map(", ".join), "pair_id": None,
            "source_file": f"NotInject_{subset}.parquet"}))
    return pd.concat(parts, ignore_index=True)


def shingles(text, n=5):
    words = comparison_key(text).split()
    return {" ".join(words[i:i + n]) for i in range(max(1, len(words) - n + 1))}


def near_duplicate_pairs(texts, ids, matrix):
    """Pairs within the set over either near-duplicate threshold."""
    sims = (matrix @ matrix.T).toarray()
    sh = [shingles(t) for t in texts]
    pairs = []
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            jac = len(sh[i] & sh[j]) / max(1, len(sh[i] | sh[j]))
            if sims[i, j] >= COSINE or jac >= JACCARD:
                pairs.append({"a": ids[i], "b": ids[j], "cosine": round(float(sims[i, j]), 3), "jaccard": round(jac, 3)})
    return pairs, sims


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-data", default="data/processed/task_a_hard_negatives_v1")
    parser.add_argument("--out-results", default="results/task_a_rq2_hard_negatives")
    args = parser.parse_args()

    synth = parse_sources().assign(component="synthetic_v1", provenance="synthetic, LLM-authored (Claude), 2026-10-22")
    errors = []
    if synth["example_id"].duplicated().any():
        errors.append(f"duplicate ids: {synth.loc[synth['example_id'].duplicated(), 'example_id'].tolist()}")
    bad_cat = set(synth["category"]) - set(CATEGORIES)
    if bad_cat:
        errors.append(f"unknown categories {bad_cat}")
    for r in synth.itertuples():
        prefix_ok = r.example_id.startswith(("HN-" if r.label == 0 else "ADV-") + r.category + "-")
        if not prefix_ok:
            errors.append(f"{r.example_id}: id prefix does not match label/category")
        if r.label == 1 and (r.pair_id not in set(synth["example_id"]) or not str(r.pair_id).startswith("HN-")):
            errors.append(f"{r.example_id}: adversarial item must pair with an existing HN item")
        if not r.text:
            errors.append(f"{r.example_id}: empty text")
    if errors:
        raise SystemExit("Source validation failed:\n" + "\n".join(errors))

    external = load_notinject().assign(component="notinject",
                                       provenance=f"NotInject (leolee99/NotInject@{NOTINJECT_REVISION[:8]}, MIT)")
    data = pd.concat([synth, external], ignore_index=True)
    data["multilingual"] = data["text"].str.contains(r"[぀-ヿ㐀-鿿가-힯]")
    data["strong_cue"] = data["text"].map(lambda t: review_priority(t)[1]).map(lambda c: ",".join(sorted(c)))
    data["has_strong_cue"] = data["strong_cue"] != ""

    # Overlap with dataset v2 (every split): exact normalised text, and TF-IDF similarity with training settings.
    ds = pd.read_parquet(DATASET, columns=["example_id", "text", "split"])
    keys = dict(zip(ds["text"].map(comparison_key), ds["split"]))
    data["exact_overlap_split"] = data["text"].map(comparison_key).map(keys)
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True).fit(ds.loc[ds["split"] == "train", "text"])
    new = vectorizer.transform(data["text"])
    for split in ["train", "validation", "test_official", "test_jailbreakhub"]:
        sims = []
        ref = vectorizer.transform(ds.loc[ds["split"] == split, "text"])
        for start in range(0, new.shape[0], 500):
            sims.append((new[start:start + 500] @ ref.T).max(axis=1).toarray().ravel())
        data[f"max_sim_{split}"] = np.concatenate(sims).round(4)
    data["closest_train_similarity"] = data["max_sim_train"]

    # Near-duplicates inside the synthetic set (designed HN/ADV pairs reported separately) and inside NotInject.
    within = {}
    for component, part in data.groupby("component"):
        own = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True).fit_transform(part["text"])
        pairs, sims = near_duplicate_pairs(part["text"].tolist(), part["example_id"].tolist(), own)
        np.fill_diagonal(sims, 0)
        designed = {frozenset((a, b)) for a, b in part[["example_id", "pair_id"]].dropna().itertuples(index=False)}
        within[component] = {
            "near_duplicate_pairs": [p for p in pairs if frozenset((p["a"], p["b"])) not in designed],
            "designed_pairs_over_threshold": [p for p in pairs if frozenset((p["a"], p["b"])) in designed],
            "max_within_similarity_median": round(float(np.median(sims.max(axis=1))), 3)}

    out_data = ROOT / args.out_data
    out_data.mkdir(parents=True, exist_ok=True)
    data_path = out_data / "hard_negatives.parquet"
    data.to_parquet(data_path, index=False)

    synth_rows = data[data["component"] == "synthetic_v1"]
    validation = {
        "rows": int(len(data)),
        "by_component_label": {f"{c}|{l}": int(n) for (c, l), n in data.groupby(["component", "label"]).size().items()},
        "synthetic_by_category_label": {f"{c}|{l}": int(n) for (c, l), n in synth_rows.groupby(["category", "label"]).size().items()},
        "synthetic_structures": int(synth_rows["structure"].nunique()),
        "notinject_by_category": data.loc[data["component"] == "notinject", "category"].value_counts().to_dict(),
        "multilingual_rows": int(data["multilingual"].sum()),
        "strong_cue_share_by_component_label": {f"{c}|{l}": round(float(v), 3) for (c, l), v in
                                                data.groupby(["component", "label"])["has_strong_cue"].mean().items()},
        "exact_overlap_with_dataset_v2": data.loc[data["exact_overlap_split"].notna(), ["example_id", "exact_overlap_split"]].to_dict("records"),
        "rows_with_max_similarity_ge_0.8": {s: int((data[f"max_sim_{s}"] >= COSINE).sum()) for s in
                                            ["train", "validation", "test_official", "test_jailbreakhub"]},
        "closest_train_similarity_quantiles": {f"{c}|{l}": [round(float(q), 3) for q in g.quantile([0.1, 0.5, 0.9])] for (c, l), g in
                                               data.groupby(["component", "label"])["closest_train_similarity"]},
        "within_component": within,
        "text_length_chars_median": {c: int(g.str.len().median()) for c, g in data.groupby("component")["text"]},
    }
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(), "builder": "scripts/build_hard_negative_set.py",
        "categories": CATEGORIES, "random_seed": "none used (no sampling); dataset v2 seed 42 unchanged",
        "sources_sha256": {p.name: sha256(p) for p in sorted(SOURCE_DIR.glob("*.txt"))},
        "notinject_revision": NOTINJECT_REVISION,
        "notinject_sha256": {p.name: sha256(p) for p in sorted(NOTINJECT_DIR.glob("*.parquet"))},
        "dataset_v2_sha256": sha256(DATASET), "output": str(data_path.relative_to(ROOT)).replace("\\", "/"),
        "output_sha256": sha256(data_path),
    }
    out_results = ROOT / args.out_results
    out_results.mkdir(parents=True, exist_ok=True)
    (out_results / "build_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (out_results / "validation.json").write_text(json.dumps(validation, indent=2, default=str), encoding="utf-8")
    print(json.dumps(validation, indent=2, default=str))


if __name__ == "__main__":
    main()
