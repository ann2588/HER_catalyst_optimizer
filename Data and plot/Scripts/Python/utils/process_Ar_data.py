import argparse
import glob
import os
import re
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.stats import linregress


SCRIPT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
DATA_ROOT = os.path.join(PROJECT_ROOT, "Data")
RAW_DATA_ROOT = os.path.join(DATA_ROOT, "All data")
RECIPE_CSV = os.path.join(DATA_ROOT, "result_all_campaign.csv")

OUTPUT_FILES = {
    "overpotential": os.path.join(DATA_ROOT, "HER_Overpotentials_all_campaign_Ar.csv"),
    "tafel": os.path.join(DATA_ROOT, "Tafel_Analysis_all_campaign_Ar.csv"),
    "capacitance": os.path.join(DATA_ROOT, "Pseudo_Capacitance_fw_full_Ar.csv"),
    "ovp_cdl": os.path.join(DATA_ROOT, "Merged_ovp_cdl_full_Ar.csv"),
    "merged": os.path.join(DATA_ROOT, "merged_all_Ar.csv"),
}

PH_KOH = 13.7
AG_AGCL_OFFSET_V = 0.205
RHE_SLOPE_V_PER_PH = 0.059
GCE_AREA_CM2 = 0.0706858
ECSA_TARGET_V = -0.15

CURRENT_TARGETS = [round(x, 1) for x in np.arange(0.5, 10.5, 0.5)] + [20.0, 30.0, 40.0, 50.0]
FINAL_OVP_TARGETS = [2.0, 10.0, 20.0, 30.0, 40.0, 50.0]


def experiment_sort_key(experiment: object) -> int:
    match = re.search(r"(\d+)", str(experiment))
    return int(match.group(1)) if match else 10**9


def experiment_id_from_path(path: str) -> str:
    parent = os.path.basename(os.path.dirname(path))
    parent_match = re.search(r"(exp\d+)", parent, re.I)
    if parent_match:
        return parent_match.group(1).lower()

    basename = os.path.basename(path)
    match = re.match(r"(exp\d+)", basename, re.I)
    if match:
        return match.group(1).lower()
    match = re.search(r"(exp\d+)", basename, re.I)
    if match:
        return match.group(1).lower()
    raise ValueError(f"Cannot infer experiment id from {path}")


def relpath(path: Optional[str]) -> str:
    if not path:
        return ""
    return os.path.relpath(path, PROJECT_ROOT).replace(os.sep, "/")


def efin_sort_key(path: str) -> Tuple[int, str]:
    match = re.search(r"_Efin_(-?\d+)mV", os.path.basename(path))
    return (int(match.group(1)) if match else 10**9, path)


def scan_rate_from_name(path: str) -> Optional[int]:
    match = re.search(r"sr_(\d+)mVs", os.path.basename(path))
    return int(match.group(1)) if match else None


def find_header_line(path: str, marker: str) -> Optional[int]:
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

    header_line = find_header_line(raw_file, "Potential/V")
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


def ensure_arkoh_conversions(arkoh_dir: str, force: bool = False) -> int:
    raw_files = [
        path
        for path in glob.glob(os.path.join(arkoh_dir, "*CV*mV.txt"))
        if not path.endswith("vsRHE.txt")
    ]
    converted = 0
    for raw_file in raw_files:
        before_exists = os.path.exists(raw_file[:-4] + "vsRHE.txt")
        out = convert_raw_cv_to_rhe(raw_file, force=force)
        if out and (force or not before_exists):
            converted += 1
    return converted


