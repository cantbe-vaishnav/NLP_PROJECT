"""Binary jailbreak (source-adversarial) dataset: loading, cleaning, merging, splitting.

Label 1 = ADVERSARIAL (source marks the prompt as a jailbreak / adversarial attempt),
label 0 = BENIGN (non-jailbreak; not necessarily harmless). Labels come from each source's
own flag and are never edited here; see docs/task_a_binary_dataset.md. This module is
separate from the four-label pilot and does not use its schema.

Model input is always the original text. `comparison_key` is used only for matching.
"""
from collections import Counter, defaultdict
import hashlib
import json
import re

from task_a.leakage import comparison_key

LABEL_NAMES = {0: "BENIGN", 1: "ADVERSARIAL"}
WILDGUARD = "wildguardmix"
JAILBREAKHUB = "jailbreakhub"
OFFICIAL_TEST = "test_official"
_WORD = re.compile(r"\w")
_CUES = re.compile(
    r"\b(DAN|do anything now|jailbreak\w*|developer mode|ignore (all |the |any )?(previous|prior|above) "
    r"instructions|no (restrictions|filters|limits)|without (any )?(restrictions|censorship|filters)|"
    r"unfiltered|uncensored|bypass)\b", re.IGNORECASE)


def map_wildguard_label(value):
    """WildGuardMix `adversarial`: True -> 1, False -> 0. Anything else is an error."""
    if value is True:
        return 1
    if value is False:
        return 0
    raise ValueError(f"WildGuardMix adversarial flag must be boolean, got {value!r}")


def map_jailbreakhub_label(config, value):
    """JailbreakHub: `jailbreak_*` configs -> 1, `regular_*` -> 0.

    The row's own `jailbreak` column must agree with its configuration; a disagreement
    is a source inconsistency and raises rather than being silently resolved.
    """
    if config.startswith("jailbreak_"):
        expected, label = True, 1
    elif config.startswith("regular_"):
        expected, label = False, 0
    else:
        raise ValueError(f"Unknown JailbreakHub configuration {config!r}")
    if value is not expected:
        raise ValueError(f"{config}: row jailbreak={value!r} contradicts its configuration")
    return label


def is_valid_prompt(text):
    """A usable prompt is a string with at least one letter or digit."""
    return isinstance(text, str) and bool(_WORD.search(text))


def wildguard_records(rows, split):
    """Rows of one WildGuardMix Parquet split -> records. Row index is the source row ID."""
    out = []
    for i, row in enumerate(rows):
        out.append({
            "example_id": f"wildguard:{split}:{i}", "text": row["prompt"],
            "label": map_wildguard_label(row["adversarial"]), "source_dataset": WILDGUARD,
            "source_config": f"wildguard{split}", "source_split": split, "source_row": i,
            "source_label": f"adversarial={row['adversarial']}",
            "source_metadata": {"prompt_harm_label": row.get("prompt_harm_label"),
                                "subcategory": row.get("subcategory")}})
    return out


def jailbreakhub_records(rows, config):
    out = []
    for i, row in enumerate(rows):
        out.append({
            "example_id": f"jailbreakhub:{config}:{i}", "text": row["prompt"],
            "label": map_jailbreakhub_label(config, row["jailbreak"]),
            "source_dataset": JAILBREAKHUB, "source_config": config, "source_split": "train",
            "source_row": i, "source_label": f"config={config};jailbreak={row['jailbreak']}",
            "source_metadata": {k: row.get(k) for k in
                                ("platform", "source", "created_at", "community")}})
    return out


def drop_invalid(records):
    keep, excluded = [], []
    for r in records:
        if is_valid_prompt(r["text"]):
            keep.append(r)
        else:
            excluded.append({"example_id": r["example_id"], "reason": "invalid_or_empty_prompt",
                             "related_id": ""})
    return keep, excluded


