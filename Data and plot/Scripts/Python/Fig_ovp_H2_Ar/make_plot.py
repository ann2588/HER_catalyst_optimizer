import glob
import os
import re
from pathlib import Path
from typing import Dict, Optional

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
    "stable_id": "Fig_ovp_H2_Ar",
    "script": __file__,
    "data_keys": [
        "All data",
        "result_all_campaign",
        "result_pretrain",
        "All_Ovp_Cdl",
    ],
    "figure_type": "SI",
}


def get_output_dir(meta: dict[str, object]) -> Path:
    fig_base = "Figures_SI" if meta["figure_type"] == "SI" else "Figures_Main"
    outdir = PROJECT_ROOT / fig_base / str(meta["stable_id"])
    outdir.mkdir(parents=True, exist_ok=True)
    return outdir


DATA_DIR = PROJECT_ROOT / "Data"
RAW_DATA_DIR = DATA_DIR / "All data"
RECIPE_CSV = DATA_DIR / "result_all_campaign.csv"
ALL_OVP_CDL_CSV = DATA_DIR / "Merged_ovp_cdl_full.csv"
OUTPUT_DIR = get_output_dir(FIGURE_METADATA)
OUTPUT_FORMATS = ("png", "eps")

PH_KOH = 13.7
AG_AGCL_OFFSET_V = 0.205
RHE_SLOPE_V_PER_PH = 0.059
GCE_AREA_CM2 = 0.0706858

RECIPE_COLUMNS = ["Experiment", "V", "Cr", "Mg", "Fe", "Co", "Ni", "Cu", "S", "Se", "P", "blank", "Volt", "Time"]
CURRENT_TARGETS = [10.0, 50.0]
CURRENTS_TO_PLOT = [50]
DEFAULT_FIGSIZE = (7.2, 3.6)
DOE_FIGSIZE = (3.6, 1.8)
CAMPAIGN_FIGSIZE = (3.6, 1.8)
FRAME_WIDTH = 0.5
X_PAD = 5
Y_LIMITS = (1.0, 0.0)
Y_TICKS = np.linspace(0.0, 1.0, 6)
CURRENT_COLORS = {50: "#a23b72"}
DOE_COLOR = "#000000"
CAMPAIGN_COLORS = {
    "campaign1": "#4A90E2",
    "campaign2": "#D98E4A",
    "campaign3": "#4CAF50",
    "campaign4": "#9E82CE",
    "campaign5": "#8A8A8A",
}
CAMPAIGN_RANGES = {
    "Campaign1": (609, 728),
    "Campaign2": (729, 858),
    "Campaign3": (859, 978),
    "Campaign4": (979, 1098),
    "Campaign5": (1099, 1258),
}
CAMPAIGN_AXIS_MAX = {
    "campaign1": 120,
    "campaign2": 120,
    "campaign3": 120,
    "campaign4": 120,
    "campaign5": 160,
}
ETA_COLUMNS = {
    10: [
        "eta10_H2KOH_CV50_V",
        "eta10_H2KOH_CVsr50_V",
        "eta10_ArKOH_CV50_V",
        "eta10_ArKOH_CVsr50_V",
    ],
    50: [
        "eta50_H2KOH_CV50_V",
        "eta50_H2KOH_CVsr50_V",
        "eta50_ArKOH_CV50_V",
        "eta50_ArKOH_CVsr50_V",
    ],
}
GAS_ETA_COLUMNS = {
    "h2": {
        50: ["eta50_H2KOH_CV50_V", "eta50_H2KOH_CVsr50_V"],
    },
    "ar": {
        50: ["eta50_ArKOH_CV50_V", "eta50_ArKOH_CVsr50_V"],
    },
}

REMOVED_EXPERIMENTS_ABS_Y_LT_0P1 = [
    "exp637",
    "exp668",
    "exp681",
    "exp685",
    "exp686",
    "exp693",
    "exp698",
    "exp705",
    "exp714",
    "exp719",
    "exp773",
    "exp816",
    "exp830",
    "exp843",
    "exp877",
    "exp885",
    "exp1039",
    "exp1063",
]


