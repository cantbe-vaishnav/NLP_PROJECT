# Experiment notebooks

Experiments and their explanations live here as Jupyter notebooks. Data preparation,
validation and shared training/evaluation code stay in `src/task_a/` and `scripts/`, and
the notebooks import them instead of copying logic.

| Notebook | Purpose |
|---|---|
| `task_a_binary_tfidf_baseline_v2.ipynb` | RQ1 baseline: TF-IDF + Logistic Regression on binary jailbreak dataset v2 |
| `task_a_binary_tfidf_linear_svm_v2.ipynb` | RQ1 comparison: TF-IDF + Linear SVM, same features and splits |
| `task_a_binary_distilbert_v2.ipynb` | RQ1 comparison: fine-tuned DistilBERT; also writes a three-model test comparison |
| `task_a_binary_distilbert_512_v2.ipynb` | Truncation experiment: DistilBERT with 512-token inputs vs the 256-token run (length chosen on validation) |
| `task_a_error_analysis_v2.ipynb` | Descriptive error analysis of the saved test predictions of all three models (no training) |
| `task_b_fever_baselines.ipynb` | Task B first baselines (majority, claim-only, embedding similarity); needs the data in `docs/task_b_plan.md` |
| `templates/task_a_experiment_template.ipynb` | Section skeleton for new experiments (e.g. a transformer classifier) |

Conventions for new experiments:

- Name notebooks `task_a_<model>_<dataset_version>.ipynb`. Put settings in `configs/<experiment>.json`.
- Resolve paths from the repository root (the first code cell does this), so the notebook
  runs from any working directory.
- Select hyperparameters or checkpoints on validation only, then score test splits once.
  Report `test_official` and `test_jailbreakhub` separately.
- State label provenance: reviewed corrections are not human-verified labels.
- Write each run to a new `results/<experiment>/<run_id>/` directory. Predictions and model
  files are Git-ignored.
- Never display prompt text in notebook outputs; show counts and metrics only.

Run or open:

```bash
python -m jupyter nbconvert --to notebook --execute --inplace notebooks/task_a_binary_tfidf_baseline_v2.ipynb
code notebooks/task_a_binary_tfidf_baseline_v2.ipynb   # VS Code with the Jupyter extension
```

Use an interpreter that has pyarrow, pandas, scikit-learn, matplotlib, joblib and ipykernel
(the project venv currently lacks scikit-learn; the system Python 3.11 has it).
