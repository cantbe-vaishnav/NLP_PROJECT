"""Optional pretrained approaches. Importing this module does not download weights."""

from __future__ import annotations

import hashlib
from pathlib import Path

from .schema import ClaimEvidence


def model_fingerprint(path: str | Path) -> str:
    """Hash a complete local model snapshot for an exact run manifest."""
    root = Path(path)
    if not root.is_dir():
        raise FileNotFoundError(root)
    digest = hashlib.sha256()
    files = sorted(file for file in root.rglob("*") if file.is_file() and ".git" not in file.parts)
    if not files:
        raise ValueError("model directory is empty")
    for file in files:
        digest.update(str(file.relative_to(root)).encode("utf-8"))
        with file.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def embedding_predictor(model, threshold: float = 0.5):
    """Cosine similarity yields SUPPORTED/UNSUPPORTED only."""
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be between 0 and 1")

    def predict(record: ClaimEvidence) -> str:
        embeddings = model.encode([record.claim] + [item.text for item in record.evidence],
                                  normalize_embeddings=True)
        claim = embeddings[0]
        similarities = [float(claim @ evidence) for evidence in embeddings[1:]]
        return "SUPPORTED" if max(similarities) >= threshold else "UNSUPPORTED"

    return predict


def nli_label_ids(config) -> dict[str, int]:
    """Read model labels by name; never rely on classifier head order."""
    names = {str(name).lower(): int(index) for index, name in config.id2label.items()}
    required = ("entailment", "contradiction", "neutral")
    if any(name not in names for name in required):
        raise ValueError(f"NLI model must expose {required} in id2label")
    return {name: names[name] for name in required}


def nli_predictor(tokenizer, model, torch_module):
    """Highest sentence-level non-neutral score wins; neutral if neither wins.

    This is a project-specific aggregation rule, not a published method.
    """
    ids = nli_label_ids(model.config)
    model.eval()

    def predict(record: ClaimEvidence) -> str:
        pairs = tokenizer([item.text for item in record.evidence],
                          [record.claim] * len(record.evidence),
                          return_tensors="pt", padding=True, truncation=True)
        with torch_module.no_grad():
            scores = model(**pairs).logits.softmax(dim=-1).tolist()
        best_label, best_score = "UNSUPPORTED", -1.0
        for sentence in scores:
            label = max(ids, key=lambda name: sentence[ids[name]])
            score = sentence[ids[label]]
            if label != "neutral" and score > best_score:
                best_label = {"entailment": "SUPPORTED", "contradiction": "CONTRADICTED"}[label]
                best_score = score
        return best_label

    return predict
