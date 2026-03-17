import statsmodels.api as sm

"""
Strategy logic class
Just used to run regression and return z score
"""
class Strategy(self):
    def get_z_score(self, log_price_a, log_price_b):

        # Calculate Z-score
        y = log_price_a
        x_col = log_price_b
        X = sm.add_constant(x_col)

        # Ensure prices are numeric
        close_prices = close_prices.astype(float)
        log_prices = np.log(close_prices).dropna()

        # 1. Slice data to only the window we care about for the current calculation
        log_prices_window = log_prices.tail(window_size)
        
        y = log_prices_window[coin_a]
        x_col = log_prices_window[coin_b]
        X = sm.add_constant(x_col)

        # 2. Fit standard OLS on the current window 
        model = sm.OLS(y, X).fit()
        params = model.params
        
        # 3. Calculate current spread and Z-score
        current_y = y.iloc[-1]
        current_x = x_col.iloc[-1]
        
        current_spread = current_y - (params['const'] + params[coin_b] * current_x)
        spread_std = np.sqrt(model.mse_resid)
        current_z = current_spread / spread_std

        return current_z