# Archived: early Task B scaffold (2026-10-22)

Untracked files from the `task-a-binary-dataset` worktree, moved here unchanged (MD5 checked) during
repository consolidation so they could not block the Task B merge. Superseded by the Task B branch
(`src/task_b/schema.py`, `src/task_b/fever.py`, `notebooks/task_b_fever_baselines.ipynb`,
`docs/task_b_implementation.md`). Never run; no results depend on them.

Folder layout mirrors the original paths. `tests/test_task_b_data.py` imports `task_b.data`, which no
longer exists on the import path, so it is outside `tests/` and not collected by test discovery.
