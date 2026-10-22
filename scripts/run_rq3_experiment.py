"""RQ3 held-out experiments: retrain a Task A model on a reduced training pool and score held-out sets.

    python scripts/run_rq3_experiment.py --experiment A --model logreg|svm|distilbert
    python scripts/run_rq3_experiment.py --experiment B --model logreg|svm|distilbert

A: unseen harm topic. Removes WildGuardMix subcategory "cyberattack" and every train/validation row matching the
   cyber keyword list (scripts/preview_rq3_split.py) from training and model selection.
B: unseen source. Trains and selects on WildGuardMix rows only; every JailbreakHub row is held out.
Training, model selection and inference follow the RQ1 notebooks exactly (same configs, seed 42, thresholds); only
the split membership changes. Dataset v2 and the RQ1 runs are read, never written. Each run gets a new folder:
results/task_a_rq3_<experiment>/<model>/run_<timestamp>/ with run.json, metrics.json, predictions.csv (Git-ignored)
and, for the transformer, the fine-tuned model (Git-ignored).
"""

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from preview_rq3_split import HELD_OUT, KEYWORDS  # noqa: E402
from task_a.binary_metrics import binary_metrics  # noqa: E402
from task_a.leakage import comparison_key  # noqa: E402
from task_a.tfidf_baseline import load_rows, select_c, write_run  # noqa: E402

EXPERIMENT_DIRS = {"A": "results/task_a_rq3_heldout_cyberattack", "B": "results/task_a_rq3_heldout_jailbreakhub"}
COLUMNS = ["example_id", "text", "label", "source_dataset", "split", "family_id", "source_metadata"]


def wilson(k, n, z=1.96):
    if n == 0:
        return [None, None]
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(float(centre - half), 4), round(float(centre + half), 4)]


def assign(df, experiment):
    """Training role of every row ('train', 'validation' or None) and the named evaluation sets (row masks)."""
    pool = df["split"].isin(["train", "validation"])
    if experiment == "A":
        held = df["subcategory"] == HELD_OUT
        related = df["text"].str.contains(KEYWORDS) & ~held
        keep = pool & ~held & ~related
        sets = {"heldout_cyberattack_pool": pool & held,
                "heldout_cyberattack_official_test": (df["split"] == "test_official") & held,
                "official_test_without_cyberattack": (df["split"] == "test_official") & ~held,
                "test_jailbreakhub": df["split"] == "test_jailbreakhub",
                "keyword_related_removed": pool & related}
    else:
        jbh = df["source_dataset"] == "jailbreakhub"
        keep = pool & ~jbh
        sets = {"test_jailbreakhub": df["split"] == "test_jailbreakhub",
                "test_jailbreakhub_jbh_rows_only": (df["split"] == "test_jailbreakhub") & jbh,
                "all_jailbreakhub_rows": jbh,
                "official_test": df["split"] == "test_official"}
    # Family closure: a training row whose near-duplicate family has any held-out member is dropped as well.
    held_families = set().union(*(set(df.loc[m, "family_id"]) for m in sets.values()))
    closure = keep & df["family_id"].isin(held_families)
    role = df["split"].where(keep & ~closure)
    return role, sets, int(closure.sum())


def check_split(df, role, sets):
    """Families stay within one role, no held-out text appears in training, the official test is untouched."""
    training = df[role.notna()]
    assert training.groupby("family_id")["split"].nunique().max() == 1
    train_keys = set(training["text"].map(comparison_key))
    for name, mask in sets.items():
        assert not df.loc[mask, "text"].map(comparison_key).isin(train_keys).any(), f"{name} overlaps training"
        assert not set(df.loc[mask, "family_id"]) & set(training["family_id"]), f"{name} shares a family with training"
    raw_test = pd.read_parquet(ROOT.parent / "NLP_PROJECT/data/raw/wildguard_test.parquet", columns=["prompt", "adversarial"])
    official = df[df["split"] == "test_official"]
    assert sorted(zip(official["text"], official["label"])) == sorted(zip(raw_test["prompt"], raw_test["adversarial"].astype(int)))


def score_report(frame, scores, threshold):
    """binary_metrics plus Wilson intervals for adversarial recall and FPR."""
    pred = (np.asarray(scores) >= threshold).astype(int)
    m = binary_metrics(frame["label"].tolist(), pred.tolist())
    cm = m["confusion_matrix"]
    m["recall_ci95"] = wilson(cm["tp"], cm["tp"] + cm["fn"])
    m["fpr_ci95"] = wilson(cm["fp"], cm["fp"] + cm["tn"])
    return m, pred


