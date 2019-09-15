# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement

import talib.abstract as ta
from pandas import DataFrame, Series

import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.indicator_helpers import fishers_inverse
from freqtrade.strategy.interface import IStrategy


def PPSR(df):
    PP = Series((df['high'] + df['low'] + df['close']) / 3)
    R1 = Series(2 * PP - df['low'])
    S1 = Series(2 * PP - df['high'])
    R2 = Series(PP + df['high'] - df['low'])
    S2 = Series(PP - df['high'] + df['low'])
    R3 = Series(df['high'] + 2 * (PP - df['low']))
    S3 = Series(df['low'] - 2 * (df['high'] - PP))
    psr = {'PP': PP, 'R1': R1, 'S1': S1, 'R2': R2, 'S2': S2, 'R3': R3, 'S3': S3}
    PSR = DataFrame(psr)
    df = df.join(PSR)
    return df


def PPSRFIB(df):
    PP = Series((df['high'] + df['low'] + df['close']) / 3)
    S1 = Series(PP - (0.382 * (df['high'] - df['low'])))
    S2 = Series(PP - (0.618 * (df['high'] - df['low'])))
    S3 = Series(PP - (1 * (df['high'] - df['low'])))
    R1 = Series(PP + (0.382 * (df['high'] - df['low'])))
    R2 = Series(PP + (0.618 * (df['high'] - df['low'])))
    R3 = Series(PP + (1 * (df['high'] - df['low'])))
    psr = {'PP': PP, 'R1': R1, 'S1': S1, 'R2': R2, 'S2': S2, 'R3': R3, 'S3': S3}
    PSR = DataFrame(psr)
    df = df.join(PSR)
    return df


class PPRSIStrategy3(IStrategy):
    """
    Default Strategy provided by freqtrade bot.
    You can override it with your own strategy
    """

    # Optimal stoploss designed for the strategy
    stoploss = -0.1

    # Optimal ticker interval for the strategy
    ticker_interval = '15m'

    # Optional order type mapping
    order_types = {
        'buy': 'limit',
        'sell': 'limit',
        'stoploss': 'limit',
        'stoploss_on_exchange': False
    }

    # Optional time in force for orders
    order_time_in_force = {
        'buy': 'gtc',
        'sell': 'gtc',
    }

    def informative_pairs(self):
        """
        Define additional, informative pair/interval combinations to be cached from the exchange.
        These pair/interval combinations are non-tradeable, unless they are part
        of the whitelist as well.
        For more information, please consult the documentation
        :return: List of tuples in the format (pair, interval)
            Sample: return [("ETH/USDT", "5m"),
                            ("BTC/USDT", "15m"),
                            ]
        """
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Adds several different TA indicators to the given DataFrame

        Performance Note: For the best performance be frugal on the number of indicators
        you are using. Let uncomment only the indicator you are using in your strategies
        or your hyperopt configuration, otherwise you will waste your memory and CPU usage.
        :param dataframe: Raw data from the exchange and parsed by parse_ticker_dataframe()
        :param metadata: Additional information, like the currently traded pair
        :return: a Dataframe with all mandatory indicators for the strategies
        """

        # Momentum Indicator
        # ------------------------------------
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe)

        # MFL
        dataframe['mfi'] = ta.MFI(dataframe)

        # Ema Moving Average
        dataframe['ema2'] = ta.EMA(dataframe, timeperiod=2)

        # Pivot Points
        dataframe = PPSRFIB(dataframe)

        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the buy signal for the given dataframe
        :param dataframe: DataFrame
        :param metadata: Additional information, like the currently traded pair
        :return: DataFrame with buy column
        """
        buy_in_buy_trend = (
            (dataframe['close'] > dataframe['PP'] * 0.6) &
            (dataframe['close'] > dataframe['ema2'] * 1.005) &
            (dataframe['mfi'] > 15)
        )
        buy_in_sell_trend = ((dataframe['close'] <= dataframe['S1']) &
                             (dataframe['mfi'] > 20)
                             )
        dataframe.loc[
            (
                buy_in_buy_trend | buy_in_sell_trend
            ),
            'buy'] = 1

        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the sell signal for the given dataframe
        :param dataframe: DataFrame
        :param metadata: Additional information, like the currently traded pair
        :return: DataFrame with buy column
        """
        sell_in_buy_trend = ((dataframe['close'] >= dataframe['R1']) &
                             (dataframe['mfi'] < 75)
                             )

        sell_in_sell_trend = (
            (dataframe['close'] < dataframe['PP']) &
            (dataframe['close'] < dataframe['ema2']) &
            (dataframe['mfi'] < 70)
        )

        dataframe.loc[
            (
                sell_in_buy_trend | sell_in_sell_trend
            ),
            'sell'] = 1
        return dataframe
