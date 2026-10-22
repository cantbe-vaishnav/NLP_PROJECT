# JailbreakHub label review (counts only)

Counts and IDs only. Reviews are full-text reviews, not human annotation. No row has been excluded or relabelled; exclusions below are proposals.

## High-priority BENIGN rows (full text reviewed)

Rows: 184. Status: {'CONFIRMED_MISLABEL': 169, 'VALID_NON_JAILBREAK': 4, 'AMBIGUOUS': 11}. By split: {'test_jailbreakhub': {'CONFIRMED_MISLABEL': 12, 'AMBIGUOUS': 1}, 'train': {'CONFIRMED_MISLABEL': 141, 'VALID_NON_JAILBREAK': 4, 'AMBIGUOUS': 9}, 'validation': {'CONFIRMED_MISLABEL': 16, 'AMBIGUOUS': 1}}.
Confirmed mislabels already in mixed-label near-duplicate families: 43.

## Reverse audit of ADVERSARIAL (jailbreak-config) rows

Population 1304; sampling: sorted by example_id, Python random.seed(42), random.sample(n=40).
Status: {'VALID_JAILBREAK': 33, 'CONFIRMED_MISLABEL': 5, 'AMBIGUOUS': 2}; mislabel rate 0.125 (Wilson 95% [0.0546, 0.2611]).
By cue priority: {'high': {'VALID_JAILBREAK': 16}, 'medium': {'VALID_JAILBREAK': 8, 'AMBIGUOUS': 1}, 'low': {'VALID_JAILBREAK': 5, 'CONFIRMED_MISLABEL': 3}, 'none': {'VALID_JAILBREAK': 4, 'CONFIRMED_MISLABEL': 2, 'AMBIGUOUS': 1}}.

Remaining scope (label-1 JailbreakHub rows whose cue priority is none or low): 549 rows (15 already reviewed), by split {'train': 440, 'test_jailbreakhub': 48, 'validation': 61}, 1239958 characters. In-scope sample mislabel rate 0.3333 (Wilson 95% [0.1518, 0.5829]); estimated mislabels in scope (low, point, high): [83, 183, 320].

## Proposed exclusions (not applied)

174 rows marked CONFIRMED_MISLABEL; 13 AMBIGUOUS rows kept for an owner decision. IDs are listed in the JSON report.

| Split | Group | Current | After exclusions |
|---|---|---|---|
| test_jailbreakhub | jailbreakhub/label=0 | 1314 | 1302 |
| test_jailbreakhub | jailbreakhub/label=1 | 125 | 125 |
| test_jailbreakhub | wildguardmix/label=0 | 10 | 10 |
| test_official | wildguardmix/label=0 | 915 | 915 |
| test_official | wildguardmix/label=1 | 810 | 810 |
| train | jailbreakhub/label=0 | 10413 | 10272 |
| train | jailbreakhub/label=1 | 1050 | 1045 |
| train | wildguardmix/label=0 | 22397 | 22397 |
| train | wildguardmix/label=1 | 20606 | 20606 |
| validation | jailbreakhub/label=0 | 1318 | 1302 |
| validation | jailbreakhub/label=1 | 129 | 129 |
| validation | wildguardmix/label=0 | 2477 | 2477 |
| validation | wildguardmix/label=1 | 2290 | 2290 |
