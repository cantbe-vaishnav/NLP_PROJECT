"""Descriptive source-sample statistics, never SafeLLM label assignment."""

from collections import Counter
import hashlib
import json


def summarize_sample(rows):
    """Report actual fetched rows without generalizing to the parent dataset."""
    labels = Counter()
    texts = []
    malformed = 0
    empty = 0
    for entry in rows:
        row = entry.get("row") if isinstance(entry, dict) else None
        if not isinstance(row, dict) or not isinstance(row.get("text"), str):
            malformed += 1
            continue
        text = row["text"]
        if not text.strip():
            empty += 1
        texts.append(text)
        labels[json.dumps(row.get("label"), sort_keys=True)] += 1
    return {
        "scope": "fetched preview only; not a representative population estimate",
        "rows_fetched": len(rows),
        "malformed_text_rows": malformed,
        "empty_text_rows": empty,
        "source_label_distribution": dict(sorted(labels.items())),
        "exact_duplicate_excess": len(texts) - len(set(texts)),
        "min_characters": min(map(len, texts), default=None),
        "max_characters": max(map(len, texts), default=None),
        "rows_sha256": hashlib.sha256(
            json.dumps(rows, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest(),
        "safellm_labels_assigned": False,
    }