def experiment_number(value: object) -> Optional[int]:
    match = re.search(r"exp(\d+)", str(value), re.I)
    return int(match.group(1)) if match else None


def experiment_sort_key(series: pd.Series) -> pd.Series:
    return series.astype(str).str.extract(r"(\d+)")[0].astype(float)


def parent_experiment_id(path: Path) -> Optional[str]:
    match = re.search(r"(exp\d+)", path.name, re.I)
    return match.group(1).lower() if match else None


def efin_mV(path: str) -> Optional[int]:
    match = re.search(r"_Efin_(-?\d+)mV", os.path.basename(path))
    return int(match.group(1)) if match else None


def efin_sort_key(path: str) -> tuple[int, str]:
    value = efin_mV(path)
    return (value if value is not None else 10**9, path)


def relpath(path: Optional[str]) -> str:
    if not path:
        return ""
    return os.path.relpath(path, PROJECT_ROOT).replace(os.sep, "/")


def find_header_line(path: str, marker: str = "Potential/V") -> Optional[int]:
    with open(path, "r", encoding="utf-8", errors="ignore") as handle:
        for index, line in enumerate(handle):
            if marker in line:
                return index
    return None


def convert_raw_cv_to_rhe(raw_file: str, force: bool = False) -> Optional[str]:
    if raw_file.endswith("vsRHE.txt"):
        return raw_file

    converted_file = raw_file[:-4] + "vsRHE.txt"
    if (
        not force
        and os.path.exists(converted_file)
        and os.path.getmtime(converted_file) >= os.path.getmtime(raw_file)
    ):
        return converted_file

    header_line = find_header_line(raw_file)
    if header_line is None:
        return None

    raw = pd.read_csv(
        raw_file,
        skiprows=header_line,
        header=0,
        names=["Potential V vs ref", "Current A"],
        skipinitialspace=True,
    )
    raw["Potential V vs ref"] = pd.to_numeric(raw["Potential V vs ref"], errors="coerce")
    raw["Current A"] = pd.to_numeric(raw["Current A"], errors="coerce")
    raw = raw.dropna(subset=["Potential V vs ref", "Current A"])

    converted = pd.DataFrame(
        {
            "Potential V vs RHE": raw["Potential V vs ref"]
            + AG_AGCL_OFFSET_V
            + PH_KOH * RHE_SLOPE_V_PER_PH,
            "Current mA cm-2": -raw["Current A"] / GCE_AREA_CM2 * 1000,
        }
    )
    converted.to_csv(converted_file, index=False)
    return converted_file


def ensure_cv50_conversions(folder: str, force: bool = False) -> None:
    raw_files = []
    for pattern in ["*_CV_50mVs_Efin_*.txt", "*_CV_sr_50mVs_Efin_*.txt"]:
        raw_files.extend(glob.glob(os.path.join(folder, pattern)))
    raw_files = [path for path in raw_files if not path.endswith("vsRHE.txt")]
    for raw_file in raw_files:
        convert_raw_cv_to_rhe(raw_file, force=force)


