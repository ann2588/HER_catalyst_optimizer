"""Identify exact and hardware-resolution pseudo-replicates in Stage 2.

Campaign 1's historical ``stage2_only`` CSV also contains the Stage 1 rows.
Those rows are removed by experiment ID before the four campaigns are pooled.

Distance is the Chebyshev (maximum-coordinate) distance after expressing each
recipe coordinate in instrument increments:
  * composition/blank channels: 1 unit
  * deposition voltage: 0.1 V
  * deposition time: 1 s

The current detail-table threshold is 4, meaning <=4 composition units,
<=0.4 V, and <=4 s in every coordinate. Exact repeats (distance 0) are
reported separately and are excluded from the pseudo-replicate percentage.
"""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = ROOT / "Scripts" / "Python"
OUTPUT_ROOT = ROOT / "Data"

RECIPE_COLUMNS = [
    "V", "Cr", "Fe", "Co", "Ni", "Cu", "Mg", "S", "Se", "P", "blank",
    "Volt", "Time",
]
RESOLUTIONS = [1.0] * 11 + [0.1, 1.0]
THRESHOLD_STEPS = 4.0


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def stage2_rows(campaign: int) -> list[dict[str, str]]:
    folder = DATA_ROOT / f"Fig_hessian_full_campaign{campaign}" / "Set 2"
    rows = read_rows(folder / f"Campaign{campaign}_stage2_only.csv")
    if campaign == 1:
        stage1_ids = {
            row["Experiment"]
            for row in read_rows(folder / "Campaign1_stage1_only.csv")
        }
        rows = [row for row in rows if row["Experiment"] not in stage1_ids]
    return rows


def vector(row: dict[str, str]) -> list[float]:
    return [float(row[column]) for column in RECIPE_COLUMNS]


def distance_steps(left: list[float], right: list[float]) -> float:
    return max(
        abs(a - b) / resolution
        for a, b, resolution in zip(left, right, RESOLUTIONS)
    )


def clean_number(value: float) -> float | int:
    rounded = round(value)
    return int(rounded) if abs(value - rounded) < 1e-9 else round(value, 6)


campaigns = {campaign: stage2_rows(campaign) for campaign in range(1, 5)}
detail_rows: list[dict[str, object]] = []
nearest_distances: list[float] = []

for campaign, rows in campaigns.items():
    vectors = [vector(row) for row in rows]
    for index, (row, current) in enumerate(zip(rows, vectors)):
        candidates = [
            (distance_steps(current, other), other_index)
            for other_index, other in enumerate(vectors)
            if other_index != index
        ]
        nearest_distance = min(distance for distance, _ in candidates)
        nearest_distances.append(nearest_distance)
        if not (nearest_distance > 1e-9 and nearest_distance <= THRESHOLD_STEPS + 1e-9):
            continue

        distance, nearest_index = min(candidates, key=lambda item: (item[0], item[1]))
        nearest = vectors[nearest_index]
        nearest_row = rows[nearest_index]
        pair = sorted([row["Experiment"], nearest_row["Experiment"]])
        output: dict[str, object] = {
            "Pseudo_group": f"C{campaign}:{pair[0]}-{pair[1]}",
            "Campaign": campaign,
            "Experiment": row["Experiment"],
            "Nearest_pseudo_experiment": nearest_row["Experiment"],
            "Distance_hardware_steps": clean_number(distance),
        }
        for column, value in zip(RECIPE_COLUMNS, current):
            output[f"{column}_value"] = clean_number(value)
        for column, value, comparison in zip(RECIPE_COLUMNS, current, nearest):
            output[f"Delta_{column}"] = clean_number(value - comparison)
        detail_rows.append(output)

total = sum(len(rows) for rows in campaigns.values())
exact_count = sum(distance <= 1e-9 for distance in nearest_distances)
pseudo_count = len(detail_rows)

detail_path = OUTPUT_ROOT / "pending_Table_R2_stage2_pseudoreplicates_threshold4.csv"
with detail_path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(detail_rows[0]))
    writer.writeheader()
    writer.writerows(detail_rows)

sensitivity_path = OUTPUT_ROOT / "pending_Table_R2_threshold_sensitivity.csv"
with sensitivity_path.open("w", newline="", encoding="utf-8") as handle:
    fieldnames = [
        "Threshold_hardware_steps",
        "Max_composition_difference",
        "Max_voltage_difference_V",
        "Max_time_difference_s",
        "Exact_repeat_evaluations",
        "Exact_repeat_percent",
        "Slight_only_evaluations",
        "Slight_only_percent",
        "Exact_plus_slight_evaluations",
        "Exact_plus_slight_percent",
        "Total_stage2_evaluations",
    ]
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    for threshold in range(0, 6):
        slight = sum(
            distance > 1e-9 and distance <= threshold + 1e-9
            for distance in nearest_distances
        )
        writer.writerow({
            "Threshold_hardware_steps": threshold,
            "Max_composition_difference": threshold,
            "Max_voltage_difference_V": round(threshold * 0.1, 1),
            "Max_time_difference_s": threshold,
            "Exact_repeat_evaluations": exact_count,
            "Exact_repeat_percent": exact_count / total,
            "Slight_only_evaluations": slight,
            "Slight_only_percent": slight / total,
            "Exact_plus_slight_evaluations": exact_count + slight,
            "Exact_plus_slight_percent": (exact_count + slight) / total,
            "Total_stage2_evaluations": total,
        })

print(f"Stage 2 evaluations: {total}")
print(f"Exact repeats: {exact_count}/{total} = {exact_count / total:.2%}")
print(
    f"Slight-only at {THRESHOLD_STEPS:g} steps: "
    f"{pseudo_count}/{total} = {pseudo_count / total:.2%}"
)
print(detail_path)
print(sensitivity_path)
