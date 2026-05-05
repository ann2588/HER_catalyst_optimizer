import os
import sys
import json
import random
import warnings
import tempfile
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import math
import numpy as np

OFFLINE_PLOT = True
DATA_DIR = "Figures_SI/Fig_alg_efficiency"

# Compatibility patch for old Dragonfly code
if not hasattr(np, "math"):
    np.math = math
if not hasattr(np, "int"):
    np.int = int
if not hasattr(np, "float"):
    np.float = float
if not hasattr(np, "bool"):
    np.bool = bool

from sklearn.ensemble import RandomForestRegressor

# =========================
# PATH SETUP
# =========================
SCRIPT_DIR = os.path.dirname(__file__)
SCRIPTS_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
UTIL_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "utils"))
sys.path.append(SCRIPTS_ROOT)
sys.path.append(UTIL_ROOT)

from registry import get_data_path

# Optional: your original bandit import
# from LQV4_forpost import LQBandit

FIGURE_METADATA = {
    "stable_id": "Fig_alg_efficiency",
    "script": __file__,
    "data_keys": ["Campaign1","Campaign2","Campaign3","Campaign4", "result_pretrain"],
    "figure_type": "Main"
}


def get_output_dir(meta):
    base = os.path.dirname(__file__)
    fig_base = "Figures_SI" if meta["figure_type"] == "SI" else "Figures_Main"
    outdir = os.path.join(base, "..", "..", "..", fig_base, meta["stable_id"])
    os.makedirs(outdir, exist_ok=True)
    return outdir


OUTPUT_DIR = get_output_dir(FIGURE_METADATA)
os.makedirs(OUTPUT_DIR, exist_ok=True)

DATA_DICT = {k: get_data_path(k) for k in FIGURE_METADATA["data_keys"]}

PRETRAIN_FILE = DATA_DICT["result_pretrain"]
CAMPAIGN1_FILE = DATA_DICT["Campaign1"]
CAMPAIGN2_FILE = DATA_DICT["Campaign2"]
CAMPAIGN3_FILE = DATA_DICT["Campaign3"]
CAMPAIGN4_FILE = DATA_DICT["Campaign4"]

# =========================
# USER CONFIG
# =========================
OBJECTIVE_COLUMN = "Overpotential V at 50.0 mA cm-2"

# Harmonised feature order used everywhere
FEATURE_COLS = [
    "V", "Cr", "Fe", "Co", "Ni", "Cu", "Mg", "S", "Se", "P", "Volt", "Time"
]

# Campaign split
PRETRAIN_EXP_MAX = 600

# Dragonfly settings
N_BO_RUNS = 10
BO_BUDGET = 120
BO_RANDOM_SEED = 42

# Digital twin settings
RF_N_ESTIMATORS = 500
RF_RANDOM_STATE = 42

# Plot options
SHOW_INDIVIDUAL_BO_RUNS = False


# =========================
# DRAGONFLY IMPORT
# =========================
try:
    from dragonfly import maximise_function
except Exception as e:
    raise ImportError(
        "Dragonfly is not available in this environment. "
        "Please install Dragonfly in your local venv first, then rerun this script."
    ) from e


# =========================
# HELPERS
# =========================
def parse_exp_number(exp_label):
    """
    'exp601' -> 601
    """
    s = str(exp_label).strip().lower().replace("experiment", "").replace("exp", "")
    try:
        return int(s)
    except Exception:
        return np.nan


