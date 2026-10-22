"""Categorized jailbreak-cue matching for label review. Never changes labels or data.

Replaces the single crude regex in `binary_dataset.suspicious_reasons` for review
purposes only: "DAN" is case-sensitive (so the Malay/Indonesian word "dan" no longer
matches), the AIPRM "Please ignore all previous instructions." template opener is
separated from genuine instruction overrides, and cues are grouped into categories
with a strength so reviewers can prioritise.
"""
import re

_I = re.IGNORECASE
CUES = {
    # strong: wording whose usual function is to remove or evade safety behaviour
    "dan_persona": (re.compile(r"\bDAN\b|\bdo anything now\b|\bSTAN\b|\bDUDE\b"), "strong"),
    "developer_mode": (re.compile(r"\b(developer|dev) mode\b", _I), "strong"),
    "jailbreak_term": (re.compile(r"\bjail ?break(s|ing|en|ed)?\b", _I), "strong"),
    "restriction_removal": (re.compile(
        r"\b(no|without( any)?|free (from|of)( all| any)?|not bound by( any)?)\s+(restrictions?|"
        r"filters?|limits?|limitations|censorship|rules|guidelines|morals?|ethics|boundaries)\b"
        r"|\b(unfiltered|uncensored|unrestricted|amoral|unethical ai)\b", _I), "strong"),
    "policy_evasion": (re.compile(
        r"\b(ignore|bypass|disregard|violate|break|circumvent)\w*\s+(\w+\s+){0,3}"
        r"(content |safety |usage |ethical )?(polic(y|ies)|guidelines|filters?|safeguards)\b"
        r"|\bopenai'?s?\s+(content\s+)?polic(y|ies)\b", _I), "strong"),
    "refusal_suppression": (re.compile(
        r"\b(never|will not|won'?t|cannot|can'?t|do not|don'?t|must not)\s+(ever\s+)?"
        r"(refuse|decline|say (no|that you can'?t))\b|\banswers? (all|any|every) "
        r"(requests?|questions?|prompts?)\b", _I), "strong"),
    "instruction_override": (re.compile(
        r"\b(ignore|disregard|forget)\s+(all\s+|any\s+|the\s+|your\s+)?(previous|prior|above|"
        r"earlier|preceding|original)\s+(instructions|prompts?|rules|directions|messages)\b", _I),
        "strong"),
    # weak: common in harmless role-play and prompt templates
    "persona_setup": (re.compile(
        r"\bfrom now on,? you (are|will)\b|\bstay in character\b|\byou are no longer\b"
        r"|\bact as\b|\bpretend (to be|you are)\b", _I), "weak"),
}
# AIPRM prompt templates open with this sentence and then give an ordinary task.
AIPRM_OPENER = re.compile(r"^\s*please ignore all previous instructions\.", _I)
AIPRM_TOKEN = re.compile(r"\[(TARGETLANGUAGE|PROMPT|KEYWORD|VARIABLE\d?)\]")


def match_cues(text):
    """{category: [matched strings]} for every category that matches."""
    out = {}
    for name, (pattern, _) in CUES.items():
        found = sorted({m.group(0).strip() for m in pattern.finditer(text)})
        if found:
            out[name] = found
    return out


def is_aiprm_boilerplate(text):
    return bool(AIPRM_OPENER.match(text) or (AIPRM_TOKEN.search(text) and
                                             CUES["instruction_override"][0].search(text)))


def review_priority(text):
    """(priority, strong categories, matches). Priority: high, medium, low or none.

    An instruction override inside an AIPRM template does not count as strong.
    high = two or more strong categories; medium = one; low = weak cues or AIPRM opener only.
    """
    matches = match_cues(text)
    strong = [c for c in matches if CUES[c][1] == "strong"]
    if "instruction_override" in strong and is_aiprm_boilerplate(text):
        strong.remove("instruction_override")
    if len(strong) >= 2:
        return "high", strong, matches
    if strong:
        return "medium", strong, matches
    return ("low" if matches else "none"), strong, matches
