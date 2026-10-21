"""Resolve official FEVER gold evidence without inventing missing text."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
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


def load_source_prior(path: str | Path) -> list[str]:
    """Read only source labels from an explicitly separate training/development file."""
    labels = []
    for number, row, error in _read_jsonl(Path(path)):
        if error or not isinstance(row, dict):
            raise ValueError(f"invalid prior source at line {number}: {error}")
        if row.get("label") in GOLD_LABELS:
            labels.append(GOLD_LABELS[row["label"]])
    if not labels:
        raise ValueError("prior file has no SUPPORTS/REFUTES rows")
    return labels
