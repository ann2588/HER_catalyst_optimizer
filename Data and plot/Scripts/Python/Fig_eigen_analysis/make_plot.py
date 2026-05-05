import os
import sys
import matplotlib as mpl
SCRIPT_DIR = os.path.dirname(__file__)
# this points to: Scripts/Python/
SCRIPTS_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
UTIL_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "utils"))
sys.path.append(SCRIPTS_ROOT)
sys.path.append(UTIL_ROOT)
mpl.rcParams["font.size"] = 6

from registry import get_data_path
FIGURE_METADATA = {
    "stable_id": "Fig_eigen_full_campaigns",
    "script": __file__,
    "data_keys": ["Campaign1","Campaign2","Campaign3","Campaign4"],
    "figure_type": "SI"   # or "Main"
}

def get_output_dir(meta):
    base = os.path.dirname(__file__)
    fig_base = "Figures_SI" if meta["figure_type"] == "SI" else "Figures_Main"
    outdir = os.path.join(base, "..", "..", ".." , fig_base, meta["stable_id"])
    os.makedirs(outdir, exist_ok=True)
    return outdir

OUTPUT_DIR = get_output_dir(FIGURE_METADATA)
os.makedirs(OUTPUT_DIR, exist_ok=True)


#% Import Model
import numpy as np
import pandas as pd
import sys, os
from LQV4_forpost import LQBandit
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap
from sklearn.preprocessing import StandardScaler
import matplotlib.gridspec as gridspec
import seaborn as sns


#============== Loading file ==============

DATA_DICT = {k: get_data_path(k) for k in FIGURE_METADATA["data_keys"]}

CAMPAIGN1_FILE = DATA_DICT["Campaign1"]
CAMPAIGN2_FILE = DATA_DICT["Campaign2"]
CAMPAIGN3_FILE = DATA_DICT["Campaign3"]
CAMPAIGN4_FILE = DATA_DICT["Campaign4"]

LIST = [CAMPAIGN1_FILE, CAMPAIGN2_FILE, CAMPAIGN3_FILE , CAMPAIGN4_FILE]
EXPLIST = ["exp715", "exp839", "exp931", "exp1031"]