def deduplicate(records):
    """Collapse exact and normalized duplicates; exclude groups whose labels conflict.

    Records are processed in the given order, so the first member of a group is its
    representative. Conflicting binary labels exclude the whole group (no label is
    chosen). For WildGuardMix rows, differing `prompt_harm_label` within a group sets
    `harm_label_conflict`; that does not affect the binary label.
    """
    groups = defaultdict(list)
    for r in records:
        groups[comparison_key(r["text"])].append(r)
    keep, excluded = [], []
    for members in groups.values():
        if len({m["label"] for m in members}) > 1:
            excluded += [{"example_id": m["example_id"], "reason": "label_conflict_duplicate",
                          "related_id": members[0]["example_id"]} for m in members]
            continue
        rep = dict(members[0])
        harms = {m["source_metadata"].get("prompt_harm_label") for m in members
                 if m["source_dataset"] == WILDGUARD}
        rep["harm_label_conflict"] = len(harms) > 1
        rep["duplicate_count"] = len(members)
        rep["duplicate_sources"] = sorted({m["source_config"] for m in members})
        keep.append(rep)
        for m in members[1:]:
            reason = "exact_duplicate" if m["text"] == rep["text"] else "normalized_duplicate"
            excluded.append({"example_id": m["example_id"], "reason": reason,
                             "related_id": rep["example_id"]})
    return keep, excluded


CORRECTION_ACTIONS = ("correct", "keep", "exclude")


def apply_label_corrections(records, corrections, source_text):
    """Apply a reviewed correction manifest to deduplicated records, by stable ID only.

    `corrections` rows need example_id, source_label, action (correct/keep/exclude),
    corrected_label and review fields; `source_text` maps example_id to the raw source
    prompt. Every manifest ID must be a retained JailbreakHub record whose text equals
    the raw source and whose binary label equals the manifest's source_label; anything
    else raises. "correct" flips the label, "keep" confirms it, "exclude" removes the
    record from the primary dataset (returned separately). The original source fields
    are never changed; `label` becomes the training target and `corrected_label` is set
    only for reviewed records.
    """
    by_id = {r["example_id"]: r for r in records}
    seen = set()
    for c in corrections:
        eid = c["example_id"]
        if eid in seen:
            raise ValueError(f"{eid}: duplicate correction")
        seen.add(eid)
        r = by_id.get(eid)
        if r is None:
            raise ValueError(f"{eid}: not a retained record")
        if r["source_dataset"] != JAILBREAKHUB:
            raise ValueError(f"{eid}: corrections apply to JailbreakHub only")
        if source_text.get(eid) != r["text"]:
            raise ValueError(f"{eid}: text does not match the raw source")
        if int(c["source_label"]) != r["label"]:
            raise ValueError(f"{eid}: manifest source_label {c['source_label']} != {r['label']}")
        if c["action"] not in CORRECTION_ACTIONS:
            raise ValueError(f"{eid}: unknown action {c['action']!r}")
        expected = {"correct": 1 - r["label"], "keep": r["label"], "exclude": None}[c["action"]]
        given = int(c["corrected_label"]) if str(c["corrected_label"]).strip() != "" else None
        if given != expected:
            raise ValueError(f"{eid}: corrected_label {given} inconsistent with action {c['action']}")
        r["review"] = c
    kept, excluded, changes = [], [], Counter()
    for r in records:
        c = r.pop("review", None)
        r["source_binary_label"] = r["label"]
        r.setdefault("corrected_label", None)
        for key in ("review_status", "review_reason", "reviewer_type", "review_artifact"):
            r[key] = c[key] if c else ""
        if c and c["action"] == "exclude":
            excluded.append(r)
            continue
        if c:
            r["corrected_label"] = int(c["corrected_label"])
            if r["corrected_label"] != r["label"]:
                changes[f"{r['label']}->{r['corrected_label']}"] += 1
            r["label"] = r["corrected_label"]
        kept.append(r)
    return kept, excluded, dict(changes)


def suspicious_reasons(record):
    """Programmatic flags for review; they never change or remove a label."""
    reasons = []
    text = record["text"].strip()
    if len(text) < 10:
        reasons.append("very_short_prompt")
    if record["source_dataset"] == JAILBREAKHUB:
        if record["label"] == 0 and _CUES.search(text):
            reasons.append("benign_label_with_jailbreak_cue")
        if record["label"] == 1 and len(text) < 50:
            reasons.append("adversarial_label_short_prompt")
    return reasons


def _shingles(text, words):
    tokens = comparison_key(text).split()
    if len(tokens) < words:
        return {tuple(tokens)}
    return {tuple(tokens[i:i + words]) for i in range(len(tokens) - words + 1)}


