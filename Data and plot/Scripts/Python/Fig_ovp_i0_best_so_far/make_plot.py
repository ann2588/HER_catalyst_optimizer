import os
import sys

SCRIPT_DIR = os.path.dirname(__file__)
SCRIPTS_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
UTIL_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "utils"))
sys.path.append(SCRIPTS_ROOT)
sys.path.append(UTIL_ROOT)

from registry import get_data_path

FIGURE_METADATA = {
    "stable_id": "Fig_ovp_i0_best_so_far",
    "script": __file__,
    "data_keys": "All_Ovp_Cdl_Tafel",
    "figure_type": "SI",
}


def get_output_dir(meta):
    base = os.path.dirname(__file__)
    fig_base = "Figures_SI" if meta["figure_type"] == "SI" else "Figures_Main"
    outdir = os.path.join(base, "..", "..", "..", fig_base, meta["stable_id"])
    os.makedirs(outdir, exist_ok=True)
    return outdir


OUTPUT_DIR = get_output_dir(FIGURE_METADATA)
DATAPATH = get_data_path(FIGURE_METADATA["data_keys"])

###========================================================================###
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl

mpl.rcParams["font.family"] = "Arial"
mpl.rcParams["mathtext.rm"] = "Arial"
mpl.rcParams["font.size"] = 8
mpl.rcParams["ps.fonttype"] = 42


def load_analysis_data(file):
    df = pd.read_csv(file)
    required_cols = [
        "Experiment",
        "Tafel Slope (mV/dec)",
        "Exchange Current Density (mA/cm²)",
        "R²",
        "Overpotential @ 50 mA",
        "Cdl mF cm-2",
    ]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    df["exp_num"] = df["Experiment"].astype(str).str.extract(r"(\d+)")[0].astype(float)

    num_cols = [
        "Tafel Slope (mV/dec)",
        "Exchange Current Density (mA/cm²)",
        "R²",
        "Overpotential @ 50 mA",
        "Cdl mF cm-2",
    ]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df.loc[df["Overpotential @ 50 mA"].abs() < 0.05, "Overpotential @ 50 mA"] = np.nan
    df = df.dropna(
        subset=[
            "exp_num",
            "Overpotential @ 50 mA",
            "Cdl mF cm-2",
            "Exchange Current Density (mA/cm²)",
        ]
    ).copy()
    df = df[
        (df["Cdl mF cm-2"] > 0)
        & (df["Exchange Current Density (mA/cm²)"] > 0)
    ].copy()

    df["eta50_abs_V"] = df["Overpotential @ 50 mA"].abs()
    df["i0_per_Cdl"] = df["Exchange Current Density (mA/cm²)"] / df["Cdl mF cm-2"]
    df["log10_i0_per_Cdl"] = np.log10(df["i0_per_Cdl"])
    return df.sort_values("exp_num").copy()


startinglist = [609, 729, 859, 979, 1139]
endlist = [728, 858, 978, 1098, 1258]
campaign_defs = list(zip(startinglist, endlist))


def assign_phase(exp_num, campaign_defs):
    if pd.isna(exp_num):
        return np.nan, np.nan
    if exp_num < campaign_defs[0][0]:
        return "pretrain", 0
    for i, (start, end) in enumerate(campaign_defs, start=1):
        if start <= exp_num <= end:
            return "train", i
    return "post", np.nan


def make_mixed_x(pre_df, train_df):
    pre_df = pre_df.sort_values("exp_num").copy()
    train_df = train_df.sort_values("exp_num").copy()
    pre_df["plot_x"] = pre_df["exp_num"]

    train_start = pre_df["plot_x"].max() + 1 if len(pre_df) > 0 else 1
    train_df["plot_x"] = np.arange(train_start, train_start + len(train_df))
    return pre_df, train_df


campaign_cmaps = {
    1: "Blues",
    2: "Oranges",
    3: "Greens",
    4: "Purples",
    5: "Greys",
}


def sample_campaign_color(campaign_id, frac=0.65):
    cmap = plt.get_cmap(campaign_cmaps[campaign_id])
    return cmap(frac)


def add_phase_columns(df):
    phase_info = df["exp_num"].apply(lambda x: assign_phase(x, campaign_defs))
    df["phase"] = phase_info.apply(lambda x: x[0])
    df["campaign"] = phase_info.apply(lambda x: x[1])
    return df


