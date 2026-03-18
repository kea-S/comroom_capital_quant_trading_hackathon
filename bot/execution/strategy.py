import statsmodels.api as sm
import numpy as np
from logger import logger

"""
Strategy logic class
Just used to run regression and return z score
"""
class Strategy:
    def get_z_score(self, log_prices_a, log_prices_b):
        """
        Calculate Z-score using standard OLS on the provided log price windows.
        log_prices_a: Series of log prices for coin A
        log_prices_b: Series of log prices for coin B
        """

        y = log_prices_a
        x_col = log_prices_b
        X = sm.add_constant(x_col)

        # Fit standard OLS
        model = sm.OLS(y, X).fit()
        params = model.params
        
        # Calculate current spread and Z-score
        current_y = y.iloc[-1]
        current_x = x_col.iloc[-1]
        
        # current_spread = Y - (alpha + beta * X)
        # Note: params[1] is the coefficient for x_col (coin_b log price)
        current_spread = current_y - (params['const'] + params.iloc[1] * current_x)
        spread_std = np.sqrt(model.mse_resid)
        current_z = current_spread / spread_std

        logger.info(f"current_spread={current_spread}, spread_std={spread_std}, current_z={current_z}")
        return current_z