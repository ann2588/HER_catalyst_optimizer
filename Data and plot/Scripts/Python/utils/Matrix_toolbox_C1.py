import numpy as np
import matplotlib.pyplot as plt
import sys, os
from pathlib import Path

MAKE_PLOTS = True
FEATURES = ["ΔV", "ΔCr", "ΔFe", "ΔCo", "ΔNi", "ΔCu", "ΔMg", "ΔS", "ΔSe", "ΔP", "ΔVolt", "ΔTime"]
P = len(FEATURES)


PAIRS_TO_PLOT = []


def reconstruct_H_from_theta(theta_vec: np.ndarray, p: int) -> np.ndarray:
    th = np.ravel(theta_vec)
    need = 1 + p + (p*(p+1))//2
    if th.size < need:
        raise ValueError(f"theta too short: {th.size} < {need}")
    quad = th[1+p : 1+p + (p*(p+1))//2]  # upper-tri row-wise
    
    H = np.zeros((p,p), float)
    idx = 0
    for i in range(p):
        span = p - i
        row = quad[idx:idx+span]; idx += span
        H[i,i] = 2.0*row[0]
        if span > 1:
            H[i, i+1:p] = row[1:]
    H = H + H.T - np.diag(np.diag(H))
    
    return H

def show_heatmap(M, title, suffix=""):
    if not MAKE_PLOTS:
        return
    

    mask = np.zeros_like(M, dtype=bool)
    for (fx, fy) in PAIRS_TO_PLOT:
        for (i, j) in [(fx, fy), (fy, fx)]:
            if i in FEATURES and j in FEATURES:
                xi, yj = FEATURES.index(i), FEATURES.index(j)
                mask[yj, xi] = True  
    

    M_masked = np.where(mask, M, np.nan)
    

    valid_vals = M_masked[~np.isnan(M_masked)]
    a = np.nanmax(np.abs(valid_vals)) if valid_vals.size > 0 else 0.1
    a = max(a, 0.12)  


    #cmap = plt.get_cmap('bwr_r').copy()
    cmap = plt.get_cmap('coolwarm').copy()
    #cmap.set_bad(color = 'white')  
    
    plt.figure(figsize=(2.0, 2.0))
    im = plt.imshow(M_masked, vmin=-a, vmax=a, cmap=cmap)
    #plt.colorbar(im, fraction=0.046, pad=0.04)
    plt.xticks(range(P), FEATURES, rotation=90, fontsize=3, font="Arial")
    plt.yticks(range(P), FEATURES, fontsize=3, font="Arial")

    ax = plt.gca()
    ax.xaxis.set_ticks_position('top')