def read_rhe_curve(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [str(col).strip() for col in df.columns]

    combined_cols = [
        col for col in df.columns if "Potential V vs RHE" in col and "Current" in col and "," in col
    ]
    if combined_cols:
        split = df[combined_cols[0]].astype(str).str.split(",", expand=True)
        df = pd.DataFrame(
            {
                "Potential V vs RHE": pd.to_numeric(split[0], errors="coerce"),
                "Current mA cm-2": pd.to_numeric(split[1], errors="coerce"),
            }
        )
    else:
        potential_col = next((col for col in df.columns if col.strip() == "Potential V vs RHE"), None)
        current_col = next((col for col in df.columns if col.strip() in {"Current mA cm-2", "Current mA/cm2"}), None)
        if potential_col is None or current_col is None:
            raise ValueError(f"Cannot find RHE/current columns in {path}")
        df = pd.DataFrame(
            {
                "Potential V vs RHE": pd.to_numeric(df[potential_col], errors="coerce"),
                "Current mA cm-2": pd.to_numeric(df[current_col], errors="coerce"),
            }
        )

    return df.dropna(subset=["Potential V vs RHE", "Current mA cm-2"]).reset_index(drop=True)


def split_sections(df: pd.DataFrame, section_count: int = 6) -> List[pd.DataFrame]:
    bounds = np.linspace(0, len(df), section_count + 1, dtype=int)
    sections = []
    for start, end in zip(bounds[:-1], bounds[1:]):
        if end > start:
            sections.append(df.iloc[start:end].reset_index(drop=True))
    return sections


def choose_cv_file(arkoh_dir: str) -> Optional[str]:
    files = glob.glob(os.path.join(arkoh_dir, "*_CV_50mV*mVvsRHE.txt"))
    files = [path for path in files if re.search(r"_Efin_(-?\d+)mVvsRHE\.txt$", os.path.basename(path))]
    if not files:
        return None
    return sorted(files, key=efin_sort_key)[0]


def voltage_from_file(path: Optional[str]) -> str:
    if not path:
        return ""
    match = re.search(r"_Efin_(-?\d+)mV", os.path.basename(path))
    return f"{match.group(1)}mV" if match else ""


def extract_overpotentials(cv_file: str) -> Dict[str, float]:
    df = read_rhe_curve(cv_file)
    sections = split_sections(df)
    if len(sections) < 5:
        raise ValueError("CV curve has fewer than five sections")

    section = sections[4]
    result: Dict[str, float] = {"Voltage_Ar": voltage_from_file(cv_file)}
    abs_current = section["Current mA cm-2"].abs()

    for target in CURRENT_TARGETS:
        closest_idx = (abs_current - target).abs().idxmin()
        if abs(abs_current.loc[closest_idx] - target) < 1:
            result[f"Overpotential V at {target} mA/cm2_Ar"] = section.loc[
                closest_idx, "Potential V vs RHE"
            ]
            result[f"Current Density {target} mA/cm2_Ar"] = section.loc[
                closest_idx, "Current mA cm-2"
            ]
        else:
            result[f"Overpotential V at {target} mA/cm2_Ar"] = np.nan
            result[f"Current Density {target} mA/cm2_Ar"] = np.nan

    result["Overpotential @ 50 mA_Ar"] = result["Overpotential V at 50.0 mA/cm2_Ar"]
    return result


def extract_tafel(cv_file: str) -> Dict[str, float]:
    df = read_rhe_curve(cv_file)
    sections = split_sections(df)
    if len(sections) < 6:
        raise ValueError("CV curve has fewer than six sections")

    section = sections[5].copy()
    section["Log Current Density"] = np.log10(section["Current mA cm-2"].abs())
    filtered = section[
        (section["Log Current Density"] >= 0.6)
        & (section["Log Current Density"] <= 1.5)
    ].replace([np.inf, -np.inf], np.nan)
    filtered = filtered.dropna(subset=["Log Current Density", "Potential V vs RHE"])

    if len(filtered) < 2 or filtered["Log Current Density"].nunique() < 2:
        raise ValueError("Not enough points in Tafel log-current window")

    slope, intercept, r_value, _, _ = linregress(
        filtered["Log Current Density"], filtered["Potential V vs RHE"]
    )
    if not np.isfinite(slope) or slope == 0:
        raise ValueError("Invalid Tafel fit slope")

    return {
        "Tafel Slope (mV dec-1)_Ar": abs(slope * 1000),
        "Exchange Current Density (mA cm-2)_Ar": 10 ** (-intercept / slope),
        "Tafel R^2_Ar": r_value**2,
    }


def extract_ecsa(arkoh_dir: str) -> Dict[str, float]:
    files = []
    for path in glob.glob(os.path.join(arkoh_dir, "*sr_*mVs*mVvsRHE.txt")):
        scan_rate = scan_rate_from_name(path)
        if scan_rate is not None and 50 <= scan_rate <= 900:
            files.append((scan_rate, path))
    files.sort(key=lambda item: item[0])

    if len(files) < 2:
        raise ValueError("Not enough scan-rate CV files for ECSA")

    x_rates = []
    y_currents = []
    for scan_rate, path in files:
        df = read_rhe_curve(path)
        if df.empty:
            continue
        first_half = df.iloc[: int(np.ceil(len(df) / 2))].copy()
        first_half = first_half.sort_values("Potential V vs RHE")
        current_at_target = np.interp(
            ECSA_TARGET_V,
            first_half["Potential V vs RHE"],
            first_half["Current mA cm-2"],
        )
        x_rates.append(scan_rate)
        y_currents.append(current_at_target)

    if len(x_rates) < 2:
        raise ValueError("Not enough valid ECSA points")

    slope, intercept, r_value, _, _ = linregress(x_rates, y_currents)
    return {
        "ECSA voltage_Ar": voltage_from_file(files[0][1]),
        "ECSA target V_Ar": ECSA_TARGET_V,
        "ECSA slope raw_Ar": slope,
        "ECSA intercept_Ar": intercept,
        "ECSA R^2_Ar": r_value**2,
        "Cdl mF cm-2_Ar": -slope * 1000,
        "Ar ECSA file count": len(files),
    }


def iter_arkoh_dirs(raw_data_root: str) -> Iterable[str]:
    parents = [
        os.path.join(raw_data_root, name)
        for name in os.listdir(raw_data_root)
        if os.path.isdir(os.path.join(raw_data_root, name))
    ]
    parents.sort(key=lambda path: experiment_sort_key(os.path.basename(path)))
    for parent in parents:
        for name in sorted(os.listdir(parent)):
            path = os.path.join(parent, name)
            if os.path.isdir(path) and "ArKOH" in name:
                yield path


def process_arkoh_dir(arkoh_dir: str, force_convert: bool = False) -> Dict[str, object]:
    ensure_arkoh_conversions(arkoh_dir, force=force_convert)
    experiment = experiment_id_from_path(arkoh_dir)
    record: Dict[str, object] = {
        "Experiment": experiment,
        "ArKOH folder": relpath(arkoh_dir),
        "Ar processing status": "ok",
    }

    cv_file = choose_cv_file(arkoh_dir)
    record["Ar CV file"] = relpath(cv_file)
    if cv_file is None:
        record["Ar processing status"] = "missing CV"
        return record

    try:
        record.update(extract_overpotentials(cv_file))
    except Exception as exc:
        record["Ar overpotential error"] = str(exc)
        record["Ar processing status"] = "overpotential failed"

    try:
        record.update(extract_tafel(cv_file))
    except Exception as exc:
        record["Ar Tafel error"] = str(exc)
        if record["Ar processing status"] == "ok":
            record["Ar processing status"] = "tafel failed"

    try:
        record.update(extract_ecsa(arkoh_dir))
    except Exception as exc:
        record["Ar ECSA error"] = str(exc)
        if record["Ar processing status"] == "ok":
            record["Ar processing status"] = "ecsa failed"

    return record


def sorted_by_experiment(df: pd.DataFrame) -> pd.DataFrame:
    return df.sort_values("Experiment", key=lambda series: series.map(experiment_sort_key)).reset_index(drop=True)


def load_recipe() -> pd.DataFrame:
    recipe = pd.read_csv(RECIPE_CSV)
    recipe = recipe.iloc[:, :14].copy()
    recipe["Experiment"] = recipe["Experiment"].astype(str).str.lower()
    return sorted_by_experiment(recipe)


def write_outputs(records: List[Dict[str, object]]) -> pd.DataFrame:
    metrics = pd.DataFrame(records)
    metrics["Experiment"] = metrics["Experiment"].astype(str).str.lower()
    metrics = sorted_by_experiment(metrics)

    overpotential_cols = ["Experiment", "Voltage_Ar"]
    for target in CURRENT_TARGETS:
        overpotential_cols.extend(
            [
                f"Overpotential V at {target} mA/cm2_Ar",
                f"Current Density {target} mA/cm2_Ar",
            ]
        )
    metrics.reindex(columns=overpotential_cols).to_csv(OUTPUT_FILES["overpotential"], index=False)

    tafel_cols = [
        "Experiment",
        "Tafel Slope (mV dec-1)_Ar",
        "Exchange Current Density (mA cm-2)_Ar",
        "Tafel R^2_Ar",
    ]
    metrics.reindex(columns=tafel_cols).to_csv(OUTPUT_FILES["tafel"], index=False)

    capacitance_cols = [
        "Experiment",
        "ECSA voltage_Ar",
        "ECSA target V_Ar",
        "ECSA slope raw_Ar",
        "ECSA intercept_Ar",
        "ECSA R^2_Ar",
        "Cdl mF cm-2_Ar",
        "Ar ECSA file count",
    ]
    metrics.reindex(columns=capacitance_cols).to_csv(OUTPUT_FILES["capacitance"], index=False)

    ovp_cdl_cols = ["Experiment", "Overpotential @ 50 mA_Ar", "Cdl mF cm-2_Ar"]
    metrics.reindex(columns=ovp_cdl_cols).to_csv(OUTPUT_FILES["ovp_cdl"], index=False)

    recipe = load_recipe()
    final_metric_cols = [
        "Experiment",
        "Overpotential V at 2.0 mA/cm2_Ar",
        "Overpotential V at 10.0 mA/cm2_Ar",
        "Overpotential V at 20.0 mA/cm2_Ar",
        "Overpotential V at 30.0 mA/cm2_Ar",
        "Overpotential V at 40.0 mA/cm2_Ar",
        "Overpotential @ 50 mA_Ar",
        "Tafel Slope (mV dec-1)_Ar",
        "Exchange Current Density (mA cm-2)_Ar",
        "Tafel R^2_Ar",
        "Cdl mF cm-2_Ar",
        "ECSA R^2_Ar",
        "Ar ECSA file count",
        "Ar processing status",
        "ArKOH folder",
        "Ar CV file",
    ]
    final = recipe.merge(metrics.reindex(columns=final_metric_cols), on="Experiment", how="left")
    final = sorted_by_experiment(final)
    final.to_csv(OUTPUT_FILES["merged"], index=False)
    return final


def process_all(force_convert: bool = False) -> pd.DataFrame:
    records = []
    for index, arkoh_dir in enumerate(iter_arkoh_dirs(RAW_DATA_ROOT), start=1):
        if index % 100 == 0:
            print(f"[INFO] Processed {index} ArKOH folders...")
        records.append(process_arkoh_dir(arkoh_dir, force_convert=force_convert))

    final = write_outputs(records)
    print(f"[DONE] Wrote {OUTPUT_FILES['overpotential']}")
    print(f"[DONE] Wrote {OUTPUT_FILES['tafel']}")
    print(f"[DONE] Wrote {OUTPUT_FILES['capacitance']}")
    print(f"[DONE] Wrote {OUTPUT_FILES['ovp_cdl']}")
    print(f"[DONE] Wrote {OUTPUT_FILES['merged']}")
    print(f"[INFO] Final rows: {len(final)}")
    return final


def main() -> None:
    parser = argparse.ArgumentParser(description="Process ArKOH overpotential, Tafel, and ECSA data.")
    parser.add_argument(
        "--force-convert",
        action="store_true",
        help="Regenerate all ArKOH vsRHE files from raw potentiostat txt files before analysis.",
    )
    args = parser.parse_args()
    process_all(force_convert=args.force_convert)


if __name__ == "__main__":
    main()
