"""TF-IDF + Logistic Regression harness for Task A. Engineering smoke test only.

Everything except `fit_predict_tfidf_logreg` is standard-library code so it can be
tested without scikit-learn. The four-label schema is canonical; labels absent from the
data are reported as absent, never invented. See docs/task_a_semantic_pilot_guidelines.md.
"""
from collections import Counter, defaultdict
import hashlib
import itertools

from task_a.leakage import comparison_key
from task_a.semantic_pilot import LABELS

SMOKE_BANNER = ("SMOKE TEST ONLY: pipeline validation on a tiny, unadjudicated pilot subset. "
                "Not a research result; no held-out test set; no claim of generalization.")


def validate_label(label):
    """Return the label unchanged if it is canonical; never normalize or guess."""
    if label not in LABELS:
        raise ValueError(f"Invalid Task A label {label!r}; allowed: {', '.join(LABELS)}")
    return label


def unanimous_records(master, reviews, exclude_ids=()):
    """Items on which all reviewers gave the same label, minus explicit exclusions.

    2-vs-1 and three-way items are dropped, never resolved by vote. The master prompt is
    the model input, and it must equal the reviewer-file prompt unless the ID is excluded.
    """
    exclude = set(exclude_ids)
    by_id = {row["pilot_id"]: row for row in master}
    unknown = exclude - set(by_id)
    if unknown:
        raise ValueError(f"Excluded IDs not in master: {sorted(unknown)}")
    reviewers = list(reviews)
    first = reviews[reviewers[0]]
    records = []
    for i, row in enumerate(first):
        pid = row["pilot_id"]
        labels = [validate_label(reviews[r][i]["label"]) for r in reviewers]
        if any(reviews[r][i]["pilot_id"] != pid for r in reviewers):
            raise ValueError(f"Reviewer ID order mismatch at {pid}")
        if len(set(labels)) != 1 or pid in exclude:
            continue
        if pid not in by_id or by_id[pid]["prompt"] != row["prompt"]:
            raise ValueError(f"{pid}: reviewer prompt differs from master and ID is not excluded")
        records.append({"id": pid, "prompt": by_id[pid]["prompt"], "label": labels[0]})
    return records


def _shingles(text, n=3):
    tokens = comparison_key(text).split()
    if len(tokens) < n:
        return {tuple(tokens)}
    return {tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)}


