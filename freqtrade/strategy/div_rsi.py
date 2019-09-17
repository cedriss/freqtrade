from pandas import DataFrame, Series
import pandas as pd
from freqtrade.strategy.interface import IStrategy
from talib import RSI, EMA, BBANDS, MA_Type
from scipy.signal import find_peaks
import freqtrade.vendor.qtpylib.indicators as qtpylib
from pandas.tests.frame.test_validate import dataframe

class DivRSIStrategy(IStrategy):
    base_weeks = 20
    ma_trend = 20
    data_points = 4*24*7*base_weeks
    rsi_window = 14
    div_window = 20
    ma_long=50
    ma_short=10
    # Optimal stoploss designed for the strategy
    stoploss = -0.03
    
    minimal_roi = {
       "0": 0.1
    }
    
    precision =0.99
    
    osLevel = 25    
    
    timeframe_trend = 'W'

    # Optimal ticker interval for the strategy
    ticker_interval = '15m'
    
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['hlc'] = (dataframe['high'] + dataframe['low'] + dataframe['close']) / 3
        dataframe['rsi'] = RSI(dataframe['hlc'] , timeperiod=self.rsi_window)
        #dataframe['rsi_set'] = dataframe['rsi'].shift(periods = self.div_window)
        dataframe['ma_long'] = EMA(dataframe['close'], timeperiod=self.ma_long)
        dataframe['ma_short'] = EMA(dataframe['close'], timeperiod=self.ma_short)
        
        bollinger =qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        
        dataframe['bb_upper'] = bollinger['upper']
        dataframe_longterm = dataframe.set_index(['date'])
        dataframe_longterm = dataframe_longterm.resample(self.timeframe_trend).agg({
                        'close': lambda x: x[-1],
                        'low': lambda x: x[-1]
                    })
        dataframe_longterm['ma_longterm'] = EMA(dataframe_longterm['close'], timeperiod=self.ma_trend)
        old_index= None
        for index, row in dataframe_longterm.iterrows():
            if old_index is None:
                old_index = index
                continue
            dataframe.loc[
                (dataframe['date'] >= old_index) & (dataframe['date']< index) 
                , 'ma_longterm'] = dataframe_longterm['ma_longterm'][old_index]
            old_index = index
        return dataframe
    
    
        
    def bull_div(self, price, rsi, price_prominence=1, rsi_prominence=1):
        current_price = price[-1]
        latest_price = price[-2]
        current_rsi = rsi[-1]
        latest_rsi = rsi[-2]
    
        if current_rsi < latest_rsi and current_price < latest_price:
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
        minrsi = 1000
        minprice = dataframe['close'][0]*100
        minrsibar =0 #initialize at 0
        
        
        oldminprice = 0 
        oldminrsi = 100
        oldminrsibar = 0
        bullish_df = dataframe.loc[dataframe['close'] > dataframe['ma_longterm']]
        for index, row in dataframe.iterrows():
            irsi = dataframe['rsi'][index]
            os = irsi < self.osLevel
            if os: 
                if irsi < minrsi:
                    minrsi = irsi
                    minrsibar = index
                minprice = min(minprice, dataframe['low'][index] )
                
            
            if qtpylib.crossed_above(dataframe['rsi'], self.osLevel)[index]:
                div = minprice < oldminprice and minrsi > oldminrsi and minrsibar - oldminrsibar > 200
                if div:
                    #send a buy signal
                    dataframe.loc[index, 'buy']= 1
                
                oldminrsi = minrsi
                oldminprice = minprice
                oldminrsibar = minrsibar
                
                #reinitialize minrsi and minprice
                minrsi = 1000
                minprice = dataframe['close'][0]*100
                """
                rsi_set= dataframe['rsi'][index-self.div_window:index]
                price_low_set = dataframe['low'][index-self.div_window:index]
                ma_long = dataframe['ma_long'][index]
                ma_short = dataframe['ma_short'][index]
                price_prominence = ma_long * 0.01
                is_div = self.bull_div(price_low_set, rsi_set, price_prominence, 5)
                if is_div and ma_short < ma_long:
                    dataframe.loc[index, 'buy']= 1
                
                # rsi_set = rsi[index-self.div_window:index]   
                 """          
    
        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the sell signal for the given dataframe
        :param dataframe: DataFrame
        :param metadata: Additional information, like the currently traded pair
        :return: DataFrame with buy column
        """
        #dataframe.loc[
        #   dataframe['close'] > dataframe['bb_upper']
        #    ,'sell'] =1
        return dataframe
        