# HER Optimizer Platform Code

This repository contains the platform code for the autonomous hydrogen evolution reaction (HER) electrocatalyst optimization system reported in the associated article (DOI pending).

For the complete experimental context, see Method S2-S5 in the supporting information. Those sections describe the hardware design, software design, experimental workflow, and closed-loop optimization algorithm.

## Overview

The platform prepares multicomponent electrocatalyst recipes, controls the liquid-handling and electrochemical hardware, processes HER electrochemical data, and selects new experimental conditions for autonomous closed-loop optimization.

The search space used in the platform includes transition-metal cations, anions, and a blank/negative-control channel:

- Metals: V, Cr, Mg, Fe, Co, Ni, Cu
- Anions: S, Se, P
- Electrochemical variables: electrodeposition voltage and time

## Requirements

Install the Python package requirements with:

```bash
pip install -r requirements.txt
```

The core Python dependencies are listed in `requirements.txt`. The platform also requires hardware-specific drivers/modules for the connected instruments:

- CH Instruments CHI760E software, with `chi760e.exe` accessible from `CHI760E_PATH`
- IKA magnetic stirrer Python interface (`ika.magnetic_stirrer`)
- Ismatec pump Python interface (`ismatec.peristaltic_pump`)
- Alicat mass-flow-controller interface (`alicat`)
- PySerial-compatible serial ports for valves and other devices

Some hardware interfaces may need vendor-specific installation steps depending on the control computer.

## Configuration

Set hardware COM ports in:

```text
Utilities/portaccess.py
```

This file defines the magnetic stirrer, pumps, valves, and MFC ports used by the platform. Update these values before running hardware tests or closed-loop experiments.

Optional environment variables:

```bash
export HER_DATA_PATH="/path/to/save/data"
export HER_CAMPAIGN_NAME="campaign_name"
export CHI760E_PATH="C:/chi"
export HER_SLACK_BOT_PATH="/path/to/Utilities/slack-bot.py"
```

If these are not set, the code uses repo-relative defaults where possible.

## Hardware Testing

Use the scripts in:

```text
Hardwaretesting/
```

for connection and operation tests of the pumps, valves, stirrer, titration module, and related hardware. Potentiostat test scripts are in:

```text
pytentiostats/
```

Run these tests before starting an unattended campaign.

## Running Experiments

Use the following entry points:

- `Closed-Loop-DoE.py`: runs a closed-loop experimental workflow from an existing recipe/DoE table such as `batch_pretrain_doe.csv`.
- `Closed-Loop_campaign.py`: runs the autonomous closed-loop campaign, including experiment execution, overpotential extraction, model update, and next-recipe selection.

Typical workflow:

1. Edit `Utilities/portaccess.py` for the control computer.
2. Confirm all hardware connections with scripts in `Hardwaretesting/` and `pytentiostats/`.
3. Set `HER_DATA_PATH`, `HER_CAMPAIGN_NAME`, and `CHI760E_PATH` as needed.
4. Run `Closed-Loop-DoE.py` for a predefined recipe campaign, or `Closed-Loop_campaign.py` for autonomous optimization.

## Data Processing

Data processing utilities are in:

```text
DataProcessing/
```

`DataProcessing/OverpotentialExtraction.py` extracts HER overpotentials from generated CV/LSV files and writes campaign summary CSV files used by the optimization loop.

## Notes

This code controls real laboratory hardware and gas/liquid handling. Verify port assignments, tubing, valve positions, electrolyte reservoirs, waste lines, and safety interlocks before running any automated sequence.

