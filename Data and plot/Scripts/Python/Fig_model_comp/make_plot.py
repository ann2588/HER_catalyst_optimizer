'''
Note: This script contains heavy packages. You might need brew to install.
To avoid trouble, one option is to run it on google colab.
'''


import os
import sys

SCRIPT_DIR = os.path.dirname(__file__)
# this points to: Scripts/Python/
SCRIPTS_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
UTIL_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "utils"))
sys.path.append(SCRIPTS_ROOT)
sys.path.append(UTIL_ROOT)

from registry import get_data

FIGURE_METADATA = {
    "stable_id": "Fig_model_comp",
    "script": __file__,
    "data_keys": "result_pretrain", # or In folder
    "figure_type": "Main"   # or "Main"
}

def get_output_dir(meta):
    base = os.path.dirname(__file__)
    fig_base = "Figures_SI" if meta["figure_type"] == "SI" else "Figures_Main"
    outdir = os.path.join(base, "..", "..", ".." , fig_base, meta["stable_id"])
    os.makedirs(outdir, exist_ok=True)
    return outdir

OUTPUT_DIR = get_output_dir(FIGURE_METADATA)
os.makedirs(OUTPUT_DIR, exist_ok=True)
DATAPATH = get_data(FIGURE_METADATA["data_keys"])

###========================================================================###

#% File input
import pandas as pd
import os


df = pd.read_csv(DATAPATH)
df. drop(columns = 'blank')
y = df.iloc[:, 18]
x = df.iloc[:, 1:14]
print(y)
# Combine x and y temporarily to handle NaN removal
combined = pd.concat([x, y], axis=1)

# Drop rows with NaN in any column
combined_cleaned = combined.dropna()

# Separate cleaned x and y
x_cleaned = combined_cleaned.iloc[:, :x.shape[1]]  # First part is x
y_cleaned = combined_cleaned.iloc[:, x.shape[1]:]  # Remaining part is y

x = x_cleaned.values
y = y_cleaned.values

#% Data Normalization
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# Normalize x

scaler_x = StandardScaler()
x = scaler_x.fit_transform(x)

# Normalize y
scaler_y = StandardScaler()
y = scaler_y.fit_transform(y)

#% Import models
from sklearn import svm
from sklearn.linear_model import LinearRegression, Lasso, Ridge
from sklearn.kernel_ridge import KernelRidge
from sklearn.linear_model import BayesianRidge
from sklearn.neural_network import MLPRegressor
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.svm import SVR
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.ensemble import AdaBoostRegressor
from lightgbm import LGBMRegressor
from sklearn.linear_model import ElasticNet
from sklearn.linear_model import HuberRegressor
from sklearn.linear_model import SGDRegressor
from sklearn.neighbors import KNeighborsRegressor
from sklearn.linear_model import OrthogonalMatchingPursuit
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split

import matplotlib.pyplot as plt
import seaborn as sns

#%
# List of models to try
models = {
    'Linear Regression': LinearRegression(),
    'Lasso Regression': Lasso(alpha=0.1),
    'Ridge Regression': Ridge(alpha=0.1),
    'Kernel Ridge': KernelRidge(),
    'MLP Regressor': MLPRegressor(hidden_layer_sizes=(5,), max_iter=500),
    'Random Forest': RandomForestRegressor(n_estimators=10),
    'Gradient Boosting': GradientBoostingRegressor(n_estimators=10),
    'Support Vector Regression': SVR(kernel='rbf', C=1.0, epsilon=0.2),
    'Decision Tree': DecisionTreeRegressor(max_depth=5),
    'Extra Trees': ExtraTreesRegressor(n_estimators=10),
    'AdaBoost': AdaBoostRegressor(n_estimators=10),
    'LightGBM': LGBMRegressor(n_estimators=10, learning_rate=0.1),
    'Bayesian Ridge': BayesianRidge(),
    'Elastic Net': ElasticNet(alpha=0.1, l1_ratio=0.5),
    'Huber Regressor': HuberRegressor(),
    'SGD Regressor': SGDRegressor(max_iter=500, tol=1e-3),
    'K-Nearest Neighbors': KNeighborsRegressor(n_neighbors=5),
    'Orthogonal Matching Pursuit': OrthogonalMatchingPursuit(),
    'XGBoost': XGBRegressor(n_estimators=10, learning_rate=0.1)
}

results_df = pd.DataFrame(columns=models.keys())
TESTSIZE = 0.05

X_train, X_test, y_train, y_test = train_test_split(x, y, test_size=TESTSIZE, random_state=28)

# Evaluate each model
for name, model in models.items():
    # Initialize sum of test scores
    sum_test_score = 0

    # Fit the model for each y column
    for i in range(y_train.shape[1]):
        model.fit(X_train, y_train[:, i])
        test_score = model.score(X_test, y_test[:, i])

        # Add test score to sum
        sum_test_score += test_score

    # Store the average test score in the DataFrame
    results_df.loc[TESTSIZE, name] = sum_test_score / y_train.shape[1]

from LQV4_forpost import *

lq = LQBandit(csv_file=DATAPATH, alpha=10, beta=60)
r2 = lq.r2

results_df.loc[TESTSIZE, "LQBandit"] = r2

import matplotlib.pyplot as plt
import seaborn as sns
plt.rcParams["font.family"] = "Arial"
plt.rcParams["font.size"] = 8
sns.set_theme(style="whitegrid")

models_plot = results_df.columns
scores = results_df.iloc[0].astype(float).values 

plt.figure(figsize=(7.2, 3.6))
sns.barplot(x=models_plot, y=scores, palette="viridis")

plt.xticks(rotation=45, ha="right", fontsize=10)
plt.ylabel("R²", fontsize=12)
plt.xlabel("")

plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/{FIGURE_METADATA['stable_id']}.png", dpi=600)
plt.savefig(f"{OUTPUT_DIR}/{FIGURE_METADATA['stable_id']}.eps")