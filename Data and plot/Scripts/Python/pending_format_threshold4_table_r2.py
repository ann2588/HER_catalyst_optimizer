"""Format threshold-4 pseudo-replicate pairs like the manuscript Table R1."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = ROOT / "Scripts" / "Python"
OUTPUT_ROOT = ROOT / "Data"
PAIR_SOURCE = OUTPUT_ROOT / "pending_Table_R2_stage2_pseudoreplicates_threshold4.csv"

RECIPE_COLUMNS = [
    "V", "Cr", "Mg", "Fe", "Co", "Ni", "Cu", "S", "Se", "P", "blank",
    "Volt", "Time",
]
ETA50 = "Overpotential V at 50.0 mA cm-2"
EXCLUDED_EXPERIMENTS = {"exp830", "exp843"}
OPTIMAL_IDS = {
    1: "exp715",
    2: "exp839",
    3: "exp931",
    4: "exp1031",
}


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


def number(value: str) -> float:
    return float(value)


def display_number(value: float) -> str:
    rounded = round(value)
    if abs(value - rounded) < 1e-9:
        return str(int(rounded))
    return f"{value:.2f}".rstrip("0").rstrip(".")


lookup = {
    (campaign, row["Experiment"]): row
    for campaign in range(1, 5)
    for row in stage2_rows(campaign)
}
all_campaign_rows = {
    row["Experiment"]: row
    for row in read_rows(ROOT / "Data" / "result_all_campaign.csv")
}

pair_rows = read_rows(PAIR_SOURCE)
unique_pairs: dict[tuple[int, str, str], float] = {}
for row in pair_rows:
    campaign = int(row["Campaign"])
    left, right = sorted([row["Experiment"], row["Nearest_pseudo_experiment"]])
    key = (campaign, left, right)
    distance = float(row["Distance_hardware_steps"])
    unique_pairs[key] = min(distance, unique_pairs.get(key, distance))

formatted: list[dict[str, object]] = []
retained_pairs = [
    item
    for item in sorted(unique_pairs.items())
    if item[0][1] not in EXCLUDED_EXPERIMENTS
    and item[0][2] not in EXCLUDED_EXPERIMENTS
]
pair_index = 0
for campaign in range(1, 5):
    optimal_id = OPTIMAL_IDS[campaign]
    optimal_recipe = all_campaign_rows[optimal_id]
    optimal_output: dict[str, object] = {
        "Pseudo-replicate ID": f"OPT-C{campaign}",
        "# of evaluations": 1,
        "Experiment ID": optimal_id,
        "Campaign #": campaign,
        "Distance (hardware steps)": "",
    }
    for column in RECIPE_COLUMNS:
        optimal_output[column] = display_number(number(optimal_recipe[column]))
    optimal_output["|η50| (mV)"] = round(
        abs(number(optimal_recipe[ETA50])) * 1000, 2
    )
    formatted.append(optimal_output)

    campaign_pairs = [
        item for item in retained_pairs if item[0][0] == campaign
    ]
    for (pair_campaign, left, right), distance in campaign_pairs:
        pair_index += 1
        recipes = [
            lookup[(pair_campaign, left)],
            lookup[(pair_campaign, right)],
        ]
        for recipe in recipes:
            output: dict[str, object] = {
                "Pseudo-replicate ID": f"PREP-{pair_index:03d}",
                "# of evaluations": 2,
                "Experiment ID": recipe["Experiment"],
                "Campaign #": campaign,
                "Distance (hardware steps)": display_number(distance),
            }
            for column in RECIPE_COLUMNS:
                output[column] = display_number(number(recipe[column]))
            output["|η50| (mV)"] = round(
                abs(number(recipe[ETA50])) * 1000, 2
            )
            formatted.append(output)

output_path = OUTPUT_ROOT / "pending_Table_R2_threshold4_recipes_separate_rows.csv"
with output_path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(formatted[0]))
    writer.writeheader()
    writer.writerows(formatted)

print(f"Optimal recipes: {len(OPTIMAL_IDS)}")
print(f"Qualifying direct pseudo-replicate pairs: {pair_index}")
print(f"Recipe rows: {len(formatted)}")
print(output_path)
