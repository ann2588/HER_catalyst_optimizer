import glob
import os
import re
from pathlib import Path
from typing import Optional

MPL_CACHE_DIR = Path("/tmp/her-catalyst-optimizer-mpl-cache")
MPL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MPL_CACHE_DIR))
os.environ.setdefault("XDG_CACHE_HOME", str(MPL_CACHE_DIR))

import matplotlib

matplotlib.use("Agg")
from matplotlib import font_manager
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[2]

FIGURE_METADATA = {
    "stable_id": "Fig_replicate",
    "script": __file__,
    "data_keys": ["Replica_data"],
    "figure_type": "SI",
}


def get_output_dir(meta: dict[str, object]) -> Path:
    fig_base = "Figures_SI" if meta["figure_type"] == "SI" else "Figures_Main"
    outdir = PROJECT_ROOT / fig_base / str(meta["stable_id"])
    outdir.mkdir(parents=True, exist_ok=True)
    return outdir


DATA_DIR = PROJECT_ROOT / "Data"
REPLICA_DIR = DATA_DIR / "Replica data"
RECIPE_INDEX_CSV = REPLICA_DIR / "recipeindex.csv"
OUTPUT_DIR = get_output_dir(FIGURE_METADATA)
OUTPUT_STEM = "replica_eta50"
OUTPUT_FORMATS = ("png", "eps")

PH_KOH = 13.7
AG_AGCL_OFFSET_V = 0.205
RHE_SLOPE_V_PER_PH = 0.059
GCE_AREA_CM2 = 0.0706858
CURRENT_TARGET = 50.0
CURRENT_TOLERANCE = 1.0
FRAME_WIDTH_PT = 0.5
REPLICA_VALUE_COLS = ["overpotential50_CV50_V", "overpotential50_CVsr50_V"]


def setup_arial() -> None:
    candidates = [
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
        Path("/Library/Fonts/Arial.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
    ]
    arial_path = next((path for path in candidates if path.exists()), None)
    if arial_path is not None:
        font_manager.fontManager.addfont(str(arial_path))
    plt.rcParams.update(
        {
            "font.family": "Arial",
            "font.sans-serif": ["Arial"],
            "font.size": 12,
            "axes.labelsize": 12,
            "axes.linewidth": FRAME_WIDTH_PT,
            "legend.fontsize": 8,
            "xtick.labelsize": 12,
            "ytick.labelsize": 12,
            "xtick.major.width": FRAME_WIDTH_PT,
            "ytick.major.width": FRAME_WIDTH_PT,
            "mathtext.fontset": "custom",
            "mathtext.rm": "Arial",
            "mathtext.it": "Arial:italic",
            "mathtext.bf": "Arial:bold",
            "ps.fonttype": 42,
        }
    )


def experiment_number(value: object) -> Optional[int]:
    match = re.search(r"exp(\d+)", str(value), re.I)
    return int(match.group(1)) if match else None


def recipe_parts(value: object) -> tuple[str, float]:
    match = re.match(r"(exp\d+)_([0-9]+)$", str(value).strip(), re.I)
    if not match:
        return str(value), np.nan
    return match.group(1).lower(), float(match.group(2))


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


def ensure_cv50_conversions(folder: str) -> None:
    raw_files = []
    for pattern in ["*_CV_50mVs_Efin_*.txt", "*_CV_sr_50mVs_Efin_*.txt"]:
        raw_files.extend(glob.glob(os.path.join(folder, pattern)))
    raw_files = [path for path in raw_files if not path.endswith("vsRHE.txt")]
    for raw_file in raw_files:
        convert_raw_cv_to_rhe(raw_file)


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
        if sweep["Current mA cm-2"].abs().max() >= current_target - CURRENT_TOLERANCE
    ]
    if reachable:
        return reachable[-1]
    return sweeps[-1]


def extract_overpotential(path: str, current_target: float = CURRENT_TARGET) -> tuple[float, float, str]:
    df = read_rhe_curve(path)
    section = select_cathodic_sweep(df, current_target)
    abs_current = section["Current mA cm-2"].abs()
    closest_idx = (abs_current - current_target).abs().idxmin()
    actual_current = section.loc[closest_idx, "Current mA cm-2"]
    potential = section.loc[closest_idx, "Potential V vs RHE"]
    status = "ok" if abs(abs(actual_current) - current_target) < CURRENT_TOLERANCE else "outside_tolerance"
    if status != "ok":
        return np.nan, actual_current, status
    return potential, actual_current, status