for Filename, EXP, x in zip(LIST, EXPLIST, range(1,5)):

    filename = Filename
    agent = LQBandit(beta=60, csv_file=f'{filename}')
    exp_index = list(agent.exp_ids).index(EXP)  # index in the valid subset #715, 839, 931, 1066, 1238

    original_features = ["ΔV", "ΔCr", "ΔFe", "ΔCo", "ΔNi", "ΔCu", "ΔMg", "ΔS", "ΔSe", "ΔP", "ΔVolt", "ΔTime"]
    theta = agent.theta
    basename = filename.split(".csv")[0]
    print(basename)



    x0_scaled = agent.x[exp_index].reshape(1, -1)  # shape: (1, 12)
    print(x0_scaled)
    #X_centered = agent.x
    X_centered = agent.x-x0_scaled

    # Covariance matrix
    cov = agent.phi(X_centered).T @ agent.phi(X_centered)

    # Inverse (add regularization if needed to make it invertible)
    lambda_reg = 1e-6
    cov_inv = np.linalg.inv(cov)

    # Vector b: projection of y onto the design matrix
    b = agent.phi(X_centered).T @ agent.y  # shape: (12, 1)
    theta_centered = cov_inv @ b  # shape: (12, 1)

    #============== Formatting Coef Matrix ==============

    # Generate Pattern 1
    pattern_1 = [1]
    n = 12  # Starting number
    while n > 0:
        pattern_1.append(pattern_1[-1] + n)
        n -= 1

    # Generate Pattern 2
    pattern_2 = list(range(1, len(pattern_1)))[::-1]

    # Get coefficients
    #coef_df = pd.DataFrame(theta)
    coef_df = pd.DataFrame(theta_centered)

    result = []
    for i, j in zip(pattern_1, pattern_2):
        # Extract values from row 0 and columns i to j
        row = coef_df.iloc[12+i:12+i+j].values.flatten().tolist()
        result.append(row)

    # Adjust each row to start from a different column
    adjusted_result = []
    for idx, row_ in enumerate(result):
        adjusted_row = [None] * idx + row_
        adjusted_result.append(adjusted_row)

    print(adjusted_result)

    df = pd.DataFrame(adjusted_result)

    # Fill NaNs at (i, j) with values from (j, i)
    for i in range(df.shape[0]):
        for j in range(df.shape[1]):
            if pd.isna(df.iat[i, j]) and not pd.isna(df.iat[j, i]):
                df.iat[j,i] = df.iat[j,i]/2
                df.iat[i,j] = df.iat[j, i]


    Q = df.to_numpy()

    #============== Eigendecomposition ==============
    eigenvalues, eigenvectors = np.linalg.eigh(Q)
    for i in range(12):
        print(eigenvectors[:,i])
        print(eigenvalues[i])
    # Transpose eigenvectors to match MATLAB's row-eigenvector format
    eigenvectors_for_matlab = eigenvectors.T  # shape: (12, 12), each row is one eigenvector

    # Save both to a .txt file
    #np.savetxt(f"{basename}_eigenvectors.txt", eigenvectors_for_matlab, fmt="%.8f", delimiter=' ')
    #np.savetxt(f"{basename}_eigenvalues.txt", eigenvalues.reshape(-1, 1), fmt="%.17f")

    eigenvector_colors = [
        (128/255, 128/255, 128/255),  # medium gray
        (1.0, 1.0, 1.0),              # white
        (128/255, 128/255, 128/255)   # medium gray
    ]
    eigenvalue_colors = [(0, 0, 1), (1, 1, 1), (1, 0, 0)]  # Gray scale
    eigenvector_cmap = plt.get_cmap("coolwarm_r")
    eigenvalue_cmap = LinearSegmentedColormap.from_list('coolwarm_r', [(r*0.97, g*0.97, b*0.97) for r, g, b in eigenvector_colors])

    # Set up the figure with 2 subplots: top = eigenvalues, bottom = eigenvectors
    fig = plt.figure(figsize=(3.6, 3.6))
    gs = gridspec.GridSpec(2, 1, height_ratios=[6, 0.5], hspace=0.05)

    M_masked = Q.copy()
    valid_vals = M_masked[np.isnan(M_masked)]
    a = np.nanmax(np.abs(valid_vals)) if valid_vals.size > 0 else 0.1

    # bottom plot: eigenvalue heatmap (1 row)
    ax0 = plt.subplot(gs[1])
    sns.heatmap(eigenvalues.reshape(1, -1),center=0, annot=True, fmt=".1f", cmap=eigenvalue_cmap,
                xticklabels=[f'PC{i}' for i in range(12)], yticklabels=["λ"], cbar=True, ax=ax0)
    ax0.set_xticklabels(ax0.get_xticklabels(), rotation=0)
    ax0.set_xlabel("Eigenvector Index (PC)")
    ax0.set_ylabel("")
    ax0.tick_params(left=False, bottom=False)

    # TOP plot: eigenvector heatmap (12x12)
    ax1 = plt.subplot(gs[0])
    sns.heatmap(eigenvectors, annot=False, fmt=".2f", center=0, cmap=eigenvector_cmap,
                xticklabels=[f'PC{i}' for i in range(12)],
                yticklabels=original_features, cbar=True, ax=ax1)
    #ax1.set_title(f"Heatmap of Eigenvectors (Principal Directions)_{basename}")
    ax1.set_xticklabels([], rotation=0)
    ax1.set_xlabel("")
    ax1.set_ylabel("Original Feature")

    #plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/campaign{x}_PC_matrix.png", dpi = 600)
    plt.savefig(f"{OUTPUT_DIR}/campaign{x}_PC_matrix.eps")
    plt.show()