def read_rhe_curve(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [str(col).strip() for col in df.columns]
    potential_col = next((col for col in df.columns if col == "Potential V vs RHE"), None)
    current_col = next((col for col in df.columns if col in {"Current mA cm-2", "Current mA/cm2"}), None)

    if potential_col is None or current_col is None:
        raise ValueError(f"Could not find RHE/current columns in {path}")

    out = pd.DataFrame(
        {
            "Potential V vs RHE": pd.to_numeric(df[potential_col], errors="coerce"),
            "Current mA cm-2": pd.to_numeric(df[current_col], errors="coerce"),
        }
    )
    return out.dropna(subset=["Potential V vs RHE", "Current mA cm-2"]).reset_index(drop=True)


def cathodic_sweeps(df: pd.DataFrame) -> list[pd.DataFrame]:
    if len(df) < 2:
        return []

    direction = np.sign(df["Potential V vs RHE"].diff())
    direction = direction.replace(0, np.nan).ffill().bfill()
    groups = direction.ne(direction.shift()).cumsum()

    sweeps = []
    for _, segment in df.groupby(groups):
        segment_direction = direction.loc[segment.index].median()
        if segment_direction < 0 and len(segment) > 10:
            sweeps.append(segment.reset_index(drop=True))
    return sweeps


def select_cathodic_sweep(df: pd.DataFrame, current_target: float) -> pd.DataFrame:
    sweeps = cathodic_sweeps(df)
    if not sweeps:
        return df

    reachable = [
        sweep
        for sweep in sweeps
        if sweep["Current mA cm-2"].abs().max() >= current_target - 1
    ]
    if reachable:
        return reachable[-1]
    return sweeps[-1]


def extract_overpotential(path: str, current_target: float) -> tuple[float, float, str]:
    df = read_rhe_curve(path)
    section = select_cathodic_sweep(df, current_target)
    abs_current = section["Current mA cm-2"].abs()
    closest_idx = (abs_current - current_target).abs().idxmin()
    actual_current = section.loc[closest_idx, "Current mA cm-2"]
    potential = section.loc[closest_idx, "Potential V vs RHE"]
    status = "ok" if abs(abs(actual_current) - current_target) < 1 else "outside_tolerance"
    if status != "ok":
        return np.nan, actual_current, status
    return potential, actual_current, status


def choose_pair(folder: Optional[str]) -> Dict[str, Optional[str]]:
    if folder is None:
        return {"normal": None, "sr": None}

    ensure_cv50_conversions(folder)

    normal_files = [
        path
        for path in glob.glob(os.path.join(folder, "*_CV_50mVs_Efin_*mVvsRHE.txt"))
        if "_CV_sr_" not in os.path.basename(path)
    ]
    sr_files = glob.glob(os.path.join(folder, "*_CV_sr_50mVs_Efin_*mVvsRHE.txt"))

    normal_files = sorted(normal_files, key=efin_sort_key)
    sr_files = sorted(sr_files, key=efin_sort_key)
    sr_file = sr_files[0] if sr_files else None

    normal_file = None
    if sr_file is not None:
        sr_efin = efin_mV(sr_file)
        matching_normal = [path for path in normal_files if efin_mV(path) == sr_efin]
        if matching_normal:
            normal_file = matching_normal[0]

    if normal_file is None and normal_files:
        normal_file = normal_files[0]

    return {"normal": normal_file, "sr": sr_file}


def build_parent_index() -> Dict[str, Path]:
    index: Dict[str, Path] = {}
    for path in RAW_DATA_DIR.iterdir():
        if not path.is_dir():
            continue
        exp_id = parent_experiment_id(path)
        if exp_id and exp_id not in index:
            index[exp_id] = path
    return index


def find_electrolyte_folder(parent: Optional[Path], electrolyte: str) -> Optional[str]:
    if parent is None:
        return None
    matches = [
        str(path)
        for path in parent.iterdir()
        if path.is_dir() and electrolyte in path.name
    ]
    return sorted(matches)[0] if matches else None


def add_file_results(row: Dict[str, object], label: str, path: Optional[str]) -> None:
    row[f"{label}_file"] = relpath(path)
    row[f"{label}_Efin_mV"] = efin_mV(path) if path else np.nan
    if path is None:
        for target in CURRENT_TARGETS:
            current_label = int(target)
            row[f"eta{current_label}_{label}_V"] = np.nan
            row[f"actual_current{current_label}_{label}_mA_cm2"] = np.nan
            row[f"status{current_label}_{label}"] = "missing_file"
        return

    for target in CURRENT_TARGETS:
        current_label = int(target)
        try:
            eta, actual_current, status = extract_overpotential(path, target)
        except Exception as exc:
            eta, actual_current, status = np.nan, np.nan, f"error: {exc}"
        row[f"eta{current_label}_{label}_V"] = eta
        row[f"actual_current{current_label}_{label}_mA_cm2"] = actual_current
        row[f"status{current_label}_{label}"] = status


def build_table() -> pd.DataFrame:
    recipe = pd.read_csv(RECIPE_CSV)
    recipe = recipe[RECIPE_COLUMNS].copy()
    recipe["Experiment"] = recipe["Experiment"].astype(str).str.lower()
    parent_index = build_parent_index()

    rows = []
    for _, recipe_row in recipe.iterrows():
        exp_id = recipe_row["Experiment"]
        parent = parent_index.get(exp_id)
        row = recipe_row.to_dict()
        row["raw_parent_folder"] = relpath(str(parent)) if parent else ""

        h2_folder = find_electrolyte_folder(parent, "H2KOH")
        ar_folder = find_electrolyte_folder(parent, "ArKOH")
        row["H2KOH_folder"] = relpath(h2_folder)
        row["ArKOH_folder"] = relpath(ar_folder)

        h2_pair = choose_pair(h2_folder)
        ar_pair = choose_pair(ar_folder)

        add_file_results(row, "H2KOH_CV50", h2_pair["normal"])
        add_file_results(row, "H2KOH_CVsr50", h2_pair["sr"])
        add_file_results(row, "ArKOH_CV50", ar_pair["normal"])
        add_file_results(row, "ArKOH_CVsr50", ar_pair["sr"])

        rows.append(row)

    output = pd.DataFrame(rows)
    output = output.sort_values("Experiment", key=experiment_sort_key).reset_index(drop=True)
    output = remove_flagged_experiments(output)
    return output


def remove_flagged_experiments(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["Experiment"] = df["Experiment"].astype(str).str.lower()
    return df[~df["Experiment"].isin(REMOVED_EXPERIMENTS_ABS_Y_LT_0P1)].reset_index(drop=True)


def experiment_index(experiment: object) -> float:
    match = re.search(r"(\d+)", str(experiment))
    return float(match.group(1)) if match else np.nan


def compute_mean_error(df: pd.DataFrame) -> pd.DataFrame:
    out = df[["Experiment"]].copy()
    out["experiment_index"] = out["Experiment"].map(experiment_index)

    for current, columns in ETA_COLUMNS.items():
        values_v = df[columns].apply(pd.to_numeric, errors="coerce")
        signed_mV = values_v * 1000
        abs_mV = values_v.abs() * 1000

        out[f"eta{current}_n"] = values_v.notna().sum(axis=1)
        out[f"eta{current}_mean_signed_mV"] = signed_mV.mean(axis=1, skipna=True)
        out[f"eta{current}_std_signed_mV"] = signed_mV.std(axis=1, skipna=True)
        out[f"eta{current}_mean_abs_mV"] = abs_mV.mean(axis=1, skipna=True)
        out[f"eta{current}_std_abs_mV"] = abs_mV.std(axis=1, skipna=True)

    for gas, current_columns in GAS_ETA_COLUMNS.items():
        for current, columns in current_columns.items():
            values_v = df[columns].apply(pd.to_numeric, errors="coerce")
            signed_mV = values_v * 1000

            out[f"eta{current}_{gas}_n"] = values_v.notna().sum(axis=1)
            out[f"eta{current}_{gas}_mean_signed_mV"] = signed_mV.mean(axis=1, skipna=True)
            out[f"eta{current}_{gas}_std_signed_mV"] = signed_mV.std(axis=1, skipna=True)

    return out.sort_values("experiment_index").reset_index(drop=True)


def load_doe_experiments() -> set[str]:
    doe_path = DATA_DIR / "result_pretrain.csv"
    if not doe_path.exists():
        return set()
    doe = pd.read_csv(doe_path)
    return set(doe["Experiment"].astype(str).str.lower())


def dataset_label(experiment: object, experiment_idx: float, doe_experiments: set[str]) -> str:
    exp = str(experiment).lower()
    if exp in doe_experiments:
        return "DoE"

    for label, (start, end) in CAMPAIGN_RANGES.items():
        if start <= experiment_idx <= end:
            return label
    return "Other"


def add_dataset_labels(summary: pd.DataFrame) -> pd.DataFrame:
    doe_experiments = load_doe_experiments()
    summary = summary.copy()
    summary["dataset"] = [
        dataset_label(exp, idx, doe_experiments)
        for exp, idx in zip(summary["Experiment"], summary["experiment_index"])
    ]
    return summary


def filter_to_all_ovp_cdl(df: pd.DataFrame) -> pd.DataFrame:
    all_ovp_cdl = pd.read_csv(ALL_OVP_CDL_CSV, usecols=["Experiment"])
    allowed = set(all_ovp_cdl["Experiment"].astype(str).str.lower())

    working = df.copy()
    working["Experiment"] = working["Experiment"].astype(str).str.lower()
    mask = working["Experiment"].isin(allowed)
    print(
        f"[INFO] Filtered CV50 table to All_Ovp_Cdl entries: "
        f"{int(mask.sum())} kept, {int((~mask).sum())} removed"
    )
    return working.loc[mask].reset_index(drop=True)


def output_dir_for_current(current: int) -> Path:
    out_dir = OUTPUT_DIR / f"{current}mA"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def style_axes(ax: plt.Axes) -> None:
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(FRAME_WIDTH)
    ax.tick_params(axis="both", labelsize=12, width=FRAME_WIDTH)


def save_figure(fig: plt.Figure, out_dir: Path, filename: str) -> None:
    for fmt in OUTPUT_FORMATS:
        fig.savefig(out_dir / f"{filename}.{fmt}", dpi=600)


def padded_xlim(plot_df: pd.DataFrame, group_slug: str) -> tuple[float, float]:
    if group_slug.startswith("campaign"):
        axis_max = CAMPAIGN_AXIS_MAX.get(group_slug, 120)
        return 1 - X_PAD, axis_max + X_PAD

    x = plot_df["plot_index"].dropna()
    if x.empty:
        return 0, 1
    return x.min() - X_PAD, x.max() + X_PAD


def set_x_axis(ax: plt.Axes, plot_df: pd.DataFrame, group_slug: str) -> None:
    ax.set_xlim(*padded_xlim(plot_df, group_slug))
    if group_slug.startswith("campaign"):
        axis_max = CAMPAIGN_AXIS_MAX.get(group_slug, 120)
        if axis_max == 160:
            ax.set_xticks([1, 40, 80, 120, 160])
        else:
            ax.set_xticks([1, 30, 60, 90, 120])


def set_y_axis(ax: plt.Axes) -> None:
    ax.set_ylim(*Y_LIMITS)
    ax.set_yticks(Y_TICKS)
    ax.set_yticklabels([f"{tick:.1f}" for tick in Y_TICKS])


def assign_plot_index(plot_df: pd.DataFrame, group_slug: str) -> pd.DataFrame:
    plot_df = plot_df.sort_values("experiment_index").copy()
    if group_slug.startswith("campaign"):
        plot_df["plot_index"] = np.arange(1, len(plot_df) + 1)
    else:
        plot_df["plot_index"] = plot_df["experiment_index"]
    return plot_df


def figure_size_for_group(group_slug: str) -> tuple[float, float]:
    if group_slug == "doe":
        return DOE_FIGSIZE
    if group_slug.startswith("campaign"):
        return CAMPAIGN_FIGSIZE
    return DEFAULT_FIGSIZE


def color_for_group(group_slug: str, current: int) -> str:
    if group_slug == "doe":
        return DOE_COLOR
    if group_slug in CAMPAIGN_COLORS:
        return CAMPAIGN_COLORS[group_slug]
    return CURRENT_COLORS[current]


def colors_for_rows(plot_df: pd.DataFrame, group_slug: str, current: int) -> list[str]:
    return [color_for_group(group_slug, current)] * len(plot_df)


def plot_replicate_lines_current(
    data: pd.DataFrame,
    gas: str,
    current: int,
    filename: str,
    figsize: tuple[float, float],
    group_slug: str,
) -> None:
    cols = GAS_ETA_COLUMNS[gas][current]
    keep_cols = ["experiment_index", *cols]
    if "dataset" in data.columns:
        keep_cols.append("dataset")
    plot_df = data[keep_cols].copy()
    plot_df["plot_index"] = data["plot_index"] if "plot_index" in data.columns else data["experiment_index"]
    plot_df[cols] = -plot_df[cols].apply(pd.to_numeric, errors="coerce")
    plot_df = plot_df.dropna(subset=["experiment_index"])
    active = plot_df[plot_df[cols].notna().any(axis=1)]

    fig, ax = plt.subplots(figsize=figsize, constrained_layout=True)
    both = plot_df.dropna(subset=cols)
    if not both.empty:
        y_min = both[cols].min(axis=1)
        y_max = both[cols].max(axis=1)
        colors = colors_for_rows(both, group_slug, current)
        ax.vlines(
            both["plot_index"],
            y_min,
            y_max,
            colors=colors,
            linewidth=0.45,
            alpha=1.0,
        )
        ax.scatter(
            both["plot_index"],
            both[cols[0]],
            s=2.2,
            c=colors,
            linewidths=0,
            zorder=3,
        )
        ax.scatter(
            both["plot_index"],
            both[cols[1]],
            s=2.2,
            c=colors,
            linewidths=0,
            zorder=3,
        )

    single = plot_df[plot_df[cols].notna().sum(axis=1) == 1]
    if not single.empty:
        single_y = single[cols].bfill(axis=1).iloc[:, 0]
        colors = colors_for_rows(single, group_slug, current)
        ax.scatter(
            single["plot_index"],
            single_y,
            s=2.2,
            c=colors,
            linewidths=0,
            zorder=3,
        )

    ax.set_xlabel(" ", fontsize=12)
    ax.set_ylabel(" ", fontsize=12)
    set_x_axis(ax, active, group_slug)
    set_y_axis(ax)
    style_axes(ax)
    save_figure(fig, output_dir_for_current(current), filename)
    plt.close(fig)


def make_plot_groups(summary: pd.DataFrame, plot_data: pd.DataFrame) -> list[tuple[str, pd.DataFrame, pd.DataFrame]]:
    groups = []
    for group_name in ["DoE", "Campaign1", "Campaign2", "Campaign3", "Campaign4", "Campaign5"]:
        group_df = summary[summary["dataset"] == group_name].copy()
        if group_df.empty:
            continue
        group_plot_data = plot_data[plot_data["dataset"] == group_name].copy()
        group_slug = group_name.lower()
        groups.append(
            (
                group_slug,
                assign_plot_index(group_df, group_slug),
                assign_plot_index(group_plot_data, group_slug),
            )
        )
    return groups


def main() -> None:
    df = filter_to_all_ovp_cdl(build_table())
    summary = add_dataset_labels(compute_mean_error(df))
    plot_data = df.copy()
    plot_data["Experiment"] = plot_data["Experiment"].astype(str).str.lower()
    plot_data["experiment_index"] = plot_data["Experiment"].map(experiment_index)
    plot_data = add_dataset_labels(plot_data)

    plt.rcParams["lines.linewidth"] = 1
    plt.rcParams.update(
        {
            "font.family": "Arial",
            "font.size": 12,
            "axes.linewidth": FRAME_WIDTH,
            "xtick.major.width": FRAME_WIDTH,
            "ytick.major.width": FRAME_WIDTH,
            "ps.fonttype": 42,
        }
    )

    for current in CURRENTS_TO_PLOT:
        for group_slug, _, group_plot_data in make_plot_groups(summary, plot_data):
            figsize = figure_size_for_group(group_slug)
            for gas in ["h2", "ar"]:
                plot_replicate_lines_current(
                    group_plot_data,
                    gas,
                    current,
                    f"cv50_{gas}_signed_{group_slug}",
                    figsize,
                    group_slug,
                )

    print(f"[DONE] Wrote 50 mA figures to {OUTPUT_DIR / '50mA'}")
    print(f"[INFO] rows={len(df)}")


if __name__ == "__main__":
    main()
