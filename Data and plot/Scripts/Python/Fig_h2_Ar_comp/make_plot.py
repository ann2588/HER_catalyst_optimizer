import os
from pathlib import Path

MPL_CACHE_DIR = Path("/tmp/her-catalyst-optimizer-mpl-cache")
MPL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MPL_CACHE_DIR))
os.environ.setdefault("XDG_CACHE_HOME", str(MPL_CACHE_DIR))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[2]

FIGURE_METADATA = {
    "stable_id": "Fig_h2_Ar_comp",
    "script": __file__,
    "data_keys": [
        "result_all_campaign",
        "All_Ovp_Cdl_Tafel",
        "HER_Overpotentials_all_campaign_Ar",
        "Tafel_Analysis_all_campaign_Ar",
        "Capacitance_all_Ar",
    ],
    "figure_type": "SI",
}


def get_output_dir(meta: dict[str, object]) -> Path:
    fig_base = "Figures_SI" if meta["figure_type"] == "SI" else "Figures_Main"
    outdir = PROJECT_ROOT / fig_base / str(meta["stable_id"])
    outdir.mkdir(parents=True, exist_ok=True)
    return outdir


DATA_DIR = PROJECT_ROOT / "Data"
OUTPUT_DIR = get_output_dir(FIGURE_METADATA)
OUTPUT_FORMATS = ("eps", "png")

RECIPE_COLUMNS = ["Experiment", "V", "Cr", "Mg", "Fe", "Co", "Ni", "Cu", "S", "Se", "P", "blank", "Volt", "Time"]
SCATTER_FIGSIZE_IN = (7.2, 7.2)
MAX_ABS_LOG10_EXCHANGE_FOR_SCATTER = 30.0
MIN_ABS_ETA_V = 0.1
FRAME_WIDTH_PT = 0.5
H2_CONDITION_LABEL = r"H$_2$KOH"
AR_CONDITION_LABEL = "ArKOH"

plt.rcParams.update(
    {
        "font.family": "Arial",
        "font.size": 12,
        "axes.labelsize": 12,
        "axes.linewidth": FRAME_WIDTH_PT,
        "xtick.major.width": FRAME_WIDTH_PT,
        "ytick.major.width": FRAME_WIDTH_PT,
        "xtick.labelsize": 12,
        "ytick.labelsize": 12,
        "mathtext.fontset": "custom",
        "mathtext.rm": "Arial",
        "mathtext.it": "Arial:italic",
        "mathtext.bf": "Arial:bold",
        "ps.fonttype": 42,
    }
)


def read_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / name)


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def add_if_present(df: pd.DataFrame, source: str, dest: str, out: pd.DataFrame) -> None:
    if source in df.columns:
        out[dest] = numeric(df[source])


def ensure_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    for col in columns:
        if col not in df.columns:
            df[col] = np.nan
    return df


def experiment_sort_key(series: pd.Series) -> pd.Series:
    return series.astype(str).str.extract(r"(\d+)")[0].astype(float)


def build_h2_metrics() -> pd.DataFrame:
    recipe = read_csv("result_all_campaign.csv")
    h2_merged = read_csv("merged_all.csv")

    out = recipe[RECIPE_COLUMNS].copy()
    add_if_present(recipe, "Overpotential V at 50.0 mA cm-2", "eta50_H2_V", out)

    h2_metrics = h2_merged[
        [
            "Experiment",
            "Tafel Slope (mV/dec)",
            "Exchange Current Density (mA/cm²)",
            "R²",
            "Overpotential @ 50 mA",
            "Cdl mF cm-2",
        ]
    ].rename(
        columns={
            "Tafel Slope (mV/dec)": "tafel_H2_mV_dec",
            "Exchange Current Density (mA/cm²)": "exchange_H2_mA_cm2",
            "R²": "tafel_r2_H2",
            "Overpotential @ 50 mA": "eta50_H2_from_merged_V",
            "Cdl mF cm-2": "cdl_H2_mF_cm2",
        }
    )
    out = out.merge(h2_metrics, on="Experiment", how="left")
    out = ensure_columns(out, ["eta50_H2_V", "eta50_H2_from_merged_V"])
    out["eta50_H2_V"] = out["eta50_H2_V"].combine_first(out["eta50_H2_from_merged_V"])
    return out