def duplicate_groups(records, threshold=0.5, shingle_words=3):
    """Group IDs whose normalized text matches or whose word-shingle Jaccard >= threshold.

    Connected components, so a chain of near-duplicates shares one group (and one fold).
    Returns {id: group_id}. Group IDs are stable: g000, g001, ... by first member order.
    """
    if not 0 < threshold <= 1:
        raise ValueError("threshold must be in (0, 1]")
    parent = list(range(len(records)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    sets = [_shingles(r["prompt"], shingle_words) for r in records]
    keys = [comparison_key(r["prompt"]) for r in records]
    for a, b in itertools.combinations(range(len(records)), 2):
        same = keys[a] == keys[b]
        if not same:
            union = len(sets[a] | sets[b])
            same = union > 0 and len(sets[a] & sets[b]) / union >= threshold
        if same:
            parent[find(a)] = find(b)
    roots, out = {}, {}
    for i, rec in enumerate(records):
        root = find(i)
        roots.setdefault(root, f"g{len(roots):03d}")
        out[rec["id"]] = roots[root]
    return out


def grouped_stratified_folds(records, groups, k=5, seed=42):
    """Deterministic fold assignment {id: fold}. A group is never split across folds.

    Groups are ordered by (stratification label, seeded hash) and each goes to the fold
    holding the fewest items of that label, then the fewest items overall. Not a held-out
    test: every item is used for evaluation exactly once, out of fold.
    """
    if k < 2:
        raise ValueError("k must be at least 2")
    members = defaultdict(list)
    for rec in records:
        members[groups[rec["id"]]].append(rec)
    if len(members) < k:
        raise ValueError(f"Only {len(members)} groups for {k} folds")
    labelled = []
    for gid, recs in members.items():
        strat = Counter(r["label"] for r in recs).most_common()
        strat = sorted(strat, key=lambda x: (-x[1], x[0]))[0][0]
        tie = hashlib.sha256(f"{seed}:{gid}".encode()).hexdigest()
        labelled.append((strat, tie, gid))
    labelled.sort()
    per_label = [Counter() for _ in range(k)]
    sizes = [0] * k
    assignment = {}
    for strat, _, gid in labelled:
        fold = min(range(k), key=lambda f: (per_label[f][strat], sizes[f], f))
        for rec in members[gid]:
            assignment[rec["id"]] = fold
            per_label[fold][rec["label"]] += 1
            sizes[fold] += 1
    return assignment


def split_manifest(assignment, groups, k):
    """ID-only manifest: no prompt text and no labels."""
    folds = {str(f): sorted(i for i, fold in assignment.items() if fold == f) for f in range(k)}
    return {"k": k, "folds": folds, "group_of": {i: groups[i] for i in sorted(assignment)}}


def per_class_metrics(gold, pred, labels=LABELS):
    """Per-class precision/recall/F1, macro-F1 and a labelled confusion matrix.

    Classes with zero gold support are reported as absent (null metrics) and excluded
    from macro-F1; `macro_f1_classes` lists exactly which classes were averaged.
    Predicting a label with zero support yields precision 0.0 (a false positive).
    Rows of the confusion matrix are gold labels, columns are predictions.
    """
    if len(gold) != len(pred):
        raise ValueError("gold and pred lengths differ")
    for value in itertools.chain(gold, pred):
        validate_label(value)
    matrix = {g: {p: 0 for p in labels} for g in labels}
    for g, p in zip(gold, pred):
        matrix[g][p] += 1
    classes, f1s = {}, []
    for label in labels:
        tp = matrix[label][label]
        support = sum(matrix[label].values())
        predicted = sum(matrix[g][label] for g in labels)
        if support == 0:
            classes[label] = {"support": 0, "predicted": predicted, "precision": 0.0 if predicted else None,
                              "recall": None, "f1": None, "absent_from_gold": True}
            continue
        precision = tp / predicted if predicted else 0.0
        recall = tp / support
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        classes[label] = {"support": support, "predicted": predicted, "precision": precision,
                          "recall": recall, "f1": f1, "absent_from_gold": False}
        f1s.append(f1)
    present = [label for label in labels if not classes[label]["absent_from_gold"]]
    return {"per_class": classes, "macro_f1": sum(f1s) / len(f1s) if f1s else None,
            "macro_f1_classes": present,
            "absent_classes": [label for label in labels if label not in present],
            "accuracy": sum(matrix[l][l] for l in labels) / len(gold) if gold else None,
            "confusion_matrix": {"rows_gold_cols_pred": list(labels), "counts": matrix}}


def fit_predict_tfidf_logreg(train_texts, train_labels, test_texts, seed=42, params=None):
    """Fit on the training fold only (vectorizer included) and predict the held-out fold."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    params = params or {}
    model = make_pipeline(
        TfidfVectorizer(lowercase=True, ngram_range=tuple(params.get("ngram_range", (1, 2))),
                        sublinear_tf=True, min_df=params.get("min_df", 1)),
        LogisticRegression(max_iter=params.get("max_iter", 1000),
                           class_weight=params.get("class_weight", "balanced"),
                           random_state=seed))
    model.fit(train_texts, train_labels)
    return list(model.predict(test_texts))


def cross_validate(records, assignment, k, seed=42, params=None, fit_predict=fit_predict_tfidf_logreg):
    """Out-of-fold predictions {id: predicted label}, with per-fold training-label counts."""
    predictions, fold_info = {}, []
    for fold in range(k):
        train = [r for r in records if assignment[r["id"]] != fold]
        test = [r for r in records if assignment[r["id"]] == fold]
        labels_seen = {r["label"] for r in train}
        if len(labels_seen) < 2:
            raise ValueError(f"Fold {fold}: training data has fewer than two classes")
        out = fit_predict([r["prompt"] for r in train], [r["label"] for r in train],
                          [r["prompt"] for r in test], seed, params)
        for rec, label in zip(test, out):
            predictions[rec["id"]] = validate_label(label)
        fold_info.append({"fold": fold, "train_items": len(train), "eval_items": len(test),
                          "train_label_counts": dict(Counter(r["label"] for r in train))})
    return predictions, fold_info