def train_tfidf(kind, train, validation, base, svm_config):
    """RQ1 procedure: C chosen by validation macro-F1 only (ties to the smaller C); returns (model, score_fn, record)."""
    if kind == "logreg":
        best_c, search, model = select_c(train.to_dict("records"), validation.to_dict("records"), base["c_grid"],
                                         base["model"], base["seed"], base["threshold"])
        return (lambda texts: model.predict_proba(texts)[:, 1]), model, base["threshold"], {"selected_C": best_c, "c_search": search}
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.pipeline import make_pipeline
    from sklearn.svm import LinearSVC
    tfidf = base["model"]
    vectorizer = TfidfVectorizer(ngram_range=tuple(tfidf["ngram_range"]), min_df=tfidf["min_df"], sublinear_tf=True, lowercase=True)
    x_train = vectorizer.fit_transform(train["text"])
    x_val = vectorizer.transform(validation["text"])
    search, best = [], (None, -1.0, None)
    for c in sorted(svm_config["c_grid"]):
        clf = LinearSVC(C=c, class_weight=tfidf["class_weight"], max_iter=svm_config["max_iter"], random_state=base["seed"]).fit(x_train, train["label"])
        f1 = binary_metrics(validation["label"].tolist(), (clf.decision_function(x_val) >= svm_config["threshold"]).astype(int).tolist())["macro_f1"]
        search.append({"C": c, "validation_macro_f1": f1})
        if f1 > best[1]:
            best = (c, f1, clf)
    model = make_pipeline(vectorizer, best[2])
    return model.decision_function, model, svm_config["threshold"], {"selected_C": best[0], "c_search": search}


