"""Build the WildGuardMix + JailbreakHub binary jailbreak dataset and its audit.

Reads only the raw files named in the config (verifying their SHA-256), never modifies
them, and refuses to overwrite previous outputs. The official WildGuardMix test split is
copied unchanged; nothing from it or its near-duplicate families enters train/validation.
Text, labels and per-row files go to the Git-ignored output directory; the audit report
contains counts and IDs only.
"""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from task_a.binary_dataset import (
    JAILBREAKHUB, OFFICIAL_TEST, WILDGUARD, apply_label_corrections, assign_splits, deduplicate, drop_invalid,
    families, jailbreakhub_records, near_duplicate_edges, split_manifest, suspicious_reasons,
    to_row, wildguard_records)
from task_a.leakage import comparison_key

EXAMPLES_PER_FLAG = 20


def sha256(path):
    with open(path, "rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def write_parquet(path, records):
    pq.write_table(pa.Table.from_pylist([to_row(r) for r in records]), path)


def write_csv(path, fields, rows):
    with open(path, "x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def counts(records):
    out = defaultdict(Counter)
    for r in records:
        out[f"{r['source_dataset']}/{r['source_config']}"][r["label"]] += 1
    return {k: {"BENIGN": v[0], "ADVERSARIAL": v[1], "total": v[0] + v[1]} for k, v in sorted(out.items())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/task_a_binary_dataset.json")
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    out = Path(config["output_dir"])
    for path in [out, Path(config["audit_json"]), Path(config["audit_markdown"])]:
        if path.exists():
            raise FileExistsError(f"{path} exists; refusing to overwrite")

    raw, hashes = {}, {}
    for name, spec in config["sources"].items():
        digest = sha256(spec["path"])
        if digest != spec["sha256"]:
            raise ValueError(f"{name}: SHA-256 {digest} does not match config {spec['sha256']}")
        hashes[name] = digest
        raw[name] = pq.read_table(spec["path"]).to_pylist()

    test = wildguard_records(raw["wildguard_test"], "test")
    pool_all = wildguard_records(raw["wildguard_train"], "train")
    jbh_all = (jailbreakhub_records(raw["jailbreak_2023_12_25"], "jailbreak_2023_12_25")
               + jailbreakhub_records(raw["regular_2023_12_25"], "regular_2023_12_25"))
    original = counts(test + pool_all + jbh_all)
    if not all(r["text"] and r["text"].strip() for r in test):
        raise ValueError("Official test contains invalid prompts; stop and review")

    # Cleaned JailbreakHub on its own (internal invalid/duplicate/conflict handling only).
    jbh_valid, jbh_invalid = drop_invalid(jbh_all)
    jbh_clean, jbh_dup = deduplicate(jbh_valid)
    for r in jbh_clean:
        r["suspicious_reasons"] = suspicious_reasons(r)

    # Combined training pool: WildGuardMix train first, so its copy represents cross-source duplicates.
    pool_valid, excluded = drop_invalid(pool_all + jbh_all)
    test_keys = {comparison_key(r["text"]) for r in test}
    test_texts = {r["text"] for r in test}
    remaining = []
    for r in pool_valid:
        if comparison_key(r["text"]) in test_keys:
            reason = "test_overlap_exact" if r["text"] in test_texts else "test_overlap_normalized"
            excluded.append({"example_id": r["example_id"], "reason": reason, "related_id": ""})
        else:
            remaining.append(r)
    pool, dup_excluded = deduplicate(remaining)
    excluded += dup_excluded

    # Optional reviewed label corrections (by stable ID, verified against the raw source).
    corrections_info, ambiguous = None, []
    if config.get("label_corrections"):
        spec = config["label_corrections"]
        digest = sha256(spec["manifest"])
        if digest != spec["sha256"]:
            raise ValueError(f"Correction manifest SHA-256 {digest} != config {spec['sha256']}")
        with open(spec["manifest"], encoding="utf-8") as handle:
            manifest = list(csv.DictReader(handle))
        raw_text = {r["example_id"]: r["text"] for r in jbh_all}
        pool, ambiguous, changes = apply_label_corrections(pool, manifest, raw_text)
        excluded += [{"example_id": r["example_id"], "reason": "review_ambiguous_excluded",
                      "related_id": ""} for r in ambiguous]
        corrections_info = {"manifest": spec["manifest"], "sha256": digest,
                            "reviewer_type": "full-text review (not human-verified)",
                            "actions": dict(Counter(c["action"] for c in manifest)),
                            "label_changes": changes, "ambiguous_excluded": len(ambiguous),
                            "ambiguous_ids": sorted(r["example_id"] for r in ambiguous)}
        for r in test:
            r["source_binary_label"], r["corrected_label"] = r["label"], None
            for key in ("review_status", "review_reason", "reviewer_type", "review_artifact"):
                r[key] = ""

    nd = config["near_duplicate"]
    every = pool + test
    edges, matrix = near_duplicate_edges(
        [r["text"] for r in every], nd["cosine_threshold"], nd["jaccard_threshold"],
        nd["shingle_words"], nd["candidate_threshold"],
        exhaustive_rows=range(len(pool), len(every)))
    fam_ids = families(len(every), edges)
    for r, fid in zip(every, fam_ids):
        r["family_id"] = fid
    for r in test:
        r["split"] = OFFICIAL_TEST
        r.setdefault("duplicate_count", 1)
        r.setdefault("duplicate_sources", [r["source_config"]])
        r.setdefault("harm_label_conflict", False)
    test_family = {r["family_id"]: r["example_id"] for r in test}
    retained = []
    for r in pool:
        if r["family_id"] in test_family:
            excluded.append({"example_id": r["example_id"], "reason": "test_overlap_near_duplicate",
                             "related_id": test_family[r["family_id"]]})
        else:
            r["split"] = None
            retained.append(r)

    members = defaultdict(list)
    for r in retained + test:
        members[r["family_id"]].append(r)
    for r in retained + test:
        fam = members[r["family_id"]]
        r["family_size"] = len(fam)
        r["family_label_mixed"] = len({m["label"] for m in fam}) > 1
        r["suspicious_reasons"] = suspicious_reasons(r) + (
            ["mixed_label_near_duplicate_family"] if r["family_label_mixed"] else [])
    assign_splits(retained, config["split_targets"], config["seed"])
    combined = retained + test

    # Verification (raises on failure; residual similarity is reported).
    raw_test = raw["wildguard_test"]
    assert len(test) == len(raw_test) and all(
        r["text"] == row["prompt"] and r["label"] == int(row["adversarial"])
        for r, row in zip(test, raw_test)), "official test changed"
    split_of_family = defaultdict(set)
    for r in combined:
        split_of_family[r["family_id"]].add(r["split"])
    crossing = [f for f, s in split_of_family.items() if len(s) > 1]
    assert not crossing, f"{len(crossing)} families span splits"
    train_keys = {comparison_key(r["text"]) for r in retained}
    assert not train_keys & test_keys, "normalized overlap between official test and train/validation"
    index = {r["example_id"]: i for i, r in enumerate(every)}
    train_rows = np.array([index[r["example_id"]] for r in combined if r["split"] == "train"])
    residual = {}
    for split in ["validation", "test_jailbreakhub", OFFICIAL_TEST]:
        rows = np.array([index[r["example_id"]] for r in combined if r["split"] == split])
        best = np.zeros(len(rows))
        for start in range(0, len(rows), 500):
            block = matrix[rows[start:start + 500]] @ matrix[train_rows].T
            best[start:start + 500] = np.asarray(block.max(axis=1).todense()).ravel()
        residual[split] = {"rows": int(len(rows)), "max_cosine_to_train": float(best.max()),
                           **{f"rows_cosine_ge_{t}": int((best >= t).sum()) for t in (0.9, 0.8, 0.7, 0.5)}}
    assert residual[OFFICIAL_TEST]["rows_cosine_ge_0.8"] == 0, "official test row near-duplicates train"

    # Overlap of JailbreakHub with WildGuardMix (before any exclusion), by level.
    keys = {name: {comparison_key(r["text"]) for r in rs if isinstance(r["text"], str)}
            for name, rs in [("wg_train", pool_all), ("wg_test", test)]}
    texts = {name: {r["text"] for r in rs} for name, rs in [("wg_train", pool_all), ("wg_test", test)]}
    family_sources = defaultdict(set)
    for r in every:
        family_sources[r["family_id"]].add(f"{r['source_dataset']}:{r['source_split']}")
    overlap = {}
    for config_name in ["jailbreak_2023_12_25", "regular_2023_12_25"]:
        rows = [r for r in jbh_all if r["source_config"] == config_name and isinstance(r["text"], str)]
        in_pool = [r for r in pool if r["source_config"] == config_name]
        overlap[config_name] = {
            "exact_in_wildguard_train": sum(r["text"] in texts["wg_train"] for r in rows),
            "normalized_in_wildguard_train": sum(comparison_key(r["text"]) in keys["wg_train"] for r in rows),
            "exact_in_wildguard_test": sum(r["text"] in texts["wg_test"] for r in rows),
            "normalized_in_wildguard_test": sum(comparison_key(r["text"]) in keys["wg_test"] for r in rows),
            "near_duplicate_family_with_wildguard_train": sum(
                f"{WILDGUARD}:train" in family_sources[r["family_id"]] for r in in_pool),
            "near_duplicate_family_with_wildguard_test": sum(
                f"{WILDGUARD}:test" in family_sources[r["family_id"]] for r in in_pool)}

    fam_sizes = Counter(r["family_id"] for r in retained)
    largest = []
    for fid, size in fam_sizes.most_common(10):
        fam = members[fid]
        largest.append({"family_id": fid, "size": size, "split": fam[0]["split"],
                        "sources": dict(Counter(m["source_config"] for m in fam)),
                        "labels": dict(Counter(m["label"] for m in fam))})
    flags = defaultdict(list)
    for r in combined:
        for reason in r["suspicious_reasons"]:
            flags[reason].append(r["example_id"])
    final = defaultdict(lambda: defaultdict(Counter))
    for r in combined:
        final[r["split"]][r["source_dataset"]][r["label"]] += 1
    import sklearn
    audit = {
        "created_utc": datetime.now(timezone.utc).isoformat(), "config": config,
        "versions": {"python": platform.python_version(), "pyarrow": pa.__version__,
                     "numpy": np.__version__, "scikit_learn": sklearn.__version__},
        "input_sha256": hashes,
        "original_counts": original,
        "jailbreakhub_clean": {"invalid": len(jbh_invalid),
                               "excluded_by_reason": dict(Counter(e["reason"] for e in jbh_dup)),
                               "retained": counts(jbh_clean)},
        "combined_exclusions_by_reason": {
            reason: dict(Counter(e["example_id"].split(":")[0] + ":" + e["example_id"].split(":")[1]
                                 for e in excluded if e["reason"] == reason))
            for reason in sorted({e["reason"] for e in excluded})},
        "harm_label_conflict_groups_retained": sum(r["harm_label_conflict"] for r in retained),
        "jailbreakhub_overlap_with_wildguardmix": overlap,
        "near_duplicates": {
            "edges": len(edges), "families_retained": len(fam_sizes),
            "multi_member_families": sum(s > 1 for s in fam_sizes.values()),
            "rows_in_multi_member_families": sum(s for s in fam_sizes.values() if s > 1),
            "mixed_label_families": len({r["family_id"] for r in retained if r["family_label_mixed"]}),
            "largest_families": largest},
        "suspicious_flags": {k: {"count": len(v), "example_ids": v[:EXAMPLES_PER_FLAG]}
                             for k, v in sorted(flags.items())},
        "final_counts": {s: {src: {"BENIGN": c[0], "ADVERSARIAL": c[1], "total": c[0] + c[1]}
                             for src, c in sorted(v.items())} for s, v in sorted(final.items())},
        "leakage_checks": {"official_test_unchanged": True, "families_spanning_splits": 0,
                           "normalized_overlap_official_test_vs_train_validation": 0,
                           "residual_similarity_to_train": residual,
                           "limitations": "Lexical checks only (TF-IDF word 1-2-gram cosine and "
                                          "5-word-shingle Jaccard); paraphrases, translations and "
                                          "shared parent prompts are not detectable."},
    }
    if corrections_info:
        reviewed = [r for r in combined if r["review_status"]]
        corrections_info["reviewed_rows_by_split_and_final_label"] = {
            s: dict(Counter(r["label"] for r in reviewed if r["split"] == s))
            for s in sorted({r["split"] for r in reviewed})}
        corrections_info["changed_rows_by_split"] = dict(Counter(
            r["split"] for r in reviewed if r["corrected_label"] != r["source_binary_label"]))
        assert all(r["source_dataset"] == JAILBREAKHUB for r in reviewed)
        assert not any(r["review_status"] for r in test), "corrections touched the official test"
        audit["label_corrections"] = corrections_info

    out.mkdir(parents=True)
    if corrections_info:
        write_parquet(out / "ambiguous_review_holdout.parquet", ambiguous)
    write_parquet(out / "combined.parquet", combined)
    write_parquet(out / "jailbreakhub_clean.parquet", jbh_clean)
    write_csv(out / "exclusions.csv", ["example_id", "reason", "related_id"], excluded)
    write_csv(out / "families.csv", ["example_id", "family_id", "split"], combined)
    write_csv(out / "near_duplicate_edges.csv", ["a", "b", "cosine", "jaccard"],
              [{"a": every[a]["example_id"], "b": every[b]["example_id"], "cosine": round(c, 4),
                "jaccard": round(j, 4)} for a, b, c, j in edges])
    (out / "split_manifest.json").write_text(json.dumps(split_manifest(combined), indent=1) + "\n",
                                             encoding="utf-8")
    Path(config["audit_json"]).write_text(json.dumps(audit, indent=2, default=str) + "\n",
                                          encoding="utf-8")
    Path(config["audit_markdown"]).write_text(render(audit), encoding="utf-8")
    print(render(audit))


def render(audit):
    lines = ["# Binary jailbreak dataset audit (WildGuardMix + JailbreakHub)", "",
             "Generated by `scripts/build_binary_dataset.py`. Counts and IDs only; no prompt text.",
             "Labels are each source's own flag (1 = ADVERSARIAL, 0 = BENIGN = non-jailbreak, "
             "not necessarily harmless). No label was edited.", "",
             "## Original rows", "", "| Source | BENIGN | ADVERSARIAL | Total |", "|---|---|---|---|"]
    for src, c in audit["original_counts"].items():
        lines.append(f"| {src} | {c['BENIGN']} | {c['ADVERSARIAL']} | {c['total']} |")
    lines += ["", "## Exclusions from the training pool (by reason and source)", ""]
    for reason, by in audit["combined_exclusions_by_reason"].items():
        lines.append(f"- {reason}: " + ", ".join(f"{k} {v}" for k, v in sorted(by.items())))
    lines += ["", f"WildGuardMix duplicate groups with conflicting `prompt_harm_label` retained "
              f"(flagged `harm_label_conflict`): {audit['harm_label_conflict_groups_retained']}.", "",
              "## JailbreakHub overlap with WildGuardMix (before exclusion)", "",
              "| Config | exact train | normalized train | exact test | normalized test | "
              "near-dup family with train | near-dup family with test |", "|---|---|---|---|---|---|---|"]
    for cfg, o in audit["jailbreakhub_overlap_with_wildguardmix"].items():
        lines.append(f"| {cfg} | {o['exact_in_wildguard_train']} | {o['normalized_in_wildguard_train']} | "
                     f"{o['exact_in_wildguard_test']} | {o['normalized_in_wildguard_test']} | "
                     f"{o['near_duplicate_family_with_wildguard_train']} | "
                     f"{o['near_duplicate_family_with_wildguard_test']} |")
    nd = audit["near_duplicates"]
    lines += ["", "## Near-duplicate families (retained pool)", "",
              f"Edges {nd['edges']}; families {nd['families_retained']}; multi-member "
              f"{nd['multi_member_families']} covering {nd['rows_in_multi_member_families']} rows; "
              f"mixed-label families {nd['mixed_label_families']}.", "",
              "| Family | Size | Split | Sources | Labels |", "|---|---|---|---|---|"]
    for f in nd["largest_families"]:
        lines.append(f"| {f['family_id']} | {f['size']} | {f['split']} | {f['sources']} | {f['labels']} |")
    lines += ["", "## Suspicious-label flags (kept, not relabelled)", ""]
    for k, v in audit["suspicious_flags"].items():
        lines.append(f"- {k}: {v['count']}")
    lines += ["", "## Final splits", "", "| Split | Source | BENIGN | ADVERSARIAL | Total |",
              "|---|---|---|---|---|"]
    for split, by in audit["final_counts"].items():
        for src, c in by.items():
            lines.append(f"| {split} | {src} | {c['BENIGN']} | {c['ADVERSARIAL']} | {c['total']} |")
    lcorr = audit.get("label_corrections")
    if lcorr:
        lines += ["", "## Reviewed label corrections", "",
                  f"Manifest `{lcorr['manifest']}` (SHA-256 `{lcorr['sha256']}`), "
                  f"{lcorr['reviewer_type']}. Actions: {lcorr['actions']}. Label changes: "
                  f"{lcorr['label_changes']}. Ambiguous rows excluded and held out: "
                  f"{lcorr['ambiguous_excluded']}. Changed rows by split: {lcorr['changed_rows_by_split']}. "
                  "Source labels are preserved in `source_binary_label`/`source_label`; `label` is the "
                  "training target and `corrected_label` is set only for reviewed rows."]
    lc = audit["leakage_checks"]
    lines += ["", "## Leakage checks", "",
              "- Official WildGuardMix test copied unchanged (row-by-row text and label check): passed.",
              "- No near-duplicate family spans two splits: passed.",
              "- No normalized prompt shared by the official test and train/validation: passed.",
              "", "| Split | Rows | Max cosine to train | >= 0.9 | >= 0.8 | >= 0.7 | >= 0.5 |",
              "|---|---|---|---|---|---|---|"]
    for split, r in lc["residual_similarity_to_train"].items():
        lines.append(f"| {split} | {r['rows']} | {r['max_cosine_to_train']:.3f} | {r['rows_cosine_ge_0.9']} | "
                     f"{r['rows_cosine_ge_0.8']} | {r['rows_cosine_ge_0.7']} | {r['rows_cosine_ge_0.5']} |")
    lines += ["", f"Limitation: {lc['limitations']}", "", "## Provenance", ""]
    for name, digest in audit["input_sha256"].items():
        lines.append(f"- {name}: `{digest}`")
    for name, p in audit["config"]["provenance"].items():
        lines.append(f"- {name}: {p['repo']} @ `{p['revision']}`, license {p['license']}")
    lines.append(f"- Versions: {audit['versions']}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