def plot_performance_vs_iteration(df):
    n_campaigns = len(campaign_defs)
    fig, axes = plt.subplots(
        nrows=n_campaigns,
        ncols=1,
        figsize=(3.6, 1.44 * n_campaigns),
        sharex=True,
        sharey=True,
    )
    fig.subplots_adjust(hspace=0, left=0.15, right=0.95, top=0.97, bottom=0.08)

    if n_campaigns == 1:
        axes = [axes]

    for ax, (campaign_id, _) in zip(axes, enumerate(campaign_defs, start=1)):
        pre_df = df[df["phase"] == "pretrain"].sort_values("exp_num").copy()
        train_df = df[
            (df["campaign"] == campaign_id) & (df["phase"] == "train")
        ].sort_values("exp_num").copy()
        pre_df, train_df = make_mixed_x(pre_df, train_df)

        ax.scatter(
            pre_df["plot_x"],
            pre_df["eta50_abs_V"],
            s=14,
            alpha=0.35,
            color="lightgray",
            label="Pretrain",
        )
        if len(pre_df) >= 10:
            pre_roll = pre_df["eta50_abs_V"].rolling(30, min_periods=10).median()
            ax.plot(pre_df["plot_x"], pre_roll, linewidth=2, color="gray")

        train_color = sample_campaign_color(campaign_id, 0.65)
        ax.scatter(
            train_df["plot_x"],
            train_df["eta50_abs_V"],
            s=18,
            alpha=0.8,
            color=train_color,
            label=f"Campaign {campaign_id} train",
        )
        if len(train_df) >= 10:
            train_roll = train_df["eta50_abs_V"].rolling(15, min_periods=5).median()
            ax.plot(
                train_df["plot_x"],
                train_roll,
                linewidth=2,
                color=sample_campaign_color(campaign_id, 0.85),
            )

        if len(pre_df) > 0 and len(train_df) > 0:
            ax.axvline(
                pre_df["plot_x"].max() + 0.5,
                linestyle="--",
                linewidth=1,
                color="silver",
            )

        ax.set_ylim(1, 0)
        ax.set_ylabel(r"|$η_{50}$| (V vs. RHE)")
        ax.legend(frameon=False, fontsize=8, loc="best")

    for ax in axes[:-1]:
        ax.tick_params(labelbottom=False)

    axes[-1].set_xlabel("Experiment index")
    plt.savefig(os.path.join(OUTPUT_DIR, "performance_vs_iteration_all_campaigns_vertical.svg"))
    plt.close()


def plot_proxy_vs_iteration(df):
    n_campaigns = len(campaign_defs)
    fig, axes = plt.subplots(
        nrows=n_campaigns,
        ncols=1,
        figsize=(3.6, 1.44 * n_campaigns),
        sharex=True,
        sharey=True,
    )
    fig.subplots_adjust(hspace=0, left=0.15, right=0.95, top=0.97, bottom=0.08)

    if n_campaigns == 1:
        axes = [axes]

    max_len = 0
    for campaign_id, _ in enumerate(campaign_defs, start=1):
        pre_df = df[df["phase"] == "pretrain"].sort_values("exp_num").copy()
        train_df = df[
            (df["campaign"] == campaign_id) & (df["phase"] == "train")
        ].sort_values("exp_num").copy()
        pre_df, train_df = make_mixed_x(pre_df, train_df)

        panel_max = 0
        if len(pre_df) > 0:
            panel_max = max(panel_max, pre_df["plot_x"].max())
        if len(train_df) > 0:
            panel_max = max(panel_max, train_df["plot_x"].max())
        max_len = max(max_len, panel_max)

    for ax, (campaign_id, _) in zip(axes, enumerate(campaign_defs, start=1)):
        pre_df = df[df["phase"] == "pretrain"].sort_values("exp_num").copy()
        train_df = df[
            (df["campaign"] == campaign_id) & (df["phase"] == "train")
        ].sort_values("exp_num").copy()
        pre_df, train_df = make_mixed_x(pre_df, train_df)

        ax.scatter(
            pre_df["plot_x"],
            pre_df["log10_i0_per_Cdl"],
            s=14,
            alpha=0.35,
            color="lightgray",
            label="Pretrain",
        )
        if len(pre_df) >= 10:
            pre_roll = pre_df["log10_i0_per_Cdl"].rolling(30, min_periods=10).median()
            ax.plot(pre_df["plot_x"], pre_roll, linewidth=2, color="gray")

        train_color = sample_campaign_color(campaign_id, 0.65)
        ax.scatter(
            train_df["plot_x"],
            train_df["log10_i0_per_Cdl"],
            s=18,
            alpha=0.8,
            color=train_color,
            label=f"Campaign {campaign_id} train",
        )
        if len(train_df) >= 10:
            train_roll = train_df["log10_i0_per_Cdl"].rolling(15, min_periods=5).median()
            ax.plot(
                train_df["plot_x"],
                train_roll,
                linewidth=2,
                color=sample_campaign_color(campaign_id, 0.85),
            )

        if len(pre_df) > 0 and len(train_df) > 0:
            ax.axvline(
                pre_df["plot_x"].max() + 0.5,
                linestyle="--",
                linewidth=1,
                color="silver",
            )

        ax.set_xlim(left=df["exp_num"].min(), right=max_len)
        ax.set_ylabel(r"log$_{10}$($i_0$/C$_{dl}$)")
        ax.legend(frameon=False, fontsize=8, loc="best")

    for ax in axes[:-1]:
        ax.tick_params(labelbottom=False)

    axes[-1].set_xlabel("Experiment index")
    plt.savefig(os.path.join(OUTPUT_DIR, "kinetic_proxy_vs_iteration_all_campaigns_vertical.svg"))
    plt.close()


df = add_phase_columns(load_analysis_data(DATAPATH))
plot_performance_vs_iteration(df)
plot_proxy_vs_iteration(df)
