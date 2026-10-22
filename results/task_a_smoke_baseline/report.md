# Task A TF-IDF + LogReg smoke test

**SMOKE TEST ONLY: pipeline validation on a tiny, unadjudicated pilot subset. Not a research result; no held-out test set; no claim of generalization.**

Items: 112 unanimous pilot items; labels {'BENIGN': 76, 'HARMFUL': 20, 'ADVERSARIAL': 16, 'QUARANTINE': 0}.
Absent classes (no items, no metrics): QUARANTINE.
Evaluation: 5-fold grouped, stratified out-of-fold; 111 duplicate groups (1 with more than one member).

| Class | Support | Precision | Recall | F1 |
|---|---|---|---|---|
| BENIGN | 76 | 0.800 | 0.842 | 0.821 |
| HARMFUL | 20 | 0.875 | 0.350 | 0.500 |
| ADVERSARIAL | 16 | 0.542 | 0.812 | 0.650 |
| QUARANTINE | 0 | n/a (absent) | n/a (absent) | n/a (absent) |

Macro-F1 over BENIGN, HARMFUL, ADVERSARIAL: 0.657 (majority-class reference BENIGN: 0.270).
Accuracy: 0.750.

Confusion matrix (rows gold, columns predicted; order BENIGN, HARMFUL, ADVERSARIAL, QUARANTINE):

- BENIGN: 64, 1, 11, 0
- HARMFUL: 13, 7, 0, 0
- ADVERSARIAL: 3, 0, 13, 0
- QUARANTINE: 0, 0, 0, 0
