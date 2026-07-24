import json
import os
import re
import warnings
from pathlib import Path

import numpy as np
import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[2]

FIGURE_METADATA = {
    "stable_id": "Fig_alg_uncertainty_sens",
    "script": __file__,
    "data_keys": [
        "result_pretrain",
        "Campaign1",
        "Campaign2",
        "Campaign3",
        "Campaign4",
    ],
    "figure_type": "SI",
}


def get_output_dir(meta: dict[str, object]) -> Path:
    fig_base = "Figures_SI" if meta["figure_type"] == "SI" else "Figures_Main"
    outdir = PROJECT_ROOT / fig_base / str(meta["stable_id"])
    outdir.mkdir(parents=True, exist_ok=True)
    return outdir


DATA_DIR = PROJECT_ROOT / "Data"
ALG_EFFICIENCY_DIR = PROJECT_ROOT / "Figures_Main" / "Fig_alg_efficiency"
OUTPUT_DIR = get_output_dir(FIGURE_METADATA)
OUTPUT_FORMATS = ("png", "eps")

MPL_CACHE_DIR = Path("/tmp/her-catalyst-optimizer-mpl-cache")
MPL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MPL_CACHE_DIR))
os.environ.setdefault("XDG_CACHE_HOME", str(MPL_CACHE_DIR))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib import colors as mcolors
from sklearn.ensemble import RandomForestRegressor
from scipy.linalg import cho_factor, cho_solve
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern
from sklearn.preprocessing import PolynomialFeatures, StandardScaler


FEATURE_COLS = ["V", "Cr", "Fe", "Co", "Ni", "Cu", "Mg", "S", "Se", "P", "Volt", "Time"]
OBJECTIVE_COL = "Overpotential V at 50.0 mA cm-2"
NOISE_LEVELS_MV = [10, 25, 50, 100, 250]
BUDGET = 112
UCB_KAPPA = 2.0
MIN_SIGMA_V = 1e-4
FRAME_WIDTH = 0.5
CAMPAIGNS = ["Campaign1", "Campaign2", "Campaign3", "Campaign4"]
DRAGONFLY_STYLE_BO_RUNS = 10
DRAGONFLY_STYLE_BO_SEED = 42
DRAGONFLY_STYLE_POOL_SIZE = 1000
DRAGONFLY_STYLE_INITIAL_RANDOM = 5
RF_N_ESTIMATORS = 500
RF_RANDOM_STATE = 42
ALG_EFFICIENCY_COLORS = {
    "Campaign1": "blue",
    "Campaign2": "orange",
    "Campaign3": "green",
    "Campaign4": "purple",
}
NOISE_LIGHTNESS = {
    noise_mV: lightness
    for noise_mV, lightness in zip(
        sorted(NOISE_LEVELS_MV),
        np.linspace(0.70, 0.04, len(NOISE_LEVELS_MV)),
    )
}


plt.rcParams.update(
    {
        "font.family": "Arial",
        "font.size": 12,
        "axes.linewidth": FRAME_WIDTH,
        "xtick.major.width": FRAME_WIDTH,
        "ytick.major.width": FRAME_WIDTH,
        "savefig.dpi": 600,
    }
)


def parse_exp_number(value: object) -> int:
    match = re.search(r"(\d+)", str(value))
    return int(match.group(1)) if match else 10**9


def shade_for_noise(base_color: str, noise_mV: int) -> tuple[float, float, float]:
    base = np.array(mcolors.to_rgb(base_color))
    white = np.ones(3)
    noise_mV = int(noise_mV)
    if noise_mV in NOISE_LIGHTNESS:
        lightness = NOISE_LIGHTNESS[noise_mV]
    else:
        known_noise = np.array(sorted(NOISE_LIGHTNESS), dtype=float)
        known_lightness = np.array([NOISE_LIGHTNESS[int(noise)] for noise in known_noise])
        lightness = float(np.interp(noise_mV, known_noise, known_lightness))
    return tuple(base * (1 - lightness) + white * lightness)