def near_duplicate_edges(texts, cosine_threshold=0.8, jaccard_threshold=0.85,
                         shingle_words=5, candidate_threshold=0.5, exhaustive_rows=()):
    """Index pairs (i < j) whose TF-IDF cosine or word-shingle Jaccard meets a threshold.

    Candidates come from rare-term TF-IDF vectors (terms in at most 1% of documents),
    plus a full-vector pass against every text for rows with no rare terms and for
    `exhaustive_rows` (the protected test rows), then every candidate is verified on
    full word 1-2-gram TF-IDF vectors. Lexical only: paraphrases are not detected.
    Returns (edges, full TF-IDF matrix) so callers can verify isolation.
    """
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer

    full = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True).fit_transform(texts)
    # "Rare" = in at most 1% of documents (at least 3, so tiny inputs still work).
    rare = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=2,
                           max_df=max(0.01, 3 / len(texts))).fit_transform(texts)
    candidates = set()
    rare_t = rare.T.tocsr()
    for start in range(0, rare.shape[0], 1000):
        block = (rare[start:start + 1000] @ rare_t).tocoo()
        mask = (block.data >= candidate_threshold) & (block.row + start < block.col)
        candidates.update(zip((block.row[mask] + start).tolist(), block.col[mask].tolist()))
    no_rare = np.where(np.asarray(rare.multiply(rare).sum(axis=1)).ravel() == 0)[0]
    no_rare = np.union1d(no_rare, np.asarray(exhaustive_rows, dtype=int))
    full_t = full.T.tocsr()
    for start in range(0, len(no_rare), 500):
        rows = no_rare[start:start + 500]
        block = (full[rows] @ full_t).tocoo()
        mask = (block.data >= candidate_threshold) & (rows[block.row] != block.col)
        for a, b in zip(rows[block.row[mask]].tolist(), block.col[mask].tolist()):
            candidates.add((min(a, b), max(a, b)))
    edges = []
    for a, b in sorted(candidates):
        cosine = float(full[a].multiply(full[b]).sum())
        jaccard = 0.0
        if cosine >= 0.5:
            sa, sb = _shingles(texts[a], shingle_words), _shingles(texts[b], shingle_words)
            jaccard = len(sa & sb) / len(sa | sb)
        if cosine >= cosine_threshold or jaccard >= jaccard_threshold:
            edges.append((a, b, cosine, jaccard))
    return edges, full


def families(n, edges):
    """Connected components over edges -> list of family IDs, stable by first member."""
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b, *_ in edges:
        parent[find(a)] = find(b)
    names, out = {}, []
    for i in range(n):
        root = find(i)
        names.setdefault(root, f"fam{len(names):06d}")
        out.append(names[root])
    return out


def assign_splits(records, targets, seed=42):
    """Assign whole families to splits; the official test split is never reassigned.

    `targets` maps a stratum source ("wildguardmix" or "jailbreakhub") to
    {split: fraction}; the remainder goes to "train". A family's stratum is
    (jailbreakhub if it has any JailbreakHub member else wildguardmix, majority label).
    Families are visited in a seeded-hash order and placed in a non-train split only if
    they fit its remaining quota, so no family is ever divided.
    """
    fams = defaultdict(list)
    for r in records:
        if r["split"] != OFFICIAL_TEST:
            fams[r["family_id"]].append(r)
    strata = defaultdict(list)
    for fid, members in fams.items():
        source = JAILBREAKHUB if any(m["source_dataset"] == JAILBREAKHUB for m in members) \
            else WILDGUARD
        label = Counter(m["label"] for m in members).most_common(1)[0][0]
        strata[(source, label)].append(fid)
    for (source, _), fids in sorted(strata.items()):
        total = sum(len(fams[f]) for f in fids)
        quota = {s: round(frac * total) for s, frac in targets[source].items()}
        used = Counter()
        order = sorted(fids, key=lambda f: hashlib.sha256(f"{seed}:{f}".encode()).hexdigest())
        for fid in order:
            size = len(fams[fid])
            fits = [s for s in quota if used[s] + size <= quota[s]]
            split = max(fits, key=lambda s: (quota[s] - used[s], s)) if fits else "train"
            if split != "train":
                used[split] += size
            for m in fams[fid]:
                m["split"] = split
    return records


def split_manifest(records):
    """ID-only manifest {split: [example_id, ...]}: no text and no labels."""
    out = defaultdict(list)
    for r in records:
        out[r["split"]].append(r["example_id"])
    return {s: sorted(ids) for s, ids in sorted(out.items())}


def to_row(record):
    """Flatten a record for Parquet output (metadata and lists as JSON strings)."""
    row = dict(record)
    row["label_name"] = LABEL_NAMES[row["label"]]
    for key in ("source_metadata", "duplicate_sources", "suspicious_reasons"):
        row[key] = json.dumps(row.get(key, []), ensure_ascii=False, default=str)
    return row