def build_ar_metrics() -> pd.DataFrame:
    ar_eta = read_csv("HER_Overpotentials_all_campaign_Ar.csv")
    ar_tafel = read_csv("Tafel_Analysis_all_campaign_Ar.csv")
    ar_cap = read_csv("Pseudo_Capacitance_fw_full_Ar.csv")

    out = ar_eta[["Experiment"]].copy()
    add_if_present(ar_eta, "Overpotential V at 50.0 mA/cm2_Ar", "eta50_Ar_V", out)

    ar_tafel = ar_tafel.rename(
        columns={
            "Tafel Slope (mV dec-1)_Ar": "tafel_Ar_mV_dec",
            "Exchange Current Density (mA cm-2)_Ar": "exchange_Ar_mA_cm2",
            "Tafel R^2_Ar": "tafel_r2_Ar",
        }
    )
    out = out.merge(
        ar_tafel[["Experiment", "tafel_Ar_mV_dec", "exchange_Ar_mA_cm2", "tafel_r2_Ar"]],
        on="Experiment",
        how="left",
    )

    ar_cap = ar_cap.rename(columns={"Cdl mF cm-2_Ar": "cdl_Ar_mF_cm2"})
    out = out.merge(ar_cap[["Experiment", "cdl_Ar_mF_cm2"]], on="Experiment", how="left")
    return ensure_columns(
        out,
        [
            "eta50_Ar_V",
            "tafel_Ar_mV_dec",
            "exchange_Ar_mA_cm2",
            "tafel_r2_Ar",
            "cdl_Ar_mF_cm2",
        ],
    )


def apply_eta_threshold(df: pd.DataFrame) -> pd.DataFrame:
    eta_cols = [col for col in df.columns if col.startswith("eta50") and col.endswith("_V")]
    for col in eta_cols:
        df.loc[df[col].abs() < MIN_ABS_ETA_V, col] = np.nan
    return df


def add_derived_metrics(df: pd.DataFrame) -> pd.DataFrame:
    df["log10_exchange_H2"] = np.log10(df["exchange_H2_mA_cm2"].where(df["exchange_H2_mA_cm2"] > 0))
    df["log10_exchange_Ar"] = np.log10(df["exchange_Ar_mA_cm2"].where(df["exchange_Ar_mA_cm2"] > 0))
    return df


def build_comparison() -> pd.DataFrame:
    h2 = build_h2_metrics()
    ar = build_ar_metrics()
    comparison = h2.merge(ar, on="Experiment", how="left")
    comparison = apply_eta_threshold(comparison)
    comparison = add_derived_metrics(comparison)
    return comparison.sort_values("Experiment", key=experiment_sort_key).reset_index(drop=True)


def one_to_one_limits(x: pd.Series, y: pd.Series) -> tuple[float, float]:
    values = pd.concat([x, y]).replace([np.inf, -np.inf], np.nan).dropna()
    if values.empty:
        return 0.0, 1.0
    low = values.min()
    high = values.max()
    pad = (high - low) * 0.08 if high > low else max(abs(high) * 0.08, 1.0)
    return low - pad, high + pad


def filter_extreme_log_exchange_values(df: pd.DataFrame, columns: tuple[str, str]) -> pd.DataFrame:
    in_range = df.loc[:, list(columns)].abs().le(MAX_ABS_LOG10_EXCHANGE_FOR_SCATTER).all(axis=1)
    return df.loc[in_range].copy()


def plot_scatter(df: pd.DataFrame) -> None:
    plot_specs = [
        ("eta50_H2_V", "eta50_Ar_V", r"$\eta_{50}$ (V)"),
        ("tafel_H2_mV_dec", "tafel_Ar_mV_dec", r"Tafel slope (mV dec$^{-1}$)"),
        (
            "log10_exchange_H2",
            "log10_exchange_Ar",
            r"$\log_{10}(j_0\ /\ \mathrm{mA}\ \mathrm{cm}^{-2})$",
        ),
        ("cdl_H2_mF_cm2", "cdl_Ar_mF_cm2", r"$C_{\mathrm{dl}}$ (mF cm$^{-2}$)"),
    ]

    fig, axes = plt.subplots(2, 2, figsize=SCATTER_FIGSIZE_IN, constrained_layout=True)
    for ax, (h2_col, ar_col, label) in zip(axes.ravel(), plot_specs):
        valid = df[["Experiment", h2_col, ar_col]].replace([np.inf, -np.inf], np.nan).dropna()
        if h2_col == "log10_exchange_H2":
            valid = filter_extreme_log_exchange_values(valid, (h2_col, ar_col))

        ax.scatter(valid[h2_col], valid[ar_col], s=9, color="#2f6f9f")
        low, high = one_to_one_limits(valid[h2_col], valid[ar_col])
        ax.plot([low, high], [low, high], color="#555555", linewidth=FRAME_WIDTH_PT, linestyle="--")
        ax.set_xlim(low, high)
        ax.set_ylim(low, high)
        ax.set_xlabel(f"{H2_CONDITION_LABEL} {label}")
        ax.set_ylabel(f"{AR_CONDITION_LABEL} {label}")
        ax.tick_params(axis="both", width=FRAME_WIDTH_PT)
        for spine in ax.spines.values():
            spine.set_visible(True)
            spine.set_linewidth(FRAME_WIDTH_PT)

    for fmt in OUTPUT_FORMATS:
        fig.savefig(OUTPUT_DIR / f"h2_ar_metric_scatter.{fmt}", dpi=600)
    plt.close(fig)


def main() -> None:
    comparison = build_comparison()
    plot_scatter(comparison)

    print(f"[DONE] Wrote {OUTPUT_DIR / 'h2_ar_metric_scatter.eps'}")
    print(f"[INFO] rows={len(comparison)}")


if __name__ == "__main__":
    main()
