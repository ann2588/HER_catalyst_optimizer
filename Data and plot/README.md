# Figure Generation Pipeline

This repository contains the data, plotting scripts, and generated figure outputs for the manuscript figures in the work "Chemistry-infused bandit framework for interpretable autonomous campaign of electrocatalysis" (DOI pending). Run commands from the project root unless noted otherwise.

```bash
cd "/path/to/Source Code"
```

## Navigate Figures

Use `figure_registry.csv` as the main index for inspection. Each row maps a manuscript figure label to the files needed to inspect or reproduce it:

- `Figure`: manuscript label, such as `Figure3h` or `FigureS13`
- `Figure path`: generated output folder for that figure
- `script path`: plotting script used to generate the figure
- `data path`: input data file or folder used by the script

Example:

```bash
grep "FigureS13" figure_registry.csv
```

Then inspect the listed output folder and source script:

```bash
ls Figures_SI/Fig_ovp_i0_best_so_far
python Scripts/Python/Fig_ovp_i0_best_so_far/make_plot.py
```

`figure_registry.json` contains the same mapping in structured JSON form. If scripts, data IDs, or figure IDs change, regenerate both registry files with:

```bash
python list_figures.py
```

## Reproduce Figures

Install Python dependencies first:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

To reproduce one Python figure, run the script listed in `figure_registry.csv`:

```bash
python Scripts/Python/Fig_ovp_i0_best_so_far/make_plot.py
```

You can also run a Python figure module by stable script ID:

```bash
python run_figure.py Fig_ovp_i0_best_so_far
```

To reproduce all Python figure modules:

```bash
for d in Scripts/Python/*/; do
  case "$d" in *utils*/) continue;;
  esac
  python run_figure.py "$(basename "$d")"
done
```

To reproduce one MATLAB figure, run the MATLAB script listed in `figure_registry.csv`:

```bash
matlab -batch "cd('$PWD/Scripts/MATLAB/Fig_ovp_cdl_allcampaign'); make_plot"
```

If MATLAB is not on `PATH`, use the full application path:

```bash
"/Applications/MATLAB_R2024b.app/bin/matlab" -batch "cd('$PWD/Scripts/MATLAB/Fig_ovp_cdl_allcampaign'); make_plot"
```

To reproduce all MATLAB figures:

```bash
for d in Scripts/MATLAB/*/; do
  matlab -batch "cd('$PWD/$d'); make_plot"
done
```

Generated figures are written to `Figures_Main/` or `Figures_SI/`, based on each script's `FIGURE_METADATA["figure_type"]` or MATLAB metadata block. Most scripts derive their output folder from the stable figure ID at the top of the script.

## Repository Layout

The intended GitHub-facing structure is:

```text
.
├── Data/                  # Input data files and experiment folders
├── Figures_Main/          # Generated main-text figures
├── Figures_SI/            # Generated supporting-information figures
├── Scripts/
│   ├── MATLAB/            # MATLAB figure modules, one folder per figure
│   └── Python/            # Python figure modules, one folder per figure
│       └── utils/         # Shared Python helpers
├── data_id.json           # Stable data-key to data-path mapping
├── figure_id.json         # Manuscript figure labels to figure IDs
├── script_id.json         # Manuscript figure labels to script IDs
├── figure_registry.csv    # Inspector-friendly figure navigation table
├── figure_registry.json   # Machine-readable figure registry
├── list_figures.py        # Rebuilds the registry files
├── run_figure.py          # Runs one Python figure module by script ID
├── clear_figure.py        # Utility for clearing generated outputs
├── requirements.txt       # Python dependencies
└── README.md
```

Local-only folders and generated cache files, such as `venv/`, `__pycache__/`, `.DS_Store`, `._*`, and editor settings, are ignored by `.gitignore` so the GitHub page stays focused on reproducible source, data, registries, and figure outputs.

## Notes

- Keep folder names stable after publication; the registry depends on them.
- After adding or renaming a figure script, update `figure_id.json` and `script_id.json`, then run `python list_figures.py`.
- After adding or renaming data files, update `data_id.json`, then run `python list_figures.py`.
- MATLAB figures require a valid MATLAB installation and license.
