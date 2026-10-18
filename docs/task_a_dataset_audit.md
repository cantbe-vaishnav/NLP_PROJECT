# Task A preliminary dataset audit — 2026-09-12

Status: label policy APPROVED by the user. Phase 1 remains incomplete at an
authenticated-access/source-selection gate. See `phase1_access_gate_report.md`
for actual API observations and the limited downloaded preview.
All sizes below are upstream descriptions, not measured SafeLLM statistics.

## Approved label policy

Harmfulness and adversarial manipulation are different targets. A direct harmful
request may contain no jailbreak; an instruction override may seek harmless
content. Mapping safety labels directly would silently change the research task.

Canonical four-label Task A schema (supersedes the earlier three-label policy,
which had no HARMFUL label; definitions are in
[task_a_semantic_pilot_guidelines.md](task_a_semantic_pilot_guidelines.md)):

- BENIGN: non-adversarial; does not necessarily mean harmless.
- HARMFUL: harmful or problematic content without sufficiently evidenced attempts
  to manipulate or circumvent a higher-priority instruction or safety boundary.
- ADVERSARIAL: an attempt to manipulate, override or circumvent higher-priority
  instructions or safety boundaries, regardless of whether the requested content
  is harmful. Harmful subject matter alone is insufficient.
- QUARANTINE: insufficient context or genuine ambiguity prevents a reliable
  decision. Role-play, topic changes and quoted attacks are not automatically attacks.
- Audit source adversarial flags against this scheme before accepting a mapping;
  see [task_a_source_label_comparison.md](task_a_source_label_comparison.md).

## Candidate inventory

### WildGuardMix — preferred for further audit, not selected

Ai2 [dataset card](https://huggingface.co/datasets/allenai/wildguardmix/blob/main/README.md).
Declared license: ODC-BY; card describes access conditions and user information
requirements. No agreement or download attempted. Upstream: 86,759 training and
1,725 test items, not necessarily unique prompts. Fields: `prompt`, boolean
`adversarial`, response, harm/refusal labels, and `subcategory` (risk category).
Candidate mapping uses the adversarial flag, never prompt harmfulness directly.
Repeated prompt/response variants require deduplication. Preserve official test
membership; quarantine overlaps from training rather than reshuffle test rows.
Hard negatives require review. Unseen formulations require verified family
provenance; risk categories do not establish unseen attack categories.

### Deepset prompt-injections — diagnostic candidate, not accepted

Deepset [dataset/viewer](https://huggingface.co/datasets/deepset/prompt-injections).
Declared license: Apache-2.0. Fields: `text`, integer `label` (0/1). Viewer shows
546 training rows; total/test size not verified here. Candidate mapping is
1 → ADVERSARIAL and 0 → BENIGN, subject to semantic review. A positive debater
role instruction in the viewer appears context-dependent; missing application
instructions prevent deciding whether it attacks a boundary. This does not prove
the source label wrong. Repeated wording needs inspection. No attack-family or
category metadata verified. Dedicated hard negatives and unseen formulations
are unverified; unseen-category evaluation unsupported by inspected schema.

### WildJailbreak — deferred pending semantics and access

Ai2 [dataset card](https://huggingface.co/datasets/allenai/wildjailbreak).
Declared license: ODC-BY; gated access requires agreement/contact information.
Card describes approximately 262K training pairs and 2,210 evaluation examples.
Fields: `vanilla`, `adversarial`, `tactics`, `completion`, `data_type`. Four types
separate vanilla/adversarial and harmful/benign. Adversarial-benign examples are
not automatically SafeLLM hard negatives; review their actual behavior. Shared
vanilla parents and combined tactics create leakage risks. Unseen formulations
may use verified parent groups. Overlapping tactics do not yet justify exclusive
attack-category holdouts. No label mapping accepted.

### JailbreakBench JBB-Behaviors — reject direct positive-label mapping

[Official documentation](https://github.com/JailbreakBench/jailbreakbench),
[dataset license](https://huggingface.co/datasets/JailbreakBench/JBB-Behaviors/blob/main/LICENSE).
MIT; 100 harmful and 100 benign behaviors. Fields: Behavior, Goal, Target,
Category, Source. Harmful goals are not necessarily jailbreak transformations.
Categories describe misuse topics, not attack mechanisms. Benign goals are
potential reviewed controls but too few for the primary corpus. No dedicated
attack-discussion hard negatives established. Behavior tables alone support
neither unseen formulations nor unseen attack categories. Submitted jailbreak
artifacts are a separate candidate needing schema/license/provenance inspection.

### HarmBench — defer artifact audit; reject behavior-only mapping

Center for AI Safety [official repository](https://github.com/centerforaisafety/HarmBench).
Repository declares MIT; individual artifacts still need provenance review.
Behaviors, generated test cases, completions and evaluations are separate stages.
Requested harmful behaviors and completion-success labels are not binary
prompt-manipulation labels. Selected-file schema, size and license coverage remain
unverified; no files selected. Hard negatives are not established. Formulation or
method holdouts require artifact inspection; no valid category split established.

## Literature follow-up

- [MoJE](https://arxiv.org/abs/2409.17699): lightweight detection motivation;
  reusable corpus/schema/license not verified in this preliminary audit.
- [DataSentinel](https://arxiv.org/abs/2504.11358): injection-detection motivation;
  reusable corpus/schema/license not yet verified.
- [Bypassing LLM Guardrails](https://aclanthology.org/2025.llmsec-1.8.pdf): evasion
  evaluation motivation; preserve attack-relevant character features. Associated
  dataset artifacts have not been accepted.

This inventory is preliminary, not exhaustive. Further artifact research remains
Phase 1 work. No published model findings are claimed as SafeLLM results.

## Proposed implementation after review

Pin source revisions/checksums and inspect actual schemas and label samples before
adapters. Preserve original text; separate comparison normalization from model
input. Record malformed/empty exclusions and conflicting labels. Group exact and
detected near duplicates and verified shared templates before any new split.
Review grouping thresholds and source/label confounds before final generation.
Near-duplicate checks cannot prove every template leak absent.

Use seed 42. Prefer a validation split from official training data while protecting
official test membership; ratios remain pending observed groups. Save provenance,
configuration, exclusions, counts, length summaries, groups and cross-split checks.
No generated dataset may be manually edited.

Common schema proposal: `id`, `prompt`, `original_prompt`, `label`, `source`,
nullable `attack_category`, nullable `attack_type`, `split`, `metadata`. Preserve
original row/split identifiers. Never invent categories from harmful-topic labels.

Hard-negative workflow proposal: candidate text/source, context adequacy, reviewer
IDs, independent labels/rationales, review status and adjudication. No seed set
has been constructed or represented as human reviewed. Formulation and category
holdouts remain separate proposed structures; neither has been generated.

## Gate status

Selected datasets: none finalized. Normalized size, class distribution, duplicate
counts and split sizes: unavailable. Hard-negative and category-held-out sets:
absent. Gate 1 (data ready): NOT passed. No model work authorized.

Next step: obtain authorized access to WildGuardMix for actual sample inspection.
See the access gate report; no fallback corpus is silently substituted.