def harmonise_columns(df):
    """
    Standardise the order of composition/process columns across files.
    Campaign files and pretrain files do not share the same raw column order.
    """
    missing = [c for c in FEATURE_COLS + [OBJECTIVE_COLUMN, "Experiment"] if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in dataframe: {missing}")

    out = df.copy()
    out["exp_num"] = out["Experiment"].apply(parse_exp_number)
    return out


def load_all_data():
    df_pre = harmonise_columns(pd.read_csv(PRETRAIN_FILE))
    df_c1 = harmonise_columns(pd.read_csv(CAMPAIGN1_FILE))
    df_c2 = harmonise_columns(pd.read_csv(CAMPAIGN2_FILE))
    df_c3 = harmonise_columns(pd.read_csv(CAMPAIGN3_FILE))
    df_c4 = harmonise_columns(pd.read_csv(CAMPAIGN4_FILE))

    return df_pre, df_c1, df_c2, df_c3, df_c4


def build_training_table(df_pre, df_c1, df_c3):
    """
    Use all available observed data or DoE data to build a digital twin.
    Drop rows with missing objective.
    """
    #df_all = pd.concat([df_pre, df_c1, df_c3], ignore_index=True)
    df_all = pd.concat([df_pre], ignore_index=True)

    cols_needed = FEATURE_COLS + [OBJECTIVE_COLUMN]
    df_all = df_all[cols_needed].copy()
    df_all = df_all.dropna(subset=[OBJECTIVE_COLUMN])

    return df_all


def build_digital_twin(df_train):
    X = df_train[FEATURE_COLS].copy()
    y = df_train[OBJECTIVE_COLUMN].astype(float).values

    model = RandomForestRegressor(
        n_estimators=RF_N_ESTIMATORS,
        random_state=RF_RANDOM_STATE,
        n_jobs=-1
    )
    model.fit(X, y)
    return model


def oracle_predict(model, x):
    """
    x: 1D array/list in FEATURE_COLS order
    """
    x_df = pd.DataFrame([np.array(x, dtype=float)], columns=FEATURE_COLS)
    return float(model.predict(x_df)[0])


def compute_best_so_far(series):
    arr = np.asarray(series, dtype=float)
    return np.maximum.accumulate(arr)


def get_actual_campaign_curve(df_campaign, pretrain_exp_max=PRETRAIN_EXP_MAX):
    """
    Extract the *actual* trial-efficiency curve from the real campaign.
    No simplified bandit reimplementation here.
    """
    df = df_campaign.copy()
    df = df.dropna(subset=[OBJECTIVE_COLUMN, "exp_num"])
    df = df[df["exp_num"] > pretrain_exp_max].copy()
    df = df.sort_values("exp_num")

    y = df[OBJECTIVE_COLUMN].astype(float).values
    best = compute_best_so_far(y)

    out = df[["Experiment", "exp_num"] + FEATURE_COLS + [OBJECTIVE_COLUMN]].copy()
    out["best_so_far"] = best
    return out


# =========================
# FEASIBLE DOMAIN FOR DRAGONFLY
# =========================
def round_design(x):
    """
    Discretisation matched to LQBandit:
    - 10 composition dimensions: integer
    - Volt: 0.1
    - Time: integer
    """
    x = np.array(x, dtype=float).copy()
    x[:10] = np.round(x[:10])
    x[10] = np.round(x[10] / 0.1) * 0.1
    x[11] = np.round(x[11])
    return x


def clip_design(x):
    x = np.array(x, dtype=float).copy()
    x[:10] = np.clip(x[:10], 0, 70)
    x[10] = np.clip(x[10], -1.5, -1.0)
    x[11] = np.clip(x[11], 30, 180)
    return x


def enforce_total_loading_constraint(x, max_total=70):
    """
    Match the main linear constraint in your original bandit:
    sum(first 10 dimensions) <= 70
    """
    x = np.array(x, dtype=float).copy()
    total = np.sum(x[:10])
    if total <= max_total:
        return x

    if total <= 0:
        return x

    scaled = x[:10] * (max_total / total)
    x[:10] = scaled
    x = round_design(x)
    x = clip_design(x)

    # after rounding, still possible to exceed 70 by a little
    while np.sum(x[:10]) > max_total:
        pos_idx = np.where(x[:10] > 0)[0]
        if len(pos_idx) == 0:
            break
        j = int(np.argmax(x[:10]))
        x[j] -= 1

    return x


def project_to_feasible_design(x):
    x = np.array(x, dtype=float).copy()
    x = clip_design(x)
    x = round_design(x)
    x = enforce_total_loading_constraint(x, max_total=70)
    x = clip_design(x)
    return x


def sample_random_feasible_point(rng):
    metals = rng.uniform(0, 1, size=10)
    metals = metals / metals.sum()
    total = rng.uniform(0, 70)
    metals = metals * total

    volt = rng.uniform(-1.5, -1.0)
    time = rng.uniform(30, 180)

    x = np.concatenate([metals, [volt, time]])
    x = project_to_feasible_design(x)
    return x


# =========================
# DRAGONFLY OBJECTIVE
# =========================
class DragonflyObjective:
    def __init__(self, twin_model):
        self.twin_model = twin_model
        self.evaluated_points = []
        self.evaluated_vals = []

    def __call__(self, x):
        """
        Dragonfly proposes a point in the box domain.
        We project it back to the physically allowed / discretised domain
        before querying the digital twin.
        """
        x_proj = project_to_feasible_design(np.array(x, dtype=float))
        y = oracle_predict(self.twin_model, x_proj)

        self.evaluated_points.append(x_proj.copy())
        self.evaluated_vals.append(y)
        return y


def run_dragonfly_once(twin_model, budget, seed):
    """
    Dragonfly BO on the digital twin.
    Domain is a 12D Euclidean box.
    Constraint handling is done by projection inside the objective.
    """
    np.random.seed(seed)
    random.seed(seed)

    objective = DragonflyObjective(twin_model)

    domain = (
        [[0.0, 70.0]] * 10
        + [[-1.5, -1.0]]
        + [[30.0, 180.0]]
    )

    # Dragonfly minimisation
    max_val, max_pt, history = maximise_function(
        objective,
        domain,
        budget,
        reporter='silent'
    )

    # Use the actual evaluated values after projection, not raw Dragonfly history
    vals = np.array(objective.evaluated_vals, dtype=float)
    best = compute_best_so_far(vals)

    out = pd.DataFrame(objective.evaluated_points, columns=FEATURE_COLS)
    out["objective"] = vals
    out["best_so_far"] = best
    out["run"] = seed
    return out, max_val, max_pt, history


def run_dragonfly_replicates(twin_model, budget=BO_BUDGET, n_runs=N_BO_RUNS, seed0=BO_RANDOM_SEED):
    runs = []
    for i in range(n_runs):
        seed = seed0 + i
        print(f"Dragonfly run {i+1}/{n_runs} (seed={seed})")
        run_df, _, _, _ = run_dragonfly_once(twin_model, budget, seed)
        run_df["iteration"] = np.arange(1, len(run_df) + 1)
        runs.append(run_df)
    return pd.concat(runs, ignore_index=True)


# =========================
# OPTIONAL: compare by matched budget
# =========================
def truncate_curve_to_budget(curve_df, budget):
    out = curve_df.copy().iloc[:budget].copy()
    return out


def summarise_bo_curves(df_bo_runs):
    """
    df_bo_runs columns: run, iteration, best_so_far
    """
    piv = df_bo_runs.pivot(index="iteration", columns="run", values="best_so_far")
    summary = pd.DataFrame({
        "iteration": piv.index,
        "mean": piv.mean(axis=1).values,
        "std": piv.std(axis=1).values,
        "min": piv.min(axis=1).values,
        "max": piv.max(axis=1).values,
    })
    return summary


# =========================
# PLOTTING
# =========================
def make_main_plot(c1_curve, c2_curve, c3_curve, c4_curve, bo_summary, bo_runs=None):
    fig, ax = plt.subplots(figsize=(2.2, 1.8))
    plt.rcParams["font.family"] = "Arial"
    ax.tick_params(
        axis='both',
        width=0.5,   # tick line width
        length=3     # optional: tick 長度
    )

    for spine in ['top', 'bottom', 'left', 'right']:
        ax.spines[spine].set_linewidth(0.5)

    
    ax.plot(
        np.arange(1, len(c1_curve) + 1),
        c1_curve["best_so_far"].values,
        linewidth=2,
        color = "blue",
        label="Campaign 1"
    )
    ax.plot(
        np.arange(1, len(c2_curve) + 1),
        c2_curve["best_so_far"].values,
        linewidth=2,
        color = "orange",
        label="Campaign 2"
    )
    ax.plot(
        np.arange(1, len(c3_curve) + 1),
        c3_curve["best_so_far"].values,
        linewidth=2,
        color = "green",
        label="Campaign 3"
    )
    ax.plot(
        np.arange(1, len(c4_curve) + 1),
        c4_curve["best_so_far"].values,
        linewidth=2,
        color = "purple",
        label="Campaign 4"
    )

    ax.plot(
        bo_summary["iteration"].values,
        bo_summary["mean"].values,
        linewidth=2,
        color = "black", 
        label="Dragonfly BO (mean)"
    )
    ax.fill_between(
        bo_summary["iteration"].values,
        bo_summary["mean"].values - bo_summary["std"].values,
        bo_summary["mean"].values + bo_summary["std"].values,
        alpha=0.2
    )

    if SHOW_INDIVIDUAL_BO_RUNS and bo_runs is not None:
        for run_id, sub in bo_runs.groupby("run"):
            ax.plot(
                sub["iteration"].values,
                sub["best_so_far"].values,
                linewidth=1.0,
                alpha=0.35
            )

    ax.set_xlabel("Trial index", fontsize = 7)
    ax.tick_params(axis='both', labelsize=6)
    ax.set_ylim([-1.0, 0])
    ax.set_ylabel("Best-so-far $η_{50}$ (V)", fontsize = 7)
    ax.legend(frameon=False, fontsize = 6)
    fig.tight_layout()

    fig.savefig(os.path.join(OUTPUT_DIR, "Fig_alg_efficiency_main.svg"))
    plt.close(fig)

def load_processed_data():
    c1 = pd.read_csv(os.path.join(DATA_DIR, "campaign1_actual_bandit_curve.csv"))
    c2 = pd.read_csv(os.path.join(DATA_DIR, "campaign2_actual_bandit_curve.csv"))
    c3 = pd.read_csv(os.path.join(DATA_DIR, "campaign3_actual_bandit_curve.csv"))
    c4 = pd.read_csv(os.path.join(DATA_DIR, "campaign4_actual_bandit_curve.csv"))
    bo_summary = pd.read_csv(os.path.join(DATA_DIR, "dragonfly_bo_summary.csv"))

    bo_runs_path = os.path.join(DATA_DIR, "dragonfly_bo_runs.csv")
    bo_runs = pd.read_csv(bo_runs_path) if os.path.exists(bo_runs_path) else None

    return c1, c2, c3,c4, bo_summary, bo_runs

# =========================
# MAIN
# =========================
def main():
    import time
    start = time.time()
    
    warnings.filterwarnings("ignore")

    # Load
    df_pre, df_c1, df_c2, df_c3, df_c4 = load_all_data()

    # Build digital twin
    df_train = build_training_table(df_pre, df_c1, df_c3)
    twin_model = build_digital_twin(df_train)

    # Actual campaign curves = actual bandit efficiency
    c1_curve = get_actual_campaign_curve(df_c1, PRETRAIN_EXP_MAX)
    c2_curve = get_actual_campaign_curve(df_c2, PRETRAIN_EXP_MAX)
    c3_curve = get_actual_campaign_curve(df_c3, PRETRAIN_EXP_MAX)
    c4_curve = get_actual_campaign_curve(df_c4, PRETRAIN_EXP_MAX)

    # Match budget if desired
    matched_budget = min(BO_BUDGET, len(c1_curve), len(c2_curve), len(c3_curve), len(c4_curve))
    c1_curve = truncate_curve_to_budget(c1_curve, matched_budget)
    c2_curve = truncate_curve_to_budget(c2_curve, matched_budget)
    c3_curve = truncate_curve_to_budget(c3_curve, matched_budget)
    c4_curve = truncate_curve_to_budget(c4_curve, matched_budget)

    print(f"Matched budget = {matched_budget}")
    print(f"Campaign1 adaptive trials used = {len(c1_curve)}")
    print(f"Campaign2 adaptive trials used = {len(c2_curve)}")
    print(f"Campaign3 adaptive trials used = {len(c3_curve)}")
    print(f"Campaign2 adaptive trials used = {len(c4_curve)}")
    
    #Test run time
    #run_df, _, _, _ = run_dragonfly_once(twin_model, matched_budget, 42)
    #print(f"One run time: {time.time() - start:.2f} sec")

    # Dragonfly BO
    #bo_runs = run_dragonfly_replicates(
    #    twin_model,
    #    budget=matched_budget,
    #    n_runs=N_BO_RUNS,
    #    seed0=BO_RANDOM_SEED
    
    #bo_summary = summarise_bo_curves(bo_runs)
    

    # Save raw outputs
    c1_curve.to_csv(os.path.join(OUTPUT_DIR, "campaign1_actual_bandit_curve.csv"), index=False)
    c2_curve.to_csv(os.path.join(OUTPUT_DIR, "campaign2_actual_bandit_curve.csv"), index=False)
    c3_curve.to_csv(os.path.join(OUTPUT_DIR, "campaign3_actual_bandit_curve.csv"), index=False)
    c4_curve.to_csv(os.path.join(OUTPUT_DIR, "campaign4_actual_bandit_curve.csv"), index=False)
    #bo_runs.to_csv(os.path.join(OUTPUT_DIR, "dragonfly_bo_runs.csv"), index=False)
    #bo_summary.to_csv(os.path.join(OUTPUT_DIR, "dragonfly_bo_summary.csv"), index=False)

    summary = {
        "matched_budget": int(matched_budget),
        "campaign1_final_best": float(c1_curve["best_so_far"].iloc[-1]),
        "campaign2_final_best": float(c2_curve["best_so_far"].iloc[-1]),
        "campaign3_final_best": float(c3_curve["best_so_far"].iloc[-1]),
        "campaign4_final_best": float(c4_curve["best_so_far"].iloc[-1]),
        "dragonfly_final_mean_best": float(bo_summary["mean"].iloc[-1]),
        "dragonfly_final_std_best": float(bo_summary["std"].iloc[-1]),
        "n_bo_runs": int(N_BO_RUNS),
    }
    with open(os.path.join(OUTPUT_DIR, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    # Plot
    make_main_plot(c1_curve, c2_curve,  c3_curve, c4_curve,bo_summary, bo_runs)

    print("Done.")
    print(f"Outputs saved to: {OUTPUT_DIR}")


if __name__ == "__main__":

    if OFFLINE_PLOT:
        print("Running in OFFLINE PLOT mode...")
        c1, c2, c3,c4, bo_summary, bo_runs = load_processed_data()
        make_main_plot(c1, c2, c3,c4, bo_summary, bo_runs)

    else:
        print("Running FULL pipeline...")
        main()