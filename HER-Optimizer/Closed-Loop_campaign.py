import Utilities.OneStepClosedLoop as EXP
from DataProcessing.OverpotentialExtraction import *
from Utilities.LQV4 import *
from Utilities.Encoder import *
import math, time
import os
import numpy as np
from datetime import datetime

#%%
EXP.MAINFOLD = os.environ.get('HER_CAMPAIGN_NAME', 'closed_loop_campaign')
# REORGANIZE THE FLOW ACCORDING TO THE FLOW CHART
date = datetime.now().strftime('%Y-%m-%d')
base_path = os.path.join(EXP.default_path, EXP.MAINFOLD)
EXP.date = date
EXP.base_path = base_path
EXP.create_directory(base_path)
log = ExperimentRecorder(result_path = base_path)

agent = LQBandit(beta = 60)

X0 = [5, 5, 0, 0, 10, 0, 25, 0, 5, 20, -1.2, 90]  # Choose the one you want to survey around # Start from exp371 
x0_exp_num = int(os.environ.get('HER_STAGE1_X0_EXP', '371'))
exp_num = 597  # Initialize the experiment number outside the loop
stage_1_start = exp_num

#%%
EXP.Initialization()
import time

### Stage 1, Global
xnew, y_predicted = agent.select_action(X0, r=20)  # Suggest next action
for i in range(60):

    # Update xnew with the calculated value
    XNEW_exp = np.concatenate((xnew[:10], [70 - sum(xnew[:10])], xnew[10:]))
    exp = dict(zip(agent.column[1:14], XNEW_exp))
    print(exp)
    # Perform the experiment
    EXP.ONESTEPCLOSELOOP(exp_num+i, exp)
    ProcessSingleOverpotential(base_path)
    time.sleep(5)
    y_exp = get_overpotentials_by_experiment(os.path.join(EXP.base_path, 'H2KOH_overpotentials_10to50mA.csv'), f'exp{exp_num+i}')
    if y_exp is None:
        raise ValueError(f'No overpotential record found for exp{exp_num+i}')
    print(f'The overpotential for exp{exp_num+i} is {y_exp}')

    # Update the agent with the results of the experiment
    log.update(XNEW_exp, y_exp, exp_num+i)
    _x, y = XNEW_exp.reshape(1, -1), np.array(y_exp).reshape(1, -1).astype(float)
    agent.update(_x, y)
    print(f'y std: {agent.y_std}')
    print('R^2 in updated training set: {:.3f}'.format(agent.updatedr2))

    # Suggest the next action
    xnew, y_predicted = agent.select_action(X0, r=20)
    print(f'Predicted y: {y_predicted:.5f}, selection {xnew}')

stage_1_end = stage_1_start + 59
top1_index, top1_comp = log.DownSelection(stage_1_start, stage_1_end, x0_exp_num)


### Stage 2, Local
top1_comp.pop(10) # Drop blank
X0 = top1_comp
exp_num = stage_1_end + 1
xnew, y_predicted = agent.select_action(X0, r=5)

for i in range(60):

    # Update xnew with the calculated value
    XNEW_exp = np.concatenate((xnew[:10], [70 - sum(xnew[:10])], xnew[10:]))
    exp = dict(zip(agent.column[1:14], XNEW_exp))
    print(exp)
    # Perform the experiment
    EXP.ONESTEPCLOSELOOP(exp_num+i, exp)
    ProcessSingleOverpotential(base_path)
    time.sleep(5)
    y_exp = get_overpotentials_by_experiment(os.path.join(EXP.base_path, 'H2KOH_overpotentials_10to50mA.csv'), f'exp{exp_num+i}')
    if y_exp is None:
        raise ValueError(f'No overpotential record found for exp{exp_num+i}')
    print(f'The overpotential for exp{exp_num+i} is {y_exp}')

    # Update the agent with the results of the experiment
    log.update(XNEW_exp, y_exp, exp_num+i)
    _x, y = XNEW_exp.reshape(1, -1), np.array(y_exp).reshape(1, -1).astype(float)
    agent.update(_x, y)
    print(f'y std: {agent.y_std}')
    print('R^2 in updated training set: {:.3f}'.format(agent.updatedr2))

    # Suggest the next action
    xnew, y_predicted = agent.select_action(X0, r=20)
    print(f'Predicted y: {y_predicted:.5f}, selection {xnew}')
