import os
import sys

SCRIPT_DIR = os.path.dirname(__file__)
SCRIPTS_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
UTIL_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "utils"))
sys.path.append(SCRIPTS_ROOT)
sys.path.append(UTIL_ROOT)

from registry import get_data_path

FIGURE_METADATA = {
    "stable_id": "Fig_proxy_campaigns",
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
    df["log10_Cdl"] = np.log10(df["Cdl mF cm-2"])
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


def plot_geometric_benchmark(df):
    plt.figure(figsize=(3.6, 3.6))
    pre_df = df[df["phase"] == "pretrain"]
    plt.scatter(
        pre_df["log10_i0_per_Cdl"],
        pre_df["eta50_abs_V"],
        s=16,
        alpha=0.35,
        color="lightgray",
        label="Pretrain",
    )

    campaign_ids = sorted([c for c in df["campaign"].dropna().unique() if c >= 1])
    for campaign_id in campaign_ids:
        campaign_id = int(campaign_id)
        train_df = df[(df["campaign"] == campaign_id) & (df["phase"] == "train")]
        plt.scatter(
            train_df["log10_i0_per_Cdl"],
            train_df["eta50_abs_V"],
            s=20,
            alpha=0.8,
            color=sample_campaign_color(campaign_id, 0.65),
            label=f"Campaign {campaign_id} train",
        )

    plt.ylim(1.0, 0)
    plt.xlabel(r"log$_{10}$($i_0$/C$_{dl}$)")
    plt.ylabel(r"$η_{50}$(V vs. RHE)")
    plt.legend(frameon=False, fontsize=9)
    plt.tight_layout()
    plt.savefig(
        os.path.join(
            OUTPUT_DIR,
            "kinetics_proxy_vs_geometric_benchmark_by_campaign.svg",
        )
    )
    plt.close()


def plot_morphology_contribution(df):
    plt.figure(figsize=(3.6, 3.6))
    pre_df = df[df["phase"] == "pretrain"]
    plt.scatter(
        pre_df["log10_Cdl"],
        pre_df["eta50_abs_V"],
        s=16,
        alpha=0.35,
        color="lightgray",
        label="Pretrain",
    )

    campaign_ids = sorted([c for c in df["campaign"].dropna().unique() if c >= 1])
    for campaign_id in campaign_ids:
        campaign_id = int(campaign_id)
        train_df = df[(df["campaign"] == campaign_id) & (df["phase"] == "train")]
        plt.scatter(
            train_df["log10_Cdl"],
            train_df["eta50_abs_V"],
            s=20,
            alpha=0.8,
            color=sample_campaign_color(campaign_id, 0.65),
            label=f"Campaign {campaign_id} train",
        )

    plt.ylim(1.0, 0)
    plt.xlabel(r"log$_{10}$(C$_{dl}$ / mF cm$^{-2}$)")
    plt.ylabel(r"$η_{50}$(V vs. RHE)")
    plt.title("Morphology contribution proxy")
    plt.legend(frameon=False, fontsize=9)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "morphology_contribution_by_campaign.svg"))
    plt.close()


df = add_phase_columns(load_analysis_data(DATAPATH))
plot_geometric_benchmark(df)
plot_morphology_contribution(df)
