#%%
from Utilities.echemplatform import *

def echem(mainfold: str, doe:dict, initialization:True):
    # REORGANIZE THE FLOW ACCORDING TO THE FLOW CHART
    date = datetime.now().strftime('%Y-%m-%d')
    base_path = os.path.join(default_path, mainfold)
    create_directory(base_path)

    # Function to perform initial measurements
    if initialization == True:
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

    for expn, exp in doe.items():
        print(f'Running {expn}...')

        cat = expn
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

    # Initial measurements
    #perform_initial_measurements()

    # Run experiments
    #for expn, exp in doe.items():
    #    print(f'Running {expn}...')
    #    run_experiment(expn, exp)

    # Final rinsing
    cell_rinsing('water', 'water', 2)

    # Completion script
    send_status_message(message_completed)

#%%
if __name__ == '__main__':
    #%%
    doepath = r"batch_pretrain_doe.csv"
    doedicts = doeprocess(doepath, start = 568)

    campaign_name = os.environ.get('HER_CAMPAIGN_NAME', 'closed_loop_doe')
    echem(campaign_name, doedicts, initialization = True)
