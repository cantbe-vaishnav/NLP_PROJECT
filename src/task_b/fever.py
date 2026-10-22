"""Resolve official FEVER gold evidence without inventing missing text."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
from typing import Any

from .schema import ClaimEvidence, parse_claim_evidence


GOLD_LABELS = {"SUPPORTS": "SUPPORTED", "REFUTES": "CONTRADICTED"}


@dataclass(frozen=True)
class FeverRecord:
    claim: ClaimEvidence
    gold_label: str
    source_label: str
    source_file: str
    wiki_dir: str
    source_line: int
    raw_evidence: list[Any]
    selected_group: int
    raw_id: int | str
    evidence_source: str = "gold"  # "gold" FEVER evidence, or "retrieved" for NOT ENOUGH INFO claims

    def to_dict(self) -> dict[str, Any]:
        claim = asdict(self.claim)
        claim.pop("answer_id", None)
        claim.pop("claim_span", None)
        for sentence in claim["evidence"]:
            if sentence["source_document_id"] is None:
                sentence.pop("source_document_id")
        return {
            "claim": claim, "gold_label": self.gold_label,
            "source_label": self.source_label, "dataset_format": "FEVER JSONL",
            "source_file": self.source_file, "wiki_dir": self.wiki_dir,
            "source_line": self.source_line, "raw_evidence": self.raw_evidence,
            "selected_group": self.selected_group, "raw_id": self.raw_id,
            "evidence_source": self.evidence_source,
        }


def _read_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                yield line_number, None, "blank line"
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                yield line_number, None, f"invalid JSON: {exc.msg}"
                continue
            yield line_number, row, None


def _valid_ref(ref: object) -> tuple[str, int] | None:
    if (not isinstance(ref, list) or len(ref) != 4
            or not isinstance(ref[2], str) or not ref[2]
            or type(ref[3]) is not int or ref[3] < 0):
        return None
    return ref[2], ref[3]


def _load_wiki(wiki_dir: Path, wanted: set[tuple[str, int]]) -> tuple[dict[tuple[str, int], str], list[str]]:
    if not wiki_dir.is_dir():
        raise FileNotFoundError(f"FEVER wiki-pages directory missing: {wiki_dir}")
    files = sorted(wiki_dir.glob("*.jsonl"))
    if not files:
        raise FileNotFoundError(f"No wiki-pages JSONL files in {wiki_dir}")
    pages = {page for page, _ in wanted}
    found: dict[tuple[str, int], str] = {}
    conflicts: set[tuple[str, int]] = set()
    problems: list[str] = []
    for path in files:
        for number, row, error in _read_jsonl(path):
            if error:
                problems.append(f"{path.name}:{number}: {error}")
                continue
            if not isinstance(row, dict) or not isinstance(row.get("id"), str):
                problems.append(f"{path.name}:{number}: invalid wiki page")
                continue
            page = row["id"]
            if page not in pages:
                continue
            lines = row.get("lines")
            if not isinstance(lines, str):
                problems.append(f"{path.name}:{number}: missing lines for {page}")
                continue
            for line in lines.splitlines():
                parts = line.split("\t", 2)
                if len(parts) < 2 or not parts[0].isdigit():
                    problems.append(f"{path.name}:{number}: invalid sentence line for {page}")
                    continue
                key = (page, int(parts[0]))
                if key in wanted and parts[1].strip():
                    if key in conflicts:
                        continue
                    if key in found and found[key] != parts[1]:
                        problems.append(f"{path.name}:{number}: duplicate conflicting sentence {key}")
                        conflicts.add(key)
                        found.pop(key)
                    else:
                        found[key] = parts[1]
    return found, problems


def prepare_fever(claims_path: str | Path, wiki_dir: str | Path) -> tuple[list[FeverRecord], dict[str, Any]]:
    """Use the first fully resolved gold group; exclude NEI and unresolved rows."""
    claims_path, wiki_dir = Path(claims_path), Path(wiki_dir)
    rows: list[tuple[int, dict[str, Any], list[tuple[int, list[tuple[str, int]]]]]] = []
    issues: list[str] = []
    wanted: set[tuple[str, int]] = set()
    skipped_nei = 0
    seen_ids: set[str] = set()
    for number, row, error in _read_jsonl(claims_path):
        if error:
            issues.append(f"claims:{number}: {error}")
            continue
        if not isinstance(row, dict):
            issues.append(f"claims:{number}: expected object")
            continue
        if row.get("label") == "NOT ENOUGH INFO":
            skipped_nei += 1
            continue
        raw_id = row.get("id")
        claim_id = str(raw_id)
        groups = row.get("evidence")
        if (type(raw_id) not in (int, str) or not claim_id.strip()
                or claim_id in seen_ids or not isinstance(row.get("claim"), str)
                or not row["claim"].strip() or row.get("label") not in GOLD_LABELS
                or not isinstance(groups, list) or not groups):
            issues.append(f"claims:{number}: invalid id, claim, label or evidence groups")
            continue
        seen_ids.add(claim_id)
        parsed: list[tuple[int, list[tuple[str, int]]]] = []
        for group_index, group in enumerate(groups):
            if not isinstance(group, list) or not group:
                issues.append(f"claims:{number}: empty/invalid evidence group")
                continue
            refs = [_valid_ref(ref) for ref in group]
            if any(ref is None for ref in refs):
                issues.append(f"claims:{number}: invalid evidence reference")
                continue
            parsed.append((group_index, refs))  # type: ignore[arg-type]
            wanted.update(refs)  # type: ignore[arg-type]
        if parsed:
            rows.append((number, row, parsed))
        else:
            issues.append(f"claims:{number}: no valid evidence group")
    wiki, wiki_issues = _load_wiki(wiki_dir, wanted)
    issues.extend(wiki_issues)
    records: list[FeverRecord] = []
    unresolved = 0
    for number, row, groups in rows:
        chosen = next(((index, group) for index, group in groups
                       if all(ref in wiki for ref in group)), None)
        if chosen is None:
            unresolved += 1
            missing = sorted({ref for _, group in groups for ref in group if ref not in wiki})
            issues.append(f"claims:{number}: unresolved gold evidence {missing}")
            continue
        index, refs = chosen
        # Duplicate references within a group are collapsed because B0 requires unique IDs.
        unique_refs = list(dict.fromkeys(refs))
        adapted = parse_claim_evidence({
            "claim_id": str(row["id"]), "claim": row["claim"],
            "evidence": [{"evidence_id": json.dumps([page, sentence_id], ensure_ascii=False),
                          "source_document_id": page, "text": wiki[(page, sentence_id)]}
                         for page, sentence_id in unique_refs],
        })
        records.append(FeverRecord(adapted, GOLD_LABELS[row["label"]], row["label"],
                                   str(claims_path), str(wiki_dir), number,
                                   row["evidence"], index, row["id"]))
    report = {"source_file": str(claims_path), "wiki_dir": str(wiki_dir),
              "resolved": len(records), "unresolved": unresolved,
              "skipped_nei": skipped_nei, "issues": issues}
    return records, report


def write_prepared(records: list[FeverRecord], report: dict[str, Any], output_dir: str | Path) -> None:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "records.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
    (directory / "resolution_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


def claim_key(text: str) -> str:
    """Case- and whitespace-insensitive claim text, used to keep validation and evaluation disjoint."""
    return " ".join(text.casefold().split())


def write_validation_sample(train_path: str | Path, output_path: str | Path, per_label: int,
                            seed: int, exclude_claims: set[str], include_nei: bool = False) -> dict[str, Any]:
    """Sample SUPPORTS/REFUTES (and optionally NOT ENOUGH INFO) training rows, unchanged, for threshold selection.

    Rows whose claim text matches an evaluation claim (after claim_key) are skipped.
    Returns a manifest with the seed, counts and source so the sample can be rebuilt.
    """
    import random
    wanted = [*GOLD_LABELS, *(["NOT ENOUGH INFO"] if include_nei else [])]
    by_label: dict[str, list[str]] = {label: [] for label in wanted}
    overlapping = 0
    for number, row, error in _read_jsonl(Path(train_path)):
        if error or not isinstance(row, dict) or row.get("label") not in wanted:
            continue
        if claim_key(str(row.get("claim", ""))) in exclude_claims:
            overlapping += 1
            continue
        by_label[row["label"]].append(json.dumps(row, ensure_ascii=False))
    rng = random.Random(seed)
    chosen = []
    for label, rows in by_label.items():
        if len(rows) < per_label:
            raise ValueError(f"only {len(rows)} {label} rows available for {per_label} requested")
        chosen.extend(rng.sample(rows, per_label))
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(chosen) + "\n", encoding="utf-8")
    return {"source_file": str(train_path), "seed": seed, "per_label": per_label, "labels": wanted,
            "rows": len(chosen), "skipped_overlapping_with_evaluation": overlapping}


def select_training_claims(train_path: str | Path, excluded_texts: dict[str, set[str]],
                           conflict_labels: tuple[str, ...] = (*GOLD_LABELS, "NOT ENOUGH INFO")
                           ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """SUPPORTS/REFUTES training rows, unchanged, that survive claim-text exclusions applied in order.

    `excluded_texts` maps a reason to claim_key texts; every row with such a text is removed whatever its id.
    Texts carrying more than one of `conflict_labels` within the training file are removed last.
    Duplicate ids or unreadable rows raise instead of being skipped.
    """
    rows: list[tuple[str, dict[str, Any]]] = []
    ids: set[str] = set()
    labels_by_text: dict[str, set[str]] = {}
    for number, row, error in _read_jsonl(Path(train_path)):
        if error or not isinstance(row, dict) or not isinstance(row.get("claim"), str):
            raise ValueError(f"invalid training row at line {number}: {error or 'expected object with a claim'}")
        raw_id = str(row.get("id"))
        if raw_id in ids:
            raise ValueError(f"duplicate training id {raw_id} at line {number}")
        ids.add(raw_id)
        key = claim_key(row["claim"])
        if row.get("label") in conflict_labels:
            labels_by_text.setdefault(key, set()).add(row["label"])
        if row.get("label") in GOLD_LABELS:
            rows.append((key, row))
    conflicting = {key for key, labels in labels_by_text.items() if len(labels) > 1}
    combos: dict[str, int] = {}
    for key in conflicting:
        name = "+".join(sorted(labels_by_text[key]))
        combos[name] = combos.get(name, 0) + 1
    reasons = [*excluded_texts.items(), ("conflicting_labels", conflicting)]
    count = lambda subset: {label: sum(r["label"] == label for _, r in subset) for label in GOLD_LABELS}
    report: dict[str, Any] = {
        "source_file": str(train_path), "rows_read": len(ids), "supports_refutes_rows": len(rows),
        "supports_refutes_by_label": count(rows), "normalisation": "claim_key: casefold, whitespace collapsed",
        "conflict_labels": list(conflict_labels), "conflicting_claim_texts": len(conflicting),
        "conflicting_claim_texts_by_labels": dict(sorted(combos.items())),
        "rows_matching_each_exclusion_independently": {
            reason: sum(key in texts for key, _ in rows) for reason, texts in reasons},
        "removed_in_order": {}}
    kept = rows
    for reason, texts in reasons:
        removed = [item for item in kept if item[0] in texts]
        kept = [item for item in kept if item[0] not in texts]
        report["removed_in_order"][reason] = {"rows": len(removed), "by_label": count(removed),
                                              "distinct_claim_texts": len({key for key, _ in removed})}
    report["eligible_rows"] = len(kept)
    report["eligible_by_label"] = count(kept)
    report["eligible_distinct_claim_texts"] = len({key for key, _ in kept})
    return [row for _, row in kept], report


def balanced_sample(records: list[FeverRecord], seed: int) -> list[FeverRecord]:
    """Every CONTRADICTED record plus an equal seeded sample of SUPPORTED records, returned in file order."""
    import random
    contradicted = [record for record in records if record.gold_label == "CONTRADICTED"]
    supported = [record for record in records if record.gold_label == "SUPPORTED"]
    if len(supported) < len(contradicted):
        raise ValueError(f"only {len(supported)} SUPPORTED records for {len(contradicted)} CONTRADICTED")
    chosen = contradicted + random.Random(seed).sample(supported, len(contradicted))
    return sorted(chosen, key=lambda record: record.source_line)


def load_source_prior(path: str | Path, include_nei: bool = False) -> list[str]:
    """Read only source labels from an explicitly separate training/development file."""
    mapping = {**GOLD_LABELS, **({"NOT ENOUGH INFO": "UNSUPPORTED"} if include_nei else {})}
    labels = []
    for number, row, error in _read_jsonl(Path(path)):
        if error or not isinstance(row, dict):
            raise ValueError(f"invalid prior source at line {number}: {error}")
        if row.get("label") in mapping:
            labels.append(mapping[row["label"]])
    if not labels:
        raise ValueError("prior file has no SUPPORTS/REFUTES rows")
    return labels


# --- Evidence for NOT ENOUGH INFO claims (three-class evaluation) -------------------------------------
# FEVER annotators judged NEI claims unverifiable from Wikipedia, so their label maps to UNSUPPORTED.
# They have no gold evidence; giving them none would let a model learn "empty evidence = UNSUPPORTED".
# Policy: find Wikipedia pages whose title matches a capitalised phrase in the claim (FEVER-style
# document retrieval by title), then keep the sentence(s) from those pages that share the most words
# with the claim. Claims with no matching page are excluded and counted, never given placeholder text.

_WORD = re.compile(r"\w+", re.UNICODE)
_PTB = {"-LRB-": "(", "-RRB-": ")", "-LSB-": "[", "-RSB-": "]", "-LCB-": "{", "-RCB-": "}", "-COLON-": ":"}
STOPWORDS = {"a", "an", "the", "of", "in", "on", "at", "to", "for", "by", "and", "or", "is", "was", "are",
             "were", "be", "been", "has", "had", "have", "it", "its", "as", "with", "from", "that", "this"}


def title_key(page_id: str) -> str:
    """Page id -> lowercase words without the disambiguation, e.g. 'Gladiator_-LRB-2000_film-RRB-' -> 'gladiator'."""
    title = page_id.replace("_", " ")
    for token, char in _PTB.items():
        title = title.replace(token, char)
    title = re.sub(r"\s*\([^)]*\)\s*$", "", title)
    return " ".join(_WORD.findall(title.casefold()))


def claim_phrases(claim: str, max_words: int = 10) -> list[str]:
    """Word n-grams that start with a capitalised word and are not only stopwords (longest first)."""
    words = _WORD.findall(claim)
    phrases = set()
    for start, word in enumerate(words):
        if not word[:1].isupper():
            continue
        for end in range(start + 1, min(start + max_words, len(words)) + 1):
            phrase = [w.casefold() for w in words[start:end]]
            if not all(w in STOPWORDS for w in phrase):
                phrases.add(" ".join(phrase))
    return sorted(phrases, key=lambda p: (-len(p.split()), p))


def _sentences(lines: str) -> list[tuple[int, str]]:
    found = []
    for line in lines.splitlines():
        parts = line.split("\t", 2)
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].strip():
            found.append((int(parts[0]), parts[1]))
    return found


def retrieve_nei_evidence(claims_path: str | Path, wiki_dir: str | Path, sentences_per_claim: int = 1,
                          max_pages: int = 3) -> tuple[list[FeverRecord], dict[str, Any]]:
    """Retrieved evidence for every NOT ENOUGH INFO claim in a FEVER JSONL file (two Wikipedia scans)."""
    claims_path, wiki_dir = Path(claims_path), Path(wiki_dir)
    files = sorted(wiki_dir.glob("*.jsonl"))
    if not files:
        raise FileNotFoundError(f"No wiki-pages JSONL files in {wiki_dir}")
    claims = []
    for number, row, error in _read_jsonl(claims_path):
        if not error and isinstance(row, dict) and row.get("label") == "NOT ENOUGH INFO" \
                and isinstance(row.get("claim"), str) and row["claim"].strip():
            claims.append((number, row, claim_phrases(row["claim"])))
    wanted = {phrase for _, _, phrases in claims for phrase in phrases}
    # Scan 1: which pages match a wanted phrase (ids only, to keep memory small).
    pages_by_key: dict[str, list[str]] = {}
    for path in files:
        for _, page, error in _read_jsonl(path):
            if error or not isinstance(page, dict) or not isinstance(page.get("id"), str) or not page["id"]:
                continue
            key = title_key(page["id"])
            if key in wanted:
                pages_by_key.setdefault(key, []).append(page["id"])
    # Choose pages per claim: the longest matching phrase first; an undisambiguated title before others.
    chosen: dict[int, list[str]] = {}
    for index, (_, row, phrases) in enumerate(claims):
        picked: list[str] = []
        for phrase in phrases:
            candidates = sorted(pages_by_key.get(phrase, []), key=lambda pid: ("-LRB-" in pid, pid))
            for page_id in candidates:
                if page_id not in picked and len(picked) < max_pages:
                    picked.append(page_id)
            if len(picked) >= max_pages:
                break
        if picked:
            chosen[index] = picked
    # Scan 2: sentences of the chosen pages only.
    needed = {page_id for pages in chosen.values() for page_id in pages}
    page_sentences: dict[str, list[tuple[int, str]]] = {}
    for path in files:
        for _, page, error in _read_jsonl(path):
            if not error and isinstance(page, dict) and page.get("id") in needed and isinstance(page.get("lines"), str):
                page_sentences[page["id"]] = _sentences(page["lines"])
    records, no_page, no_sentence = [], 0, 0
    for index, (number, row, _) in enumerate(claims):
        if index not in chosen:
            no_page += 1
            continue
        content = set(_WORD.findall(row["claim"].casefold())) - STOPWORDS
        # Most shared content words first; ties go to the earlier-chosen page, then its earlier sentence.
        ranked = sorted(((len(content & set(_WORD.findall(text.casefold()))), rank, sid, page_id, text)
                         for rank, page_id in enumerate(chosen[index])
                         for sid, text in page_sentences.get(page_id, [])),
                        key=lambda item: (-item[0], item[1], item[2]))
        if not ranked:
            no_sentence += 1
            continue
        selected = [(page_id, sid, text) for _, _, sid, page_id, text in ranked[:sentences_per_claim]]
        claim = parse_claim_evidence({
            "claim_id": str(row["id"]), "claim": row["claim"],
            "evidence": [{"evidence_id": json.dumps([page_id, sid], ensure_ascii=False),
                          "source_document_id": page_id, "text": text} for page_id, sid, text in selected]})
        records.append(FeverRecord(claim, "UNSUPPORTED", "NOT ENOUGH INFO", str(claims_path), str(wiki_dir),
                                   number, row.get("evidence", []), -1, row["id"], evidence_source="retrieved"))
    report = {"source_file": str(claims_path), "nei_claims": len(claims), "retrieved": len(records),
              "no_matching_page": no_page, "no_sentence_on_matched_pages": no_sentence,
              "sentences_per_claim": sentences_per_claim, "max_pages": max_pages,
              "policy": "title-matched pages, highest word-overlap sentence(s); unreviewed"}
    return records, report
