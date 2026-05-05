import numpy as np
import pandas as pd
import os
import matplotlib.pyplot as plt
import seaborn as sns
from tabulate import tabulate


class ExperimentRecorder:
    def __init__(self, result_path, csv_file=r'./pretrain.csv'):
        self.offlinedata = pd.read_csv(csv_file, sep=',').to_numpy()
        self.column = pd.read_csv(csv_file, sep=',').columns.tolist()
        self.result_path = result_path  # Directory to save the result file

    def update(self, x, ops, exp_num):
        # Ensure x is a 2D array (e.g., shape (1, 12) for a 12-feature input)
        x = np.array(x).reshape(1, -1)

        # Ensure ops (y) is a 2D row array with shape (1, n) for concatenation
        ops = np.array(ops).reshape(1, -1)

        # Merge input features with the result (x + y)
        merging_array = np.concatenate((x, ops), axis=1)

        # Add experiment label (e.g., expXX) as a 2D array
        exp_label = np.array([[f'exp{exp_num}']], dtype=object)

        # Concatenate the label with the data (label + x + y)
        merged_array_with_expXX = np.concatenate((exp_label, merging_array), axis=1)

        # Append the new data to offlinedata
        self.offlinedata = np.append(self.offlinedata, merged_array_with_expXX, axis=0)

        # Create a DataFrame and save it as a CSV file
        df_csv = pd.DataFrame(self.offlinedata, columns=self.column)
        df_csv.to_csv(os.path.join(self.result_path, 'pretrain.csv'), index=False)

    def DownSelection(self, starting: int, ending: int, Original_X0:int):
        """
        1. Access the data
        2. Access the data from exp(starting point) to exp (ending point), naming stage_1_data
        3. make it in ascending order according to 'Overpotential at 50 mA cm-2'
        4. filter any row with 'Overpotential at 50 mA cm-2' value > -0.08
        5. Analyze the similarity of composition of top 5, report the value
        """
        # Access the data from starting to ending
        start_index = np.where(self.offlinedata[:, 0] == f'exp{starting}')[0][0]
        end_index = np.where(self.offlinedata[:, 0] == f'exp{ending}')[0][0]
        stage_1_data = self.offlinedata[start_index:end_index+1]
        Original_X0_index = int(np.where(self.offlinedata[:, 0] == f'exp{Original_X0}')[0][0])
        
        # Convert to DataFrame for easier manipulation
        df_stage_1_raw = pd.DataFrame(stage_1_data, columns=self.column)
        df_stage_1_raw.rename(columns={'Overpotential V at 50.0 mA cm-2': 'Overpotential V at 50.0 mA/cm2'}, inplace=True)

        # Filter rows where 'Overpotential at 50 mA cm-2' > -0.008
        df_stage_1 = df_stage_1_raw[df_stage_1_raw['Overpotential V at 50.0 mA/cm2'] <= -0.1]

        # Sort by 'Overpotential at 50 mA cm-2' in descending order
        df_stage_1 = df_stage_1.sort_values(by='Overpotential V at 50.0 mA/cm2', ascending=False)
        
        # Analyze the similarity of composition of top 5
        top_5 = df_stage_1.head(5)
        X0 = self.offlinedata[Original_X0_index:Original_X0_index+1]
        df_X0 = pd.DataFrame(X0, columns=self.column)
        
        #print(tabulate(top_5, headers='keys', tablefmt='grid'))

        # Calculate rankings before similarity report
        rankings = self.calculate_rankings(top_5, df_X0)
        
        # Print both tables
        print("\nTop Candidates:")
        print(tabulate(top_5, headers='keys', tablefmt='grid'))
        
        print("\nRankings Analysis:")
        print(tabulate(rankings, headers='keys', tablefmt='grid'))

        similarity_report = self.analyze_similarity(top_5, df_X0)
        
        top_1_index = int(rankings.iloc[0]['expID'].split('exp')[1])
        _index = np.where(self.offlinedata[:, 0] == f'exp{top_1_index}')[0][0]
        top_1_composition = self.offlinedata[_index:_index+1, 1:14].tolist()[0]  # converts to 1D list
        # Print the result: next X0 candidate, top 1 in rankings
        print(f"Next X0 candidate: {top_1_index}")
        print(f"Composition: {top_1_composition}")
        
        # Return the exp ID, composition of top one in rankings
        return top_1_index, top_1_composition

    def calculate_rankings(self, top_candidates, X0):
        """
        Calculate rankings based on three criteria:
        1. Overpotential value (larger is better)
        2. Average dissimilarity with other experiments (larger distance is better)
        3. Dissimilarity with original X0 (larger distance is better)
        """
        # Create working DataFrame
        rankings_df = pd.DataFrame()
        rankings_df['expID'] = top_candidates.iloc[:,0]
        rankings_df['overpotential'] = top_candidates['Overpotential V at 50.0 mA/cm2']
        
        # Get compositions
        composition_data = top_candidates.iloc[:, 1:13].values
        X0_composition = X0.iloc[:, 1:13].values
        n_samples = len(composition_data)
        
        # Calculate distances
        avg_distances = []
        X0_distances = []
        std_distances = []
        
        for i in range(n_samples):
            # Calculate distances to all other points
            distances = []
            for j in range(n_samples):
                if i != j:
                    dist = np.linalg.norm(composition_data[i] - composition_data[j])
                    distances.append(dist)
            avg_distances.append(np.mean(distances))
            std_distances.append(np.std(distances))
            
            # Calculate distance to X0
            X0_dist = np.linalg.norm(composition_data[i] - X0_composition)
            X0_distances.append(X0_dist)
        
        rankings_df['avg_distance'] = [round(d, 3) for d in avg_distances]
        rankings_df['std_distance'] = [round(d, 10) for d in std_distances]
        rankings_df['X0_distance'] = [round(d, 3) for d in X0_distances]
        
        # Calculate weighted rankings (1 is best)
        rankings_df['overpotential_rank'] = rankings_df['overpotential'].rank(ascending=False)
        rankings_df['avg_distance_rank'] = rankings_df['avg_distance'].rank(ascending=True)
        rankings_df['std_distance_rank'] = rankings_df['std_distance'].rank(ascending=False)
        rankings_df['X0_distance_rank'] = rankings_df['X0_distance'].rank(ascending=True)
        
        # Calculate final score and overall rank
        rankings_df['final_score'] = (rankings_df['overpotential_rank']* 2.5 + 
                                    rankings_df['avg_distance_rank']*1.5 + 
                                    rankings_df['std_distance_rank']*1 + 
                                    rankings_df['X0_distance_rank']*1.5)
        
        rankings_df = rankings_df.sort_values('final_score')
        rankings_df['overall_rank'] = range(1, len(rankings_df) + 1)
        #print("\nRankings Analysis:")
        #print(tabulate(rankings_df, headers='keys', tablefmt='grid'))
        
        '''
        # Add visualization
        plt.figure(figsize=(7.2, 3.6))
        plt.subplot(131)
        plt.scatter(rankings_df['overpotential'], rankings_df['avg_distance'])
        plt.xlabel('Overpotential')
        plt.ylabel('Avg Distance')
        
        plt.subplot(132)
        plt.scatter(rankings_df['overpotential'], rankings_df['X0_distance'])
        plt.xlabel('Overpotential')
        plt.ylabel('X0 Distance')
        
        plt.subplot(133)
        plt.scatter(rankings_df['avg_distance'], rankings_df['X0_distance'])
        plt.xlabel('Avg Distance')
        plt.ylabel('X0 Distance')
        
        plt.tight_layout()
        plt.show()
        '''
        
        return rankings_df

    def analyze_similarity(self, top_5, X0):
        """
        Analyze similarity between top 5 samples using Euclidean distance
        Only considers the composition columns (first 12 columns after 'expXX')
        Returns a dictionary with mean, min, max distances and distance matrix
        """
        # Extract composition columns (first 12 columns after 'expXX')
        composition_data = top_5.iloc[:, 1:13].values
        X0_data = X0.iloc[:, 1:13].values
        
        # Initialize distance matrix
        n_samples = len(composition_data)
        distance_matrix = np.zeros((n_samples, n_samples))
        
        # Calculate Euclidean distances between all pairs
        distances = []
        for i in range(n_samples):
            for j in range(i+1, n_samples):
                dist = np.linalg.norm(composition_data[i] - composition_data[j])
                distance_matrix[i,j] = dist
                distance_matrix[j,i] = dist
                distances.append(dist)
        
        # Create a DataFrame with the original index {expXX}
        distance_matrix_df = pd.DataFrame(distance_matrix, index=top_5.iloc[:,0], columns=top_5.iloc[:,0])
        
        similarity_report = {
            'mean_distance': round(float(np.mean(distances)), 1),
            'min_distance': round(float(np.min(distances)), 1),
            'max_distance': round(float(np.max(distances)), 1),
            'std_distance': round(float(np.std(distances)), 1),
            'distance_matrix': distance_matrix_df,
            'composition_data': composition_data
        }

        # Plotting the distance matrix
        plt.figure(figsize=(3.6, 3.6))
        sns.heatmap(distance_matrix, annot=True, cmap='Blues_r', square=True, xticklabels=top_5.iloc[:,0], yticklabels=top_5.iloc[:,0])
        plt.title('Distance Matrix')
        plt.xlabel('Sample Index')
        plt.ylabel('Sample Index')
        plt.show()

        return similarity_report
    
    def ReturnStEdX0(self, X0: int):
        if X0 == 59:
            starting = 609
            ending = 667
        elif X0 == 667:
            starting = 668
            ending = 728
        elif X0 == 136:
            starting = 729
            ending = 788
        elif X0 == 772:
            starting = 800
            ending = 858
        elif X0 == 994:
            starting = 1039
            ending = 1098
        elif X0 == 891:
            starting = 919
            ending = 978
        else:
            print(f'No campaign start with X0 = {X0}, please select again.')
        return starting, ending, X0

if __name__ == "__main__":
    result_path = os.environ.get("HER_ENCODER_RESULT_PATH", ".")
    csv_file = os.environ.get("HER_ENCODER_CSV_FILE", os.path.join(result_path, "Batch_Demo_result_all.csv"))
    log = ExperimentRecorder(result_path=result_path, csv_file=csv_file)
    X0s = [891]
    list = []
    for _X0 in X0s:
        starting, ending, X0 = log.ReturnStEdX0(_X0)
        top1_index, top1_comp = log.DownSelection(starting, ending, X0)
        list.append(top1_index)
        print(top1_index, top1_comp)

