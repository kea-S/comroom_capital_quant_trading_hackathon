class Pair():
    """
    Represents a pair of 2 crypto coins, Coin A and Coin B
    Window size = number of candles which we run the OLS regression on each time we run the strategy logic
    Allocated capital = how much money this pair gets to trade with
    Cooldown = If we hit a stop loss the pair gets disabled temporarily, represents how many more hours until we can trade again
    """
    def __init__(self, coin_a, coin_b, allocated_capital, window_size=720):
        self.coin_a = coin_a
        self.coin_b = coin_b
        self.allocated_capital = allocated_capital
        self.window_size = window_size
        self.cooldown = 0
    
    """
    Check if this pair is on cooldown or not
    """
    def is_cooldown(self):
        return self.cooldown > 0
        
    """
    Decrement the cooldown timer for this pair
    Should be called every hour on every pair
    """
    def update_cooldown(self):
        if self.cooldown > 0:
            self.cooldown -= 1
        
    """
    Set the cooldown to a cooldown period
    Should be called if stop loss for this pair is hit
    """
    def set_cooldown(self, hours=120):
        self.cooldown = hours