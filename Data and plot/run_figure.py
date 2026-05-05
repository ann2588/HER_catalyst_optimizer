import os
import sys
import subprocess

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_ROOT = os.path.join(PROJECT_ROOT, "Scripts", "Python")

def run_figure(fig_id):
    target_dir = os.path.join(SCRIPTS_ROOT, fig_id)
    target_file = os.path.join(target_dir, "make_plot.py")

    if not os.path.exists(target_file):
        print(f"[Error] Cannot find script for figure ID: {fig_id}")
        print(f"Expected: {target_file}")
        return

    print(f"[Running] {target_file}")
    subprocess.run(["python3", target_file])

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 run_figure.py <FIGURE_STABLE_ID>")
    else:
        run_figure(sys.argv[1])