def choose_h2koh_pair(folder: str) -> dict[str, Optional[str]]:
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
        matches = [path for path in normal_files if efin_mV(path) == sr_efin]
        if matches:
            normal_file = matches[0]
    if normal_file is None and normal_files:
        normal_file = normal_files[0]

    return {"CV50": normal_file, "CVsr50": sr_file}


def find_h2koh_folder(replica_folder: Path) -> Optional[Path]:
    matches = [path for path in replica_folder.iterdir() if path.is_dir() and "H2KOH" in path.name]
    return sorted(matches)[0] if matches else None


def load_recipe_index() -> pd.DataFrame:
    recipes = pd.read_csv(RECIPE_INDEX_CSV)
    recipes["collection_exp_index"] = pd.to_numeric(recipes["exp"], errors="coerce").astype("Int64")
    parts = recipes["Experiment"].map(recipe_parts)
    recipes = recipes.rename(columns={"Experiment": "replica_label"})
    recipes["source_experiment"] = [part[0] for part in parts]
    recipes["replica_index"] = [part[1] for part in parts]
    return recipes[["collection_exp_index", "replica_label", "source_experiment", "replica_index"]]


def build_results() -> pd.DataFrame:
    recipes = load_recipe_index()
    records = []

    for replica_folder in sorted(REPLICA_DIR.glob("*-exp*"), key=lambda path: experiment_number(path.name) or 10**9):
        collection_index = experiment_number(replica_folder.name)
        if collection_index is None:
            continue
        recipe = recipes[recipes["collection_exp_index"] == collection_index]
        recipe_row = recipe.iloc[0].to_dict() if not recipe.empty else {}

        h2_folder = find_h2koh_folder(replica_folder)
        record = {
            "collection_exp_index": collection_index,
            "collection_folder": relpath(str(replica_folder)),
            "h2koh_folder": relpath(str(h2_folder)) if h2_folder else "",
            **recipe_row,
        }

        if h2_folder is None:
            for label in ["CV50", "CVsr50"]:
                record[f"eta50_{label}_V"] = np.nan
                record[f"overpotential50_{label}_V"] = np.nan
                record[f"actual_current50_{label}_mA_cm2"] = np.nan
                record[f"status50_{label}"] = "missing_h2koh_folder"
            records.append(record)
            continue

        pair = choose_h2koh_pair(str(h2_folder))
        for label, path in pair.items():
            if path is None:
                eta, actual_current, status = np.nan, np.nan, "missing_file"
            else:
                try:
                    eta, actual_current, status = extract_overpotential(path)
                except Exception as exc:
                    eta, actual_current, status = np.nan, np.nan, f"error: {exc}"
            record[f"eta50_{label}_V"] = eta
            record[f"overpotential50_{label}_V"] = -eta if pd.notna(eta) else np.nan
            record[f"actual_current50_{label}_mA_cm2"] = actual_current
            record[f"status50_{label}"] = status
        records.append(record)

    return pd.DataFrame(records).sort_values("collection_exp_index").reset_index(drop=True)


def first_valid(series: pd.Series) -> object:
    values = series.dropna()
    return values.iloc[0] if not values.empty else np.nan


def sem(series: pd.Series) -> float:
    values = series.dropna()
    if len(values) < 2:
        return np.nan
    return float(values.std(ddof=1) / np.sqrt(len(values)))


def prepare_replica_values(df: pd.DataFrame) -> pd.DataFrame:
    prepared = df.copy()
    for col in REPLICA_VALUE_COLS + ["replica_index"]:
        prepared[col] = pd.to_numeric(prepared[col], errors="coerce")

    prepared["replica_mean_overpotential50_V"] = prepared[REPLICA_VALUE_COLS].mean(axis=1, skipna=True)
    return prepared


