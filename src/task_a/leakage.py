"""Conservative source audit helpers; no model text or labels are changed."""
from collections import defaultdict
import unicodedata


def comparison_key(text):
    """Only for duplicate detection. Never use this as model input."""
    return " ".join(unicodedata.normalize("NFC", text).casefold().split())


def duplicate_summary(records, normalized=False):
    groups = defaultdict(list)
    for record in records:
        text = record["prompt"]
        if not isinstance(text, str) or not text.strip():
            continue
        groups[comparison_key(text) if normalized else text].append(record)
    cross = [group for group in groups.values()
             if len({r["split"] for r in group}) > 1]
    conflict = [group for group in groups.values()
                if len({r["adversarial"] for r in group}) > 1]
    return {
        "unique_nonempty_prompts": len(groups),
        "duplicate_excess": sum(len(g) - 1 for g in groups.values()),
        "duplicate_groups": sum(len(g) > 1 for g in groups.values()),
        "cross_official_split_groups": len(cross),
        "cross_official_split_rows": sum(map(len, cross)),
        "conflicting_adversarial_groups": len(conflict),
        "conflicting_adversarial_rows": sum(map(len, conflict)),
        "conflict_ids": [[r["id"] for r in g] for g in conflict],
        "cross_split_ids": [[r["id"] for r in g] for g in cross],
    }


def adjacent_near_duplicates(records, words=5, threshold=0.85):
    """Compare adjacent unique normalized texts: bounded diagnostic, low recall.

    Not an exhaustive search and never sufficient to certify leakage absence.
    Return row IDs only; preserve the originals in their source artifact.
    """
    if words < 1 or not 0 < threshold <= 1:
        raise ValueError("Invalid shingle size or threshold")
    unique = {}
    for r in records:
        if isinstance(r["prompt"], str) and r["prompt"].strip():
            key = comparison_key(r["prompt"])
            unique.setdefault(key, r)
    keys = sorted(unique)

    def shingles(key):
        tokens = key.split()
        return {tuple(tokens[i:i + words]) for i in range(len(tokens) - words + 1)}

    previous = None
    for key in keys:
        current = shingles(key)
        if previous is not None:
            prev_key, prev = previous
            if prev and current:
                score = len(prev & current) / len(prev | current)
                if score >= threshold:
                    a, b = unique[prev_key], unique[key]
                    yield {"left_id": a["id"], "right_id": b["id"],
                           "jaccard": score, "cross_official_split": a["split"] != b["split"]}
        previous = key, current