def train_distilbert(train, validation, base, config):
    """RQ1 notebook loop: AdamW, linear warmup, balanced class weights, bf16, best epoch by validation macro-F1."""
    import torch
    import transformers
    from torch.utils.data import DataLoader
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, DataCollatorWithPadding, get_linear_schedule_with_warmup, set_seed
    set_seed(base["seed"])
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    use_bf16 = device.type == "cuda" and torch.cuda.is_bf16_supported()
    transformers.logging.set_verbosity_error()
    tokenizer = AutoTokenizer.from_pretrained(config["model_name"])
    model = AutoModelForSequenceClassification.from_pretrained(config["model_name"], num_labels=2, id2label={0: "BENIGN", 1: "ADVERSARIAL"},
                                                               label2id={"BENIGN": 0, "ADVERSARIAL": 1}).to(device)
    collate = DataCollatorWithPadding(tokenizer)

    def encode(frame, with_labels=True):
        tok = tokenizer(frame["text"].tolist(), truncation=True, max_length=config["max_length"])
        return [{"input_ids": i, "attention_mask": m, **({"labels": int(l)} if with_labels else {})}
                for i, m, l in zip(tok["input_ids"], tok["attention_mask"], frame["label"])]

    @torch.no_grad()
    def scores(texts):
        model.eval()
        tok = tokenizer(list(texts), truncation=True, max_length=config["max_length"])
        rows = [{"input_ids": i, "attention_mask": m} for i, m in zip(tok["input_ids"], tok["attention_mask"])]
        out = []
        for batch in DataLoader(rows, batch_size=config["eval_batch_size"], collate_fn=collate):
            batch = {k: v.to(device) for k, v in batch.items()}
            with torch.autocast(device_type=device.type, dtype=torch.bfloat16, enabled=use_bf16):
                logits = model(**batch).logits
            out += torch.softmax(logits.float(), dim=-1)[:, 1].tolist()
        return np.array(out)

    train_loader = DataLoader(encode(train), batch_size=config["train_batch_size"], shuffle=True, collate_fn=collate,
                              generator=torch.Generator().manual_seed(base["seed"]))
    optimizer = torch.optim.AdamW(model.parameters(), lr=config["learning_rate"], weight_decay=config["weight_decay"])
    total_steps = len(train_loader) * config["max_epochs"]
    scheduler = get_linear_schedule_with_warmup(optimizer, int(config["warmup_ratio"] * total_steps), total_steps)
    counts = np.bincount(train["label"], minlength=2)
    loss_fn = torch.nn.CrossEntropyLoss(weight=torch.tensor(counts.sum() / (2 * counts), dtype=torch.float, device=device))
    history, best_f1, best_epoch, best_state, stale = [], -1.0, None, None, 0
    for epoch in range(1, config["max_epochs"] + 1):
        model.train()
        start, total_loss = time.time(), 0.0
        for batch in train_loader:
            batch = {k: v.to(device) for k, v in batch.items()}
            labels = batch.pop("labels")
            with torch.autocast(device_type=device.type, dtype=torch.bfloat16, enabled=use_bf16):
                logits = model(**batch).logits
            loss = loss_fn(logits.float(), labels)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step(); scheduler.step(); optimizer.zero_grad()
            total_loss += loss.item()
        val_pred = (scores(validation["text"]) >= config["threshold"]).astype(int)
        val_f1 = binary_metrics(validation["label"].tolist(), val_pred.tolist())["macro_f1"] or 0.0
        history.append({"epoch": epoch, "train_loss": total_loss / len(train_loader), "validation_macro_f1": val_f1,
                        "minutes": round((time.time() - start) / 60, 2)})
        print(history[-1], flush=True)
        if val_f1 > best_f1:
            best_f1, best_epoch, stale = val_f1, epoch, 0
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        else:
            stale += 1
            if stale >= config["early_stopping_patience"]:
                break
    model.load_state_dict(best_state)
    scores.save = lambda path: (model.save_pretrained(path), tokenizer.save_pretrained(path))  # called after write_run
    return scores, None, config["threshold"], {"selected_epoch": best_epoch, "selected_validation_macro_f1": best_f1,
                                               "training_history": history, "versions": {"torch": torch.__version__, "transformers": transformers.__version__}}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--experiment", choices=["A", "B"], required=True)
    parser.add_argument("--model", choices=["logreg", "svm", "distilbert"], required=True)
    args = parser.parse_args()
    started = time.time()

    base = json.loads((ROOT / "configs/task_a_binary_tfidf_v2.json").read_text(encoding="utf-8"))
    svm_config = json.loads((ROOT / "configs/task_a_binary_tfidf_linear_svm_v2.json").read_text(encoding="utf-8"))
    bert_config = json.loads((ROOT / "configs/task_a_binary_distilbert_v2.json").read_text(encoding="utf-8"))
    rows, dataset_sha256 = load_rows(ROOT / base["dataset"], columns=COLUMNS)
    assert dataset_sha256 == "f4852e888871b09477149852ecf500c3344171cf5fcd5bf65b9828dfe7ec24f2", "dataset v2 differs from the RQ1 runs"
    df = pd.DataFrame(rows)
    df["subcategory"] = df["source_metadata"].map(lambda s: json.loads(s).get("subcategory"))
    role, sets, family_closure_rows = assign(df, args.experiment)
    check_split(df, role, sets)
    train, validation = df[role == "train"].reset_index(drop=True), df[role == "validation"].reset_index(drop=True)

    run_dir = ROOT / EXPERIMENT_DIRS[args.experiment] / args.model / datetime.now(timezone.utc).strftime("run_%Y%m%dT%H%M%SZ")
    if args.model == "distilbert":
        score_fn, model, threshold, record = train_distilbert(train, validation, base, bert_config)
    else:
        score_fn, model, threshold, record = train_tfidf(args.model, train, validation, base, svm_config)
    train_seconds = time.time() - started

    # Score validation and every evaluation set once with the selected model.
    results, predictions = {}, []
    eval_sets = {"validation": role == "validation", **sets}
    for name, mask in eval_sets.items():
        frame = df[mask]
        s = score_fn(frame["text"].tolist())
        results[name], pred = score_report(frame, s, threshold)
        predictions += [{"example_id": e, "split": name, "gold": int(g), "score": round(float(v), 6), "pred": int(p)}
                        for e, g, v, p in zip(frame["example_id"], frame["label"], s, pred)]
    split_counts = {name: {"benign": int((df.loc[m, "label"] == 0).sum()), "adversarial": int((df.loc[m, "label"] == 1).sum())}
                    for name, m in {"train": role == "train", **eval_sets}.items()}
    record.update({"created_utc": datetime.now(timezone.utc).isoformat(), "script": "scripts/run_rq3_experiment.py",
                   "experiment": args.experiment, "model": args.model, "dataset_sha256": dataset_sha256, "seed": base["seed"],
                   "configs": {"base": base, "svm": svm_config if args.model == "svm" else None,
                               "distilbert": bert_config if args.model == "distilbert" else None},
                   "threshold": threshold, "split_counts": split_counts, "family_closure_rows_removed": family_closure_rows,
                   "train_ids_sha256": hashlib.sha256("\n".join(sorted(train["example_id"])).encode()).hexdigest(),
                   "validation_ids_sha256": hashlib.sha256("\n".join(sorted(validation["example_id"])).encode()).hexdigest(),
                   "runtime_seconds": {"train_and_select": round(train_seconds, 1), "total": round(time.time() - started, 1)}})
    write_run(run_dir, record, results, predictions, model=model)  # creates run_dir; refuses an existing one
    if hasattr(score_fn, "save"):
        score_fn.save(run_dir / "model")
    print(json.dumps({k: {"macro_f1": v["macro_f1"], "recall": v["per_class"]["ADVERSARIAL"]["recall"], "fpr": v["fpr"]}
                      for k, v in results.items()}, indent=1))
    print("runtime", record["runtime_seconds"], "saved to", run_dir.relative_to(ROOT))


if __name__ == "__main__":
    main()