def build_duplicate_points(df: pd.DataFrame) -> pd.DataFrame:
    source_order = {
        source: index
        for index, source in enumerate(df["source_experiment"].drop_duplicates(), start=1)
    }
    point_rows = []
    for row in df.itertuples(index=False):
        value = row.replica_mean_overpotential50_V
        point_rows.append(
            {
                "source_order": source_order[row.source_experiment],
                "source_experiment": row.source_experiment,
                "point_label": row.replica_label,
                "replica_index": row.replica_index,
                "overpotential50_V": value,
            }
        )

    points = pd.DataFrame(point_rows)
    return points.sort_values(["source_order", "replica_index"], kind="stable").reset_index(drop=True)


def build_duplicate_stats(points: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for source_experiment, group in points.groupby("source_experiment", sort=False):
        values = group["overpotential50_V"].dropna()
        rows.append(
            {
                "source_experiment": source_experiment,
                "point_count": int(values.count()),
                "mean_overpotential50_V": values.mean() if not values.empty else np.nan,
                "sd_overpotential50_V": values.std(ddof=1) if len(values) > 1 else np.nan,
                "sem_overpotential50_V": sem(values),
            }
        )
    return pd.DataFrame(rows)


def plot_replicates(points: pd.DataFrame, stats: pd.DataFrame) -> None:
    plot_stats = stats.copy()
    plot_stats["x"] = np.arange(1, len(plot_stats) + 1)
    x_lookup = dict(zip(plot_stats["source_experiment"], plot_stats["x"]))

    plot_points = points.copy()
    plot_points["x"] = plot_points["source_experiment"].map(x_lookup)
    plot_points["jitter"] = 0.0
    for _, group in plot_points.groupby("source_experiment", sort=False):
        if len(group) > 1:
            plot_points.loc[group.index, "jitter"] = np.linspace(-0.12, 0.12, len(group))

    fig, ax_value = plt.subplots(figsize=(7.2, 2.5), constrained_layout=True)

    ax_value.scatter(
        plot_points["x"] + plot_points["jitter"],
        plot_points["overpotential50_V"],
        s=16,
        color="#9a9a9a",
        linewidths=0,
        label="Replicates",
        zorder=2,
    )
    ax_value.errorbar(
        plot_stats["x"],
        plot_stats["mean_overpotential50_V"],
        yerr=plot_stats["sd_overpotential50_V"].fillna(0),
        fmt="o",
        markersize=4.0,
        markerfacecolor="#2f6f9f",
        markeredgecolor="#2f6f9f",
        ecolor="#2f6f9f",
        elinewidth=1.0,
        capsize=2.5,
        capthick=1.0,
        label="Mean +- SD",
        zorder=4,
    )
    ax_value.set_ylabel(r"$|\eta_{50}|$ (V vs. RHE)")
    ax_value.set_xlabel("Experiment ID", fontsize=12)
    ax_value.set_xticks(plot_stats["x"])
    experiment_ids = plot_stats["source_experiment"].astype(str).str.replace(r"^exp", "", regex=True)
    ax_value.set_xticklabels(experiment_ids, rotation=90, ha="center", va="top")
    ax_value.legend(frameon=False, loc="best")
    ax_value.set_ylim(0.0, 1.0)

    ax_value.grid(False)
    for spine in ax_value.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(FRAME_WIDTH_PT)
    ax_value.tick_params(width=FRAME_WIDTH_PT, length=3)

    for fmt in OUTPUT_FORMATS:
        fig.savefig(OUTPUT_DIR / f"{OUTPUT_STEM}.{fmt}", dpi=600)
    plt.close(fig)


def main() -> None:
    setup_arial()
    results = build_results()
    replica_df = prepare_replica_values(results)
    points = build_duplicate_points(replica_df)
    stats = build_duplicate_stats(points)
    plot_replicates(points, stats)

    ok_count = int(results[["status50_CV50", "status50_CVsr50"]].eq("ok").sum().sum())
    print(f"[DONE] wrote {OUTPUT_DIR / OUTPUT_STEM}.{{png,eps}}")
    print(f"[INFO] collected_folders={len(results)} ok_eta_values={ok_count}")
    print(f"[INFO] replicate_groups={len(stats)} replicate_points={len(points)}")


if __name__ == "__main__":
    main()
