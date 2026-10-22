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


def embedding_similarities(model, records: list[ClaimEvidence], batch_size: int = 64) -> list[float]:
    """Largest claim-evidence cosine per record, encoding all texts once in batches."""
    claims = model.encode([record.claim for record in records], batch_size=batch_size,
                          normalize_embeddings=True)
    evidence_texts = [item.text for record in records for item in record.evidence]
    evidence = model.encode(evidence_texts, batch_size=batch_size, normalize_embeddings=True)
    scores, start = [], 0
    for claim, record in zip(claims, records):
        end = start + len(record.evidence)
        scores.append(max(float(claim @ vector) for vector in evidence[start:end]))
        start = end
    return scores


def nli_label_ids(config) -> dict[str, int]:
    """Read model labels by name; never rely on classifier head order."""
    names = {str(name).lower(): int(index) for index, name in config.id2label.items()}
    required = ("entailment", "contradiction", "neutral")
    if any(name not in names for name in required):
        raise ValueError(f"NLI model must expose {required} in id2label")
    return {name: names[name] for name in required}


NLI_TO_TASK_B = {"entailment": "SUPPORTED", "contradiction": "CONTRADICTED", "neutral": "UNSUPPORTED"}


def joined_premise(record: ClaimEvidence) -> str:
    """All evidence sentences in their stored order, joined by a space: the fine-tuning premise."""
    return " ".join(item.text for item in record.evidence)


def nli_scores_to_label(scores: list[float], ids: dict[str, int]) -> str:
    """Highest of the three NLI classes as a Task B label; neutral means UNSUPPORTED."""
    return NLI_TO_TASK_B[max(ids, key=lambda name: scores[ids[name]])]


def nli_joined_predictions(tokenizer, model, torch_module, records: list[ClaimEvidence],
                           max_length: int = 256, batch_size: int = 64) -> tuple[list[str], list[list[float]]]:
    """One (joined evidence, claim) pair per claim, batched. A different protocol from nli_predictor.

    Only the evidence is truncated, so the claim is always seen whole. Returns labels and class probabilities.
    """
    ids = nli_label_ids(model.config)
    model.eval()
    labels, probabilities = [], []
    for start in range(0, len(records), batch_size):
        batch = records[start:start + batch_size]
        pairs = tokenizer([joined_premise(record) for record in batch], [record.claim for record in batch],
                          return_tensors="pt", padding=True, truncation="only_first",
                          max_length=max_length).to(model.device)
        with torch_module.no_grad():
            scores = model(**pairs).logits.float().softmax(dim=-1).tolist()
        labels += [nli_scores_to_label(row, ids) for row in scores]
        probabilities += scores
    return labels, probabilities


def nli_predictor(tokenizer, model, torch_module):
    """Highest sentence-level non-neutral score wins; neutral if neither wins.

    This is a project-specific aggregation rule, not a published method.
    """
    ids = nli_label_ids(model.config)
    model.eval()

    def predict(record: ClaimEvidence) -> str:
        # Premise = evidence sentence, hypothesis = claim; inputs go to the model's device (CPU or GPU).
        pairs = tokenizer([item.text for item in record.evidence],
                          [record.claim] * len(record.evidence),
                          return_tensors="pt", padding=True, truncation=True).to(model.device)
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
