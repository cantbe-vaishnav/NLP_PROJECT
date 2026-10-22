"""Shared figure styling for the Task A analysis notebooks (colors, model names, Matplotlib defaults)."""

import matplotlib as mpl
from matplotlib.colors import LinearSegmentedColormap

# Display names and fixed colors per model; a model keeps its color in every figure.
MODEL_LABELS = {"LogReg": "TF-IDF + LogReg", "SVM": "TF-IDF + Linear SVM",
                "DistilBERT": "DistilBERT-256", "DistilBERT-512": "DistilBERT-512"}
MODEL_COLORS = {"LogReg": "#2a78d6", "SVM": "#eb6834", "DistilBERT": "#1baf7a", "DistilBERT-512": "#eda100"}

# Colors for evaluation splits (validation vs the two test sets) and for highlighting errors.
SPLIT_COLORS = {"validation": "#1baf7a", "test_official": "#2a78d6", "test_jailbreakhub": "#eb6834"}
ERROR_COLOR = "#e34948"
TEXT_SECONDARY = "#52514e"

# One-hue sequential ramp (light -> dark blue) for heatmaps such as confusion matrices.
SEQUENTIAL = LinearSegmentedColormap.from_list("task_a_blue", ["#f4f8fd", "#9ec5f4", "#3987e5", "#1c5cab", "#0d366b"])


# Recessive grid and axes, readable font sizes, white background (also in saved PNGs).
STYLE = {
    "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
    "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": "#b5b4ad",
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": "#e6e5e0", "grid.linewidth": 0.8,
    "axes.axisbelow": True, "axes.titlesize": 11, "axes.titleweight": "bold", "axes.labelsize": 10,
    "xtick.labelsize": 9, "ytick.labelsize": 9, "legend.fontsize": 9, "legend.frameon": False,
    "figure.titlesize": 12, "figure.titleweight": "bold", "figure.dpi": 100,
}


def apply_style():
    """Apply STYLE to Matplotlib; returns the previous values so a caller can restore them."""
    previous = {key: mpl.rcParams[key] for key in STYLE}
    mpl.rcParams.update(STYLE)
    return previous
