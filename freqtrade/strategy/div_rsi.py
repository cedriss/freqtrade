from pandas import DataFrame, Series
import pandas as pd
from freqtrade.strategy.interface import IStrategy
from talib import RSI, EMA, BBANDS, MA_Type
from scipy.signal import find_peaks

class DivRSIStrategy(IStrategy):
    base_weeks = 20
    ma_trend = 20
    data_points = 4*24*7*base_weeks
    rsi_window = 14
    div_window = 50
    ma_long=50
    ma_short=10
    # Optimal stoploss designed for the strategy
    stoploss = -0.03
    
    timeframe_trend = 'W'

    # Optimal ticker interval for the strategy
    ticker_interval = '15m'
    
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['hlc'] = (dataframe['high'] + dataframe['low'] + dataframe['close']) / 3
        dataframe['rsi'] = RSI(dataframe['hlc'] , timeperiod=self.rsi_window)
        #dataframe['rsi_set'] = dataframe['rsi'].shift(periods = self.div_window)
        dataframe['ma_long'] = EMA(dataframe['close'], timeperiod=self.ma_long)
        dataframe['ma_short'] = EMA(dataframe['close'], timeperiod=self.ma_short)
        return dataframe
    
    
        
    def bull_div(self, price, rsi, price_prominence=0.000032, rsi_prominence=1):
        current_price = price[-1]
        latest_price = price[-2]
        current_rsi = rsi[-1]
        latest_rsi = rsi[-2]
    
        if current_rsi < latest_rsi:
            return False
    
        price_peaks, _ = find_peaks(-price, prominence=price_prominence)
        rsi_peaks, _ = find_peaks(-rsi, prominence=rsi_prominence)
        peaks_index = sorted(set(price_peaks).intersection(set(rsi_peaks)))
        full_peaks_set = tuple(
            (index, price[index], rsi[index]) for index in peaks_index)
    
        detected_divs = []
    
        for index, price_peak, rsi_peak in full_peaks_set:
            if latest_price < price_peak and latest_rsi > rsi_peak:
                if rsi_peak == min(rsi[index:-1]):
                    detected_divs.append((index, price_peak, rsi_peak))
    
        return len(detected_divs)
    
    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the buy signal for the given dataframe
        :param dataframe: DataFrame
        :param metadata: Additional information, like the currently traded pair
        :return: DataFrame with buy column
        """
        for index, row in dataframe.iterrows():
            if index < self.data_points:
                continue
           #date, low, close, rsi, long ma, short ma
            latest_N_bars= dataframe.iloc[index-self.data_points:index, [0,3,4, 7, 8, 9]]
            latest_N_bars = latest_N_bars.set_index(['date'])
            latest_N_bars_resampled = latest_N_bars.resample(self.timeframe_trend).agg({
                        'close': lambda x: x[-1],
                        'low': lambda x: x[-1]
                    })
            
            ma_lg = EMA(latest_N_bars_resampled['close'], timeperiod=self.ma_trend)
            is_bullish = latest_N_bars_resampled['close'][-2] > ma_lg[-2]
            
            if is_bullish:
                rsi_set= latest_N_bars['rsi'][-self.div_window:]
                price_low_set = latest_N_bars['low'][-self.div_window:]
                is_div = self.bull_div(price_low_set, rsi_set, 0.000032, 1)
                ma_long = latest_N_bars['ma_long'][-1]
                ma_short = latest_N_bars['ma_short'][-1]
                if is_div and ma_short < ma_long:
                    dataframe.loc[index, 'buy']= 1
             
            # rsi_set = rsi[index-self.div_window:index]   
                       
            
        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the sell signal for the given dataframe
        :param dataframe: DataFrame
        :param metadata: Additional information, like the currently traded pair
        :return: DataFrame with buy column
        """
        
        return dataframe
        