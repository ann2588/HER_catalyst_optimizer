
#reset -f
import pandas as pd
import numpy as np
import sklearn
from sklearn.model_selection import train_test_split, KFold, cross_val_score
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler, PolynomialFeatures
from scipy.optimize import minimize, LinearConstraint
from sklearn.linear_model import Ridge, LinearRegression, Lasso
import random

class LQBandit:
    def __init__(self, csv_file=r'C:\Users\guazh\PycharmProjects\AutoHeteroCata\Batch_Demo_Result.csv', alpha=10, beta=100, swap_v_mn=False):
        # parameter alpha is for regularize the noise (larger for larger noise)
        # parameter beta is for the strength for exploration (larger for more aggressive)
        df = pd.read_csv(csv_file, sep=',').to_numpy()
        config = np.delete(df[:, 1:14].astype(float), 10, axis=1) # experiment configurations
        self.column = pd.read_csv(csv_file, sep=',').columns.tolist()
        self.offlinedata = pd.read_csv(csv_file, sep=',').to_numpy()
        # Swap V and Mn columns if the flag is set
        if swap_v_mn:
            # Assuming V is column index 0 and Mn is column index 2 in the configuration
            config[:, [0, 2]] = config[:, [2, 0]]
        self.id = df[:,0]
        
        self.cd = np.array([10., 20., 30., 40., 50.]) # current density list
        op = self.sanitize_nan(df[:, 14:].astype(float)) # overpotential over different current
        
        valid_indices = ~np.isnan(op[:, -1])
        self.exp_ids = self.id[valid_indices]  # Store experiment IDs after filtering
        x, y = config[valid_indices], op[valid_indices, -1]
        
        self.indices = np.where(y > -0.15)[0]
        self.scaler_x = StandardScaler()
        self.x = self.scaler_x.fit_transform(x)

        self.y_mean = y.mean()
        self.y_std = y.std()
        self.y = (y - self.y_mean) / self.y_std
        

        
        # nonlinear featurizer
        self.polyfeature = PolynomialFeatures(degree = 2, include_bias = True, interaction_only = False)
        self.featurizer = PolynomialFeatures(degree=2, include_bias=True, interaction_only=False).fit(self.x) #TODO does the linear model included in this featurizer? If not, which part describes the linear model? #Interaction_only=False: with xi^2
        self.featurizE = self.featurizer.transform(self.x)
        self.phi = lambda _x: self.featurizer.transform(_x)
        
        self.d = self.featurizer.n_output_features_
        
        self.alpha, self.beta = alpha, beta
        
        # we do not need this parameter, just an way to show the global, unweighted performance
        self.cov = self.phi(self.x).T @ self.phi(self.x) + self.alpha * np.eye(self.d)
        self.cov_inv = np.linalg.inv(self.cov) #[d, d]
        self.b = self.phi(self.x).T @ self.y
        
        self.theta = self.cov_inv @ self.b     
        self.r2 = 1 - np.mean((self.phi(self.x) @ self.theta - self.y) ** 2)
        #print('R^2 without weighting: {:.3f}'.format(1 - np.mean((self.phi(self.x) @ self.theta - self.y) ** 2)))
        
        # Constraints, bounds and others
        self.constrainA = np.array([
            [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0],
            [1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0],
        ])
        self.discrete_level = np.array([1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0.1, 1]) #TODO is this setting still generate descrete level of 1?
        # To avoid 0 visit of specific element
        # lower the descrete level to 1
        # add purturbation after suggested new X. 
        # the descrete level can be modified based on diff X0.
        self.ub = np.array([70, np.inf, np.inf]) #TODO
        self.lb = np.array([-np.inf, 0, 0]) #TODO
        
    def sanitize_nan(self, op):
        for i in range(op.shape[0]):
            # Find the indices of non-NaN values
            non_nan_indices = ~np.isnan(op[i, :])
            # If only one value, skip the row
            if np.sum(non_nan_indices) <= 1:
                continue

            # Extract the x and y values for non-NaN entries
            x_non_nan = self.cd[non_nan_indices].reshape(-1, 1)
            y_non_nan = op[i, non_nan_indices]

            # Fit linear regression on non-NaN data
            model = LinearRegression().fit(x_non_nan, y_non_nan)

            # Predict the NaN values based on the fitted model
            nan_indices = np.isnan(op[i, :])
            if np.any(nan_indices):
                x_nan = self.cd[nan_indices].reshape(-1, 1)
                y_pred = model.predict(x_nan)
                op[i, nan_indices] = y_pred
        return op
        
    def update(self, x, ops):
        # x: [N, 13] in align with output
        # ops: [N, 5] with cd = 10, ... 50 mA
        
        x = np.delete(x.astype(float), 10, axis=1)
        ops_sanitized = self.sanitize_nan(ops)
        
        x, y = x[~np.isnan(ops_sanitized[:, -1])], ops_sanitized[~np.isnan(ops_sanitized[:, -1]), -1]
        
        # record the x and y, though not necessary, we choose not to change the scaling factor of x and y
        x_scaled = self.scaler_x.transform(x)
        y_scaled = (y - self.y_mean) / self.y_std
        self.x = np.concatenate((self.x, x_scaled))
        self.y = np.concatenate((self.y, y_scaled))
        
        # update the TS / UCB warehouse
        # again, we do not really need this because of the weighted regression
        # valid when r < 10
        # when r > 10, the additional distance weight, objective 2 was introduced to ensure the randomness of the generated input
        self.cov += self.phi(x_scaled).T @ self.phi(x_scaled)
        self.cov_inv = np.linalg.inv(self.cov) #[d, d]
        self.b += self.phi(x_scaled).T @ y_scaled
        self.theta = self.cov_inv @ self.b        
        print('Updated R^2 in offline training set: {:.3f}'.format(1 - np.mean((self.phi(self.x) @ self.theta - self.y) ** 2)))
    
    def func(self, x):
        return -self.weighted_theta_sampled @ self.phi(self.scaler_x.transform(x.reshape(1, -1))).reshape(-1)
    
    def get_weight(self, x0, r):
        x0_transform = self.scaler_x.transform(np.array([x0]))
        # the distance was calculated based on the normalized x
        # r is absolute value, x is normalized value.
        # here 3 is a very rough estimation to guarantee that the weight is at around 0.5 when r = 20
        ds = np.linalg.norm(self.x - x0_transform[0], axis=1) ** 2
        return np.exp(- 3 * ds / r / r) 
        #



    def select_action(self, x0, r=30):
        self.beta = r / 10.0 # we assume the most common request is r = 10 
        
        if x0 is None:
            # if we do not have a good 'prior' to search...
            # so we are trying to find a sample with maximum average weight 
            bounds = [(0, 70) for i in range(10)] + [(-1.5, -1), (30, 180)]
            ret = minimize(
                # I fixed a 10 for finding a good weight #TODO 10? 20? 30?
                fun=lambda _x0: -self.get_weight(_x0, 10).max(), #TODO min() -> max() 
                x0=[random.uniform(_l, _r) for (_l, _r) in bounds],
                constraints=(LinearConstraint(self.constrainA, self.lb, self.ub),),
                bounds=bounds
            )
            discrete_x = np.round(ret.x / self.discrete_level) * self.discrete_level
            y = self.theta @ self.phi(self.scaler_x.transform(discrete_x.reshape(1, -1))).reshape(-1) * self.y_std + self.y_mean
            return discrete_x, y
        else:
            # I assume now we are seaching around x0
            # the weighted regression considering more on the nearest neighborhood
            weight = self.get_weight(x0, r)
            self.weighted_cov = self.phi(self.x).T @ np.diag(weight) @ self.phi(self.x) + self.alpha * np.eye(self.d)
            self.weighted_cov_inv = np.linalg.inv(self.weighted_cov)
            self.weighted_b = self.phi(self.x).T @ np.diag(weight) @ self.y
            self.weighted_theta = self.weighted_cov_inv @ self.weighted_b 
            self.weighted_theta_sampled = np.random.multivariate_normal(self.weighted_theta, self.beta * self.weighted_cov_inv)
            R2 = 1 - np.mean((self.phi(self.x) @ self.weighted_theta - self.y) ** 2)
            distance_weight = max(1 - 1 / self.beta, 0) #!! r and beta is coupled now. 
            print('Average weight: {:.3f}, R^2: {:.3f}, distance weight: {:.3f}'.format(weight.mean(), R2, distance_weight))
            
            self.theta_sampled = np.random.multivariate_normal(self.theta, self.beta * self.cov_inv)
            
            bounds = [(max(0, x0[i] - r), min(70, x0[i] + r)) for i in range(10)] + [(-1.5, -1), (30, 180)]
            print(self.get_weight(x0, r).min(), self.func(np.array(x0)))
            ret = minimize(
                # I fixed a 10 for finding a good weight, where \beta = 1
                fun=lambda _x0: distance_weight * -self.get_weight(_x0, 10).max() + (1 - distance_weight) * self.func(_x0),
                x0=[random.uniform(_l, _r) for (_l, _r) in bounds],
                constraints=(LinearConstraint(self.constrainA, self.lb, self.ub),),
                bounds=bounds
            ) 
            discrete_x = np.round(ret.x / self.discrete_level) * self.discrete_level
            y = self.theta @ self.phi(self.scaler_x.transform(discrete_x.reshape(1, -1))).reshape(-1) * self.y_std + self.y_mean
            return discrete_x, y