def load_table(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["Experiment"] = df["Experiment"].astype(str).str.lower()
    df["exp_num"] = df["Experiment"].map(parse_exp_number)
    missing = [col for col in ["Experiment", *FEATURE_COLS, OBJECTIVE_COL] if col not in df.columns]
    if missing:
        raise ValueError(f"{path} is missing columns: {missing}")
    return df


def load_experimental_landscapes() -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    pretrain = load_table(DATA_DIR / "result_pretrain.csv").dropna(subset=[OBJECTIVE_COL])

    campaign_candidates = {}
    for campaign_id in range(1, 5):
        campaign = f"Campaign{campaign_id}"
        path = DATA_DIR / f"Campaign{campaign_id}.csv"
        df = load_table(path)
        df = df[df["exp_num"] > 600].copy()
        df = df.dropna(subset=[OBJECTIVE_COL])
        df = df.drop_duplicates(subset=["Experiment"], keep="first")
        df = df.sort_values("exp_num").reset_index(drop=True)
        df["campaign"] = campaign
        campaign_candidates[campaign] = df

    return pretrain.reset_index(drop=True), campaign_candidates


def standardize_objective(y: np.ndarray, mean: float, std: float) -> np.ndarray:
    return (np.asarray(y, dtype=float) - mean) / std


def unstandardize_objective(y_scaled: np.ndarray, mean: float, std: float) -> np.ndarray:
    return np.asarray(y_scaled, dtype=float) * std + mean


def compute_best_so_far(values: list[float]) -> list[float]:
    return np.maximum.accumulate(np.asarray(values, dtype=float)).tolist()


def fit_lq_posterior(phi_train: np.ndarray, y_train: np.ndarray, sigma_scaled: float):
    noise_var = sigma_scaled**2
    prior_precision = 1.0
    precision = prior_precision * np.eye(phi_train.shape[1]) + (phi_train.T @ phi_train) / noise_var
    cho = cho_factor(precision, lower=True, check_finite=False)
    theta = cho_solve(cho, (phi_train.T @ y_train) / noise_var, check_finite=False)
    return theta, cho


def run_lq_ucb(
    pretrain: pd.DataFrame,
    candidates: pd.DataFrame,
    sigma_v: float,
    campaign: str,
    budget: int = BUDGET,
) -> pd.DataFrame:
    scaler = StandardScaler().fit(pretrain[FEATURE_COLS])
    poly = PolynomialFeatures(degree=2, include_bias=True).fit(scaler.transform(pretrain[FEATURE_COLS]))

    x_train = poly.transform(scaler.transform(pretrain[FEATURE_COLS]))
    x_candidate_all = poly.transform(scaler.transform(candidates[FEATURE_COLS]))

    y_pre = pretrain[OBJECTIVE_COL].astype(float).to_numpy()
    y_mean = float(y_pre.mean())
    y_std = float(y_pre.std())
    y_train = standardize_objective(y_pre, y_mean, y_std)

    sigma_scaled = max(sigma_v, MIN_SIGMA_V) / y_std
    remaining = np.arange(len(candidates))
    selected_values: list[float] = []
    records = []

    for iteration in range(1, min(budget, len(remaining)) + 1):
        theta, cho = fit_lq_posterior(x_train, y_train, sigma_scaled)
        x_remaining = x_candidate_all[remaining]
        mu_scaled = x_remaining @ theta
        cov_times_phi = cho_solve(cho, x_remaining.T, check_finite=False)
        std_scaled = np.sqrt(np.maximum(np.sum(x_remaining * cov_times_phi.T, axis=1), 0.0)) * sigma_scaled
        acquisition = mu_scaled + UCB_KAPPA * std_scaled

        local_idx = int(np.argmax(acquisition))
        candidate_idx = int(remaining[local_idx])
        row = candidates.iloc[candidate_idx]
        objective = float(row[OBJECTIVE_COL])
        selected_values.append(objective)

        records.append(
            {
                "campaign": campaign,
                "algorithm": "LQ bandit",
                "noise_mV": int(round(sigma_v * 1000)),
                "iteration": iteration,
                "Experiment": row["Experiment"],
                "objective_V": objective,
                "predicted_mean_V": float(unstandardize_objective(mu_scaled[local_idx], y_mean, y_std)),
                "predicted_std_V": float(std_scaled[local_idx] * y_std),
                "acquisition_scaled": float(acquisition[local_idx]),
                "best_so_far_V": float(max(selected_values)),
            }
        )

        x_train = np.vstack([x_train, x_candidate_all[candidate_idx]])
        y_train = np.append(y_train, standardize_objective([objective], y_mean, y_std)[0])
        remaining = np.delete(remaining, local_idx)

    return pd.DataFrame(records)


def run_gp_bo(
    pretrain: pd.DataFrame,
    candidates: pd.DataFrame,
    sigma_v: float,
    campaign: str,
    budget: int = BUDGET,
) -> pd.DataFrame:
    scaler = StandardScaler().fit(pretrain[FEATURE_COLS])
    x_train = scaler.transform(pretrain[FEATURE_COLS])
    x_candidate_all = scaler.transform(candidates[FEATURE_COLS])

    y_pre = pretrain[OBJECTIVE_COL].astype(float).to_numpy()
    y_mean = float(y_pre.mean())
    y_std = float(y_pre.std())
    y_train = standardize_objective(y_pre, y_mean, y_std)

    alpha = max((sigma_v / y_std) ** 2, (MIN_SIGMA_V / y_std) ** 2)
    kernel = ConstantKernel(1.0, constant_value_bounds="fixed") * Matern(
        length_scale=np.ones(len(FEATURE_COLS)),
        length_scale_bounds="fixed",
        nu=2.5,
    )

    remaining = np.arange(len(candidates))
    selected_values: list[float] = []
    records = []

    for iteration in range(1, min(budget, len(remaining)) + 1):
        model = GaussianProcessRegressor(
            kernel=kernel,
            alpha=alpha,
            optimizer=None,
            normalize_y=False,
            copy_X_train=False,
            random_state=0,
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model.fit(x_train, y_train)

        x_remaining = x_candidate_all[remaining]
        mu_scaled, std_scaled = model.predict(x_remaining, return_std=True)
        acquisition = mu_scaled + UCB_KAPPA * std_scaled

        local_idx = int(np.argmax(acquisition))
        candidate_idx = int(remaining[local_idx])
        row = candidates.iloc[candidate_idx]
        objective = float(row[OBJECTIVE_COL])
        selected_values.append(objective)

        records.append(
            {
                "campaign": campaign,
                "algorithm": "GP BO",
                "noise_mV": int(round(sigma_v * 1000)),
                "iteration": iteration,
                "Experiment": row["Experiment"],
                "objective_V": objective,
                "predicted_mean_V": float(unstandardize_objective(mu_scaled[local_idx], y_mean, y_std)),
                "predicted_std_V": float(std_scaled[local_idx] * y_std),
                "acquisition_scaled": float(acquisition[local_idx]),
                "best_so_far_V": float(max(selected_values)),
            }
        )

        x_train = np.vstack([x_train, x_candidate_all[candidate_idx]])
        y_train = np.append(y_train, standardize_objective([objective], y_mean, y_std)[0])
        remaining = np.delete(remaining, local_idx)

    return pd.DataFrame(records)


def build_digital_twin(pretrain: pd.DataFrame) -> RandomForestRegressor:
    df_train = pretrain.dropna(subset=[*FEATURE_COLS, OBJECTIVE_COL]).copy()
    model = RandomForestRegressor(
        n_estimators=RF_N_ESTIMATORS,
        random_state=RF_RANDOM_STATE,
        n_jobs=-1,
    )
    model.fit(df_train[FEATURE_COLS], df_train[OBJECTIVE_COL].astype(float))
    return model


def round_design(x: np.ndarray) -> np.ndarray:
    x = np.array(x, dtype=float).copy()
    x[:10] = np.round(x[:10])
    x[10] = np.round(x[10] / 0.1) * 0.1
    x[11] = np.round(x[11])
    return x


def clip_design(x: np.ndarray) -> np.ndarray:
    x = np.array(x, dtype=float).copy()
    x[:10] = np.clip(x[:10], 0, 70)
    x[10] = np.clip(x[10], -1.5, -1.0)
    x[11] = np.clip(x[11], 30, 180)
    return x


def enforce_total_loading_constraint(x: np.ndarray, max_total: float = 70) -> np.ndarray:
    x = np.array(x, dtype=float).copy()
    total = float(np.sum(x[:10]))
    if total <= max_total or total <= 0:
        return x

    x[:10] = x[:10] * (max_total / total)
    x = round_design(x)
    x = clip_design(x)

    while np.sum(x[:10]) > max_total:
        positive_idx = np.where(x[:10] > 0)[0]
        if len(positive_idx) == 0:
            break
        x[int(np.argmax(x[:10]))] -= 1

    return x


def project_to_feasible_design(x: np.ndarray) -> np.ndarray:
    x = clip_design(x)
    x = round_design(x)
    x = enforce_total_loading_constraint(x)
    return clip_design(x)


def sample_random_feasible_point(rng: np.random.Generator) -> np.ndarray:
    metals = rng.uniform(0, 1, size=10)
    metals = metals / metals.sum()
    total = rng.uniform(0, 70)
    metals = metals * total
    volt = rng.uniform(-1.5, -1.0)
    time = rng.uniform(30, 180)
    return project_to_feasible_design(np.concatenate([metals, [volt, time]]))


def sample_feasible_pool(rng: np.random.Generator, pool_size: int) -> pd.DataFrame:
    rows = []
    while len(rows) < pool_size:
        rows.append(sample_random_feasible_point(rng))
        if len(rows) % pool_size == 0:
            pool = pd.DataFrame(rows, columns=FEATURE_COLS).drop_duplicates()
            rows = pool.to_numpy().tolist()
    return pd.DataFrame(rows[:pool_size], columns=FEATURE_COLS).drop_duplicates().reset_index(drop=True)


def run_dragonfly_style_bo_once(
    twin_model: RandomForestRegressor,
    sigma_v: float,
    noise_mV: int,
    run_seed: int,
    budget: int = BUDGET,
) -> pd.DataFrame:
    rng = np.random.default_rng(run_seed)
    candidate_pool = sample_feasible_pool(rng, DRAGONFLY_STYLE_POOL_SIZE)
    while len(candidate_pool) < budget:
        extra_pool = sample_feasible_pool(rng, DRAGONFLY_STYLE_POOL_SIZE)
        candidate_pool = (
            pd.concat([candidate_pool, extra_pool], ignore_index=True)
            .drop_duplicates()
            .reset_index(drop=True)
        )

    objective_all = twin_model.predict(candidate_pool[FEATURE_COLS]).astype(float)
    scaler = StandardScaler().fit(candidate_pool[FEATURE_COLS])
    x_all = scaler.transform(candidate_pool[FEATURE_COLS])

    kernel = ConstantKernel(1.0, constant_value_bounds="fixed") * Matern(
        length_scale=np.ones(len(FEATURE_COLS)),
        length_scale_bounds="fixed",
        nu=2.5,
    )

    remaining = np.arange(len(candidate_pool))
    selected_idx: list[int] = []
    selected_values: list[float] = []
    records = []

    for iteration in range(1, min(budget, len(remaining)) + 1):
        predicted_mean = np.nan
        predicted_std = np.nan
        acquisition_value = np.nan

        if iteration <= DRAGONFLY_STYLE_INITIAL_RANDOM:
            local_idx = int(rng.integers(len(remaining)))
        else:
            train_idx = np.array(selected_idx, dtype=int)
            y_obs = objective_all[train_idx]
            y_mean = float(np.mean(y_obs))
            y_std = float(np.std(y_obs))
            if y_std < 1e-12:
                y_std = 1.0

            y_train = standardize_objective(y_obs, y_mean, y_std)
            alpha = max((sigma_v / y_std) ** 2, (MIN_SIGMA_V / y_std) ** 2)
            model = GaussianProcessRegressor(
                kernel=kernel,
                alpha=alpha,
                optimizer=None,
                normalize_y=False,
                copy_X_train=False,
                random_state=run_seed,
            )
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                model.fit(x_all[train_idx], y_train)

            mu_scaled, std_scaled = model.predict(x_all[remaining], return_std=True)
            acquisition = mu_scaled + UCB_KAPPA * std_scaled
            local_idx = int(np.argmax(acquisition))
            predicted_mean = float(unstandardize_objective(mu_scaled[local_idx], y_mean, y_std))
            predicted_std = float(std_scaled[local_idx] * y_std)
            acquisition_value = float(acquisition[local_idx])

        candidate_idx = int(remaining[local_idx])
        objective = float(objective_all[candidate_idx])
        selected_idx.append(candidate_idx)
        selected_values.append(objective)

        row = candidate_pool.iloc[candidate_idx]
        records.append(
            {
                "campaign": "DigitalTwin",
                "algorithm": "Dragonfly-style BO",
                "noise_mV": noise_mV,
                "run": run_seed,
                "iteration": iteration,
                "Experiment": f"bo_seed{run_seed}_iter{iteration}",
                "objective_V": objective,
                "predicted_mean_V": predicted_mean,
                "predicted_std_V": predicted_std,
                "acquisition_scaled": acquisition_value,
                "best_so_far_V": float(max(selected_values)),
                **{col: float(row[col]) for col in FEATURE_COLS},
            }
        )

        remaining = np.delete(remaining, local_idx)

    return pd.DataFrame(records)


def run_dragonfly_style_bo_by_noise(pretrain: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    twin_model = build_digital_twin(pretrain)
    run_frames = []
    for noise_mV in NOISE_LEVELS_MV:
        sigma_v = noise_mV / 1000
        for run_idx in range(DRAGONFLY_STYLE_BO_RUNS):
            seed = DRAGONFLY_STYLE_BO_SEED + run_idx
            print(
                f"Running Dragonfly-style BO, assumed noise={noise_mV} mV, "
                f"run {run_idx + 1}/{DRAGONFLY_STYLE_BO_RUNS}"
            )
            run_frames.append(run_dragonfly_style_bo_once(twin_model, sigma_v, noise_mV, seed))

    runs_df = pd.concat(run_frames, ignore_index=True)
    curve_summary = summarize_bo_runs(runs_df)
    effect_summary = summarize_bo_noise_effect(curve_summary)
    return runs_df, curve_summary, effect_summary


def summarize_bo_runs(runs_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for noise_mV, group in runs_df.groupby("noise_mV"):
        pivot = group.pivot(index="iteration", columns="run", values="best_so_far_V")
        for iteration, row in pivot.sort_index().iterrows():
            rows.append(
                {
                    "noise_mV": int(noise_mV),
                    "iteration": int(iteration),
                    "mean": float(row.mean()),
                    "std": float(row.std()),
                    "min": float(row.min()),
                    "max": float(row.max()),
                }
            )
    return pd.DataFrame(rows).sort_values(["noise_mV", "iteration"]).reset_index(drop=True)


def summarize_bo_noise_effect(curve_summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for noise_mV, group in curve_summary.groupby("noise_mV"):
        group = group.sort_values("iteration")
        rows.append(
            {
                "campaign": "DigitalTwin",
                "algorithm": "Dragonfly-style BO",
                "noise_mV": int(noise_mV),
                "final_best_V": float(group["mean"].iloc[-1]),
                "mean_best_so_far_V": float(group["mean"].mean()),
                "best_experiment": "mean_of_runs",
            }
        )

    summary = pd.DataFrame(rows).sort_values("noise_mV").reset_index(drop=True)
    baseline = summary[summary["noise_mV"] == 50].iloc[0]
    summary["final_delta_vs_50mV_mV"] = (
        summary["final_best_V"] - baseline["final_best_V"]
    ) * 1000
    summary["mean_curve_delta_vs_50mV_mV"] = (
        summary["mean_best_so_far_V"] - baseline["mean_best_so_far_V"]
    ) * 1000
    return summary


def summarize_trajectories(trajectories: pd.DataFrame) -> pd.DataFrame:
    rows = []
    group_cols = ["campaign", "algorithm", "noise_mV"]
    for (campaign, algorithm, noise_mV), group in trajectories.groupby(group_cols):
        group = group.sort_values("iteration")
        final_best = float(group["best_so_far_V"].iloc[-1])
        auc = float(group["best_so_far_V"].mean())
        rows.append(
            {
                "campaign": campaign,
                "algorithm": algorithm,
                "noise_mV": noise_mV,
                "final_best_V": final_best,
                "mean_best_so_far_V": auc,
                "best_experiment": group.loc[group["best_so_far_V"].idxmax(), "Experiment"],
            }
        )

    summary = pd.DataFrame(rows).sort_values(["campaign", "algorithm", "noise_mV"]).reset_index(drop=True)
    comparison = []
    for (campaign, algorithm), group in summary.groupby(["campaign", "algorithm"]):
        baseline = group[group["noise_mV"] == 50].iloc[0]
        for _, row in group.iterrows():
            comparison.append(
                {
                    "campaign": campaign,
                    "algorithm": algorithm,
                    "noise_mV": row["noise_mV"],
                    "final_delta_vs_50mV_mV": (row["final_best_V"] - baseline["final_best_V"]) * 1000,
                    "mean_curve_delta_vs_50mV_mV": (
                        row["mean_best_so_far_V"] - baseline["mean_best_so_far_V"]
                    )
                    * 1000,
                }
            )
    comparison_df = pd.DataFrame(comparison)
    return summary.merge(comparison_df, on=["campaign", "algorithm", "noise_mV"], how="left")


def plot_trajectories(trajectories: pd.DataFrame, bo_curve_summary: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(3.6, 3.6), constrained_layout=True)
    all_y = np.concatenate(
        [
            trajectories["best_so_far_V"].to_numpy(dtype=float),
            bo_curve_summary["mean"].to_numpy(dtype=float),
        ]
    )
    y_min = np.floor((np.nanmin(all_y) - 0.03) / 0.05) * 0.05
    y_max = min(0.02, np.ceil((np.nanmax(all_y) + 0.03) / 0.05) * 0.05)

    for campaign in CAMPAIGNS:
        subset = trajectories[
            (trajectories["campaign"] == campaign)
            & (trajectories["algorithm"] == "LQ bandit")
        ]
        for noise_mV in NOISE_LEVELS_MV:
            group = subset[subset["noise_mV"] == noise_mV]
            if group.empty:
                continue
            group = group.sort_values("iteration")
            ax.plot(
                group["iteration"],
                group["best_so_far_V"],
                color=shade_for_noise(ALG_EFFICIENCY_COLORS[campaign], int(noise_mV)),
                linewidth=1.2,
            )

    for noise_mV in NOISE_LEVELS_MV:
        group = bo_curve_summary[bo_curve_summary["noise_mV"] == noise_mV]
        if group.empty:
            continue
        group = group.sort_values("iteration")
        ax.plot(
            group["iteration"],
            group["mean"],
            color=shade_for_noise("black", int(noise_mV)),
            linewidth=1.4,
        )

    ax.set_xlim(1, BUDGET)
    ax.set_ylim(y_min, y_max)
    ax.set_xlabel("Trial index")
    ax.set_ylabel(r"Best-so-far $\eta_{50}$ (V)")
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_linewidth(FRAME_WIDTH)
    ax.tick_params(width=FRAME_WIDTH, length=3, labelsize=12)

    label_specs = [
        ("C1", "Campaign1", -0.012),
        ("C2", "Campaign2", 0.018),
        ("C3", "Campaign3", 0.000),
        ("C4", "Campaign4", 0.040),
    ]
    for label, campaign, offset in label_specs:
        subset = trajectories[
            (trajectories["campaign"] == campaign)
            & (trajectories["algorithm"] == "LQ bandit")
            & (trajectories["noise_mV"] == 50)
        ].sort_values("iteration")
        if subset.empty:
            continue
        ax.text(
            BUDGET * 0.86,
            float(subset["best_so_far_V"].iloc[-1]) + offset,
            label,
            color=shade_for_noise(ALG_EFFICIENCY_COLORS[campaign], 50),
            ha="left",
            va="center",
            fontsize=12,
        )

    bo_last = bo_curve_summary[bo_curve_summary["noise_mV"] == 50].sort_values("iteration")
    if not bo_last.empty:
        ax.text(
            BUDGET * 0.68,
            float(bo_last["mean"].iloc[-1]) - 0.035,
            "BO",
            color=shade_for_noise("black", 50),
            ha="left",
            va="center",
            fontsize=12,
        )

    legend_handles = [
        plt.Line2D([0], [0], color=shade_for_noise("black", noise_mV), linewidth=1.4)
        for noise_mV in NOISE_LEVELS_MV
    ]
    ax.legend(
        legend_handles,
        [f"{noise_mV} mV" for noise_mV in NOISE_LEVELS_MV],
        frameon=False,
        title="Noise",
        fontsize=8,
        title_fontsize=9,
        loc="lower right",
        handlelength=2.0,
        labelspacing=0.35,
    )

    for ext in OUTPUT_FORMATS:
        fig.savefig(
            OUTPUT_DIR / f"figure_R3_LQ_campaign_Dragonfly_style_BO_uncertainty_sensitivity.{ext}",
            dpi=600,
        )
    plt.close(fig)


def load_alg_efficiency_outputs() -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    campaign_curves = {}
    for campaign_id in range(1, 5):
        campaign = f"Campaign{campaign_id}"
        path = ALG_EFFICIENCY_DIR / f"campaign{campaign_id}_actual_bandit_curve.csv"
        campaign_curves[campaign] = pd.read_csv(path)

    bo_summary = pd.read_csv(ALG_EFFICIENCY_DIR / "dragonfly_bo_summary.csv")
    return campaign_curves, bo_summary


def plot_fig_alg_efficiency_effect(summary: pd.DataFrame) -> None:
    campaign_curves, bo_summary = load_alg_efficiency_outputs()
    noise_colors = {
        10: "#3B78B8",
        25: "#4CAF50",
    }

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(7.2, 3.0),
        gridspec_kw={"width_ratios": [1.3, 1.0]},
        constrained_layout=True,
    )
    ax_eff, ax_effect = axes

    for campaign, curve in campaign_curves.items():
        ax_eff.plot(
            np.arange(1, len(curve) + 1),
            curve["best_so_far"].astype(float).to_numpy(),
            linewidth=1.6,
            color=ALG_EFFICIENCY_COLORS[campaign],
            label=campaign.replace("Campaign", "Campaign "),
        )

    bo_x = bo_summary["iteration"].to_numpy()
    bo_mean = bo_summary["mean"].astype(float).to_numpy()
    bo_std = bo_summary["std"].astype(float).to_numpy()
    ax_eff.plot(bo_x, bo_mean, linewidth=1.6, color="black", label="Dragonfly BO")
    ax_eff.fill_between(bo_x, bo_mean - bo_std, bo_mean + bo_std, color="0.88", linewidth=0)
    ax_eff.set_xlim(1, max(len(curve) for curve in campaign_curves.values()))
    ax_eff.set_ylim(-1.0, 0.0)
    ax_eff.set_xlabel("Trial index")
    ax_eff.set_ylabel(r"Best-so-far $\eta_{50}$ (V)")
    ax_eff.legend(frameon=False, fontsize=7)

    categories = CAMPAIGNS + ["BO"]
    category_positions = np.arange(len(categories))
    effect_noise_levels = [10, 25]
    jitter = {10: -0.09, 25: 0.09}
    effect_rows = summary[summary["noise_mV"].isin(effect_noise_levels)].copy()
    effect_rows["category"] = effect_rows["campaign"].where(
        effect_rows["algorithm"].eq("LQ bandit"),
        "BO",
    )

    for noise_mV in effect_noise_levels:
        subset = effect_rows[effect_rows["noise_mV"] == noise_mV]
        x_vals = []
        y_vals = []
        for category in categories:
            row = subset[subset["category"] == category]
            if row.empty:
                continue
            x_vals.append(category_positions[categories.index(category)] + jitter[noise_mV])
            y_vals.append(float(row["mean_curve_delta_vs_50mV_mV"].iloc[0]))
        ax_effect.scatter(
            x_vals,
            y_vals,
            s=24,
            color=noise_colors[noise_mV],
            label=f"{noise_mV} mV",
            zorder=3,
        )

    ax_effect.axhline(0, color="0.25", linewidth=FRAME_WIDTH)
    ax_effect.set_xticks(category_positions)
    ax_effect.set_xticklabels(["C1", "C2", "C3", "C4", "BO"])
    ax_effect.set_ylabel(r"$\Delta$ mean best-so-far vs 50 mV (mV)")
    ax_effect.set_xlabel("Algorithm-efficiency curve")
    ax_effect.legend(frameon=False, title="Assumed noise", fontsize=7, title_fontsize=7)

    y_abs = max(2.0, float(np.nanmax(np.abs(effect_rows["mean_curve_delta_vs_50mV_mV"]))) * 1.25)
    ax_effect.set_ylim(-0.15 * y_abs, y_abs)

    for ax in axes:
        ax.grid(False)
        for spine in ax.spines.values():
            spine.set_linewidth(FRAME_WIDTH)
        ax.tick_params(width=FRAME_WIDTH, length=3)

    for ext in OUTPUT_FORMATS:
        fig.savefig(OUTPUT_DIR / f"figure_R3_Fig_alg_efficiency_uncertainty_effect.{ext}", dpi=600)
    plt.close(fig)


def plot_alg_efficiency_by_error(trajectories: pd.DataFrame, bo_curve_summary: pd.DataFrame) -> None:
    displayed_noise_levels = [10, 25, 50]
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.7), sharex=True, sharey=True)
    axes_flat = np.atleast_1d(axes).ravel()

    for ax, noise_mV in zip(axes_flat, displayed_noise_levels):
        noise_subset = trajectories[trajectories["noise_mV"] == noise_mV]

        for campaign in CAMPAIGNS:
            campaign_curve = noise_subset[
                (noise_subset["campaign"] == campaign)
                & (noise_subset["algorithm"] == "LQ bandit")
            ].sort_values("iteration")
            ax.plot(
                campaign_curve["iteration"],
                campaign_curve["best_so_far_V"],
                linewidth=1.5,
                color=ALG_EFFICIENCY_COLORS[campaign],
                label=campaign.replace("Campaign", "Campaign "),
            )

        bo_summary = bo_curve_summary[bo_curve_summary["noise_mV"] == noise_mV].sort_values("iteration")
        bo_x = bo_summary["iteration"].to_numpy()
        bo_mean = bo_summary["mean"].astype(float).to_numpy()
        bo_std = bo_summary["std"].astype(float).to_numpy()
        ax.fill_between(bo_x, bo_mean - bo_std, bo_mean + bo_std, color="0.88", linewidth=0)
        ax.plot(
            bo_x,
            bo_mean,
            linewidth=1.7,
            color="black",
            label="Dragonfly BO",
        )

        ax.text(
            0.04,
            0.08,
            f"{noise_mV} mV",
            transform=ax.transAxes,
            ha="left",
            va="bottom",
        )
        ax.set_xlim(1, BUDGET)
        ax.set_ylim(-1.0, 0.0)
        ax.grid(False)
        for spine in ax.spines.values():
            spine.set_linewidth(FRAME_WIDTH)
        ax.tick_params(width=FRAME_WIDTH, length=3)

    axes_flat[0].set_ylabel(r"Best-so-far $\eta_{50}$ (V)")
    for ax in axes_flat:
        ax.set_xlabel("Trial index")

    axes_flat[1].legend(frameon=False, fontsize=7, loc="lower right")
    fig.tight_layout()

    for ext in OUTPUT_FORMATS:
        fig.savefig(OUTPUT_DIR / f"figure_R3_Fig_alg_efficiency_by_error.{ext}", dpi=600)
    plt.close(fig)


def write_readme(
    summary: pd.DataFrame,
    pretrain: pd.DataFrame,
    campaign_candidates: dict[str, pd.DataFrame],
) -> None:
    candidate_lines = "\n".join(
        f"- {campaign}: {len(df)} candidate recipes" for campaign, df in campaign_candidates.items()
    )
    text = f"""# Uncertainty sensitivity optimization test

This folder tests whether the optimization trajectories materially change when the
assumed observation noise is reduced from 50 mV.

The output `figure_R3_Fig_alg_efficiency_uncertainty_effect` places the uncertainty
effect in the `Fig_alg_efficiency` frame. Its left panel reuses the saved actual
campaign curves and Dragonfly BO mean curve from `Figures_Main/Fig_alg_efficiency`;
its right panel reports the sensitivity effect of reducing assumed noise relative
to 50 mV, including the rerun Dragonfly-style BO benchmark.

The output `figure_R3_Fig_alg_efficiency_by_error` uses the left-panel
`Fig_alg_efficiency` layout directly, with one subplot each for 10, 25, and
50 mV assumed error. The BO curve in each panel is rerun for that assumed error
level and summarized as the mean of {DRAGONFLY_STYLE_BO_RUNS} runs.

Because the campaign curves in `Fig_alg_efficiency` are the actual executed
experimental order, those curves are fixed. The uncertainty effect is therefore
reported as a companion calculation using the same best-so-far efficiency metric
and trial-index convention.

Inputs:
- `Data/result_pretrain.csv` as the initial observed set.
- `Data/Campaign1.csv` through `Data/Campaign4.csv` as finite measured candidate pools
  for the LQ bandit campaign analysis.
- A random-forest digital twin trained on `Data/result_pretrain.csv`, matching the
  Dragonfly BO benchmark structure in `Fig_alg_efficiency`.

Algorithms:
- `LQ bandit`: quadratic-feature Bayesian linear UCB, evaluated separately on
  Campaign1-Campaign4 candidate pools.
- `Dragonfly-style BO`: feasible-domain BO on the random-forest digital twin.
  The local implementation uses GP-UCB with the assumed error as the GP observation
  noise, because the Dragonfly package is not installed in this environment.

Both algorithms maximize `{OBJECTIVE_COL}` and report the true measured best-so-far
trajectory after each selected recipe. The assumed observation noise controls model
regularization/predictive uncertainty; it is not used to perturb the true measured
objective for scoring.

Rows in initial set: {len(pretrain)}
LQ candidate pools:
{candidate_lines}
Digital-twin training rows: {len(pretrain.dropna(subset=[*FEATURE_COLS, OBJECTIVE_COL]))}
Dragonfly-style BO runs per noise level: {DRAGONFLY_STYLE_BO_RUNS}
Dragonfly-style candidate pool size per run: {DRAGONFLY_STYLE_POOL_SIZE}
Budget: {BUDGET}
Assumed noise levels: {NOISE_LEVELS_MV} mV

Summary:
{summary.to_string(index=False)}
"""
    (OUTPUT_DIR / "README.md").write_text(text, encoding="utf-8")


def main() -> None:
    pretrain, campaign_candidates = load_experimental_landscapes()
    trajectories = []

    for campaign, candidates in campaign_candidates.items():
        for noise_mV in NOISE_LEVELS_MV:
            sigma_v = noise_mV / 1000
            print(f"Running {campaign} LQ bandit, assumed noise={noise_mV} mV")
            trajectories.append(run_lq_ucb(pretrain, candidates, sigma_v, campaign))

    bo_runs_df, bo_curve_summary_df, bo_effect_summary_df = run_dragonfly_style_bo_by_noise(pretrain)

    trajectories_df = pd.concat(trajectories, ignore_index=True)
    lq_summary_df = summarize_trajectories(trajectories_df)
    summary_df = pd.concat([lq_summary_df, bo_effect_summary_df], ignore_index=True)

    plot_trajectories(trajectories_df, bo_curve_summary_df)

    print(f"[DONE] Wrote uncertainty sensitivity figures to {OUTPUT_DIR}")
    print(summary_df.to_string(index=False))


if __name__ == "__main__":
    main()
