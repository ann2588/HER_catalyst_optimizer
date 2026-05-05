from Utilities.echemplatform import *

#%%
MAINFOLD = os.environ.get('HER_CAMPAIGN_NAME', 'closed_loop_campaign')
# REORGANIZE THE FLOW ACCORDING TO THE FLOW CHART
date = datetime.now().strftime('%Y-%m-%d')
base_path = os.path.join(default_path, MAINFOLD)
create_directory(base_path)

#%%
def Initialization(BASE_PATH = base_path):
    cat = 'Initial'
    subfold = f'{date}-{cat}'
    initial_path = f'{base_path}/{subfold}'
    create_directory(initial_path)
    insitu_echem_regeneration(initial_path)
    cell_rinsing('water', 'koh', 3)
    purgeH2(50)
    time.sleep(180)
    run_CV_HER_varyE(initial_path, sample=cat, gas='H2KOH', sr_cv=50)
    offH2()
    purgeN2(50)
    time.sleep(60)
    run_CV_HER_varyE(initial_path, sample=cat, gas='ArKOH', sr_cv=50)
    offN2()
def ONESTEPCLOSELOOP(expn, exp):

    #for expn, exp in doe.items():
    print(f'Running exp{expn}...')
    cat = f'exp{expn}'
    subfold = f'{date}-{cat}'
    exp_path = f'{base_path}/{subfold}'
    create_directory(exp_path)

    make_solution(sample=exp)
    purgeN2(50)
    stirring(plate, 60)
    deposit_v, deposit_t = exp['Volt'], exp['Time']
    electrodeposition(exp_path, f'{cat}Deposition', deposit_v, deposit_t)
    cell_rinsing('spelec', 'spelec', 2)
    cell_rinsing('water', 'koh', 3)

    purgeH2(50)
    plate.start_stirring()
    time.sleep(180)
    run_CV_HER_varyE(exp_path, sample=cat, gas='H2KOH', sr_cv=50)
    offH2()
    cell_rinsing('koh', 'koh', 1)
    purgeN2(50)
    plate.start_stirring()
    time.sleep(60)
    run_CV_HER_varyE(exp_path, sample=cat, gas='ArKOH', sr_cv=50)
    cell_rinsing('koh', 'koh', 1)
    offN2()

    insitu_echem_regeneration(exp_path)
    cell_rinsing('water', 'koh', 3)
    purgeN2(50)
    plate.start_stirring()
    time.sleep(60)
    LSV_HER(exp_path, 'RegeneratedGCE', criteria_current=10)
    send_status_message(f"{cat} completed")
