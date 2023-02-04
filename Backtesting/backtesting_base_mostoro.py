# Python Backtesting Script
#
# (c) MOSTORO
# QSociety

from typing_extensions import Self
import pandas as pd
from arctic import Arctic
from arctic.date import DateRange
import matplotlib.pyplot as plt
import numpy as np
from arctic.hooks import register_get_auth_hook
from arctic.auth import Credential


class Backtesting():
    #'''Base class for event-based backtesting of trading strategies'''
    #position = 0: out of market, 1: long, -1: short
    #dates should be in the format '2022-06-12'
    def __init__(self, start, end, symbol, amount, verbose=False):
        self.start = start  
        self.end = end 
        self.symbol =  symbol
        self.amount = amount
        self.symbol = 'MES'
        self.position = 0 
        self.margin = True 
        self.instruments = pd.read_csv(r'instruments.csv').set_index('symbol')  
        self.instrument = self.instruments.loc[self.symbol]
        self.init_margin = float(self.instrument.init_margin)
        self.maint_margin = float(self.instrument.maint_margin)
        self.tick_size = float(self.instrument.tick_size)
        self.comm_value = float(self.instrument.comm_value)
        self.slippage = float(self.instrument.tick_size * 2) 
        self.point_value = float(self.instrument.point_value)
        self.margin_call_signal = 0
        self.profit = pd.DataFrame(columns = ['Instrument', 'Direction', 'Contracts', 'Commision', 'Price', 'Stop', 'Target', 'Time',
        'Position', 'Profit'])
        self.stop_loss = 5
        self.target = 10
        self.bar_time = '5S'
        self.get_data()
        

    # Arctic authentication:
    def arctic_auth_hook(self, mongo_host, app, database):
        return Credential(database='arctic',user='camilo',password='Mr.robot#77')

    

    #Retrieves and prepares the data
    def get_data(self):
        register_get_auth_hook(self.arctic_auth_hook)
        store = Arctic('137.184.109.220')
        library = store['Futures_Historical_Ticks']


        data = library.read(self.symbol, date_range=DateRange('%s' % self.start, '%s' % self.end)).data


        Open = data.Last.resample(self.bar_time).first()
        High = data.Last.resample(self.bar_time).max()
        Low = data.Last.resample(self.bar_time).min()
        Close = data.Last.resample(self.bar_time).last()
        Volume = data.Volume.resample(self.bar_time).sum()

        self.data = pd.concat([Open, High, Low, Close, Volume],axis=1).dropna()
        self.data.columns = ['open', 'high', 'low', 'close', 'volume']
        print('%s Data Loaded! in backtesting base' % self.symbol)

    
    def get_date(self, bar): 
        #returns the date and price for the given bar
        # global self.date
        # global self.weekday
        # global self.hour

        self.date = self.data.index[bar]    
        self.weekday = self.date.weekday()     
        self.hour = self.data.index[bar].time()

    def calculate_margins(self, price=0, contracts=0): 
        'Calcultes the margins, according with each market'
        # global init_margin
        # global maint_margin
        self.init_margin = self.init_margin *  contracts
        self.maint_margin = self.maint_margin * contracts

    def calculate_commision(self, contracts): 
        #calculate commision per trade
        # global self.commision
        self.commision = self.comm_value * contracts
        return self.commision


    def place_order(self, direction, price, contracts, bar): 
        
#         global self.position
#         global self.init_margin
#         global self.profit
#         global self.amount
#         global self.commision
        
        if self.position == 0:
            # global self_init_marginß
            # global self.profit
            self.calculate_margins(contracts=contracts)
            if self.amount >= self.init_margin:
                if direction == 'Long':
                    self.position += contracts  
                    self.commision = self.calculate_commision(contracts=contracts)
                    trade = {
                        'Instrument': self.symbol, 'Direction': direction,  'Contracts': contracts,
                        'Commision': self.commision, 'Price': price, 'Stop': price - self.stop_loss,
                        'Target': price + self.target, 'Time': self.data.index[bar], 'Position': self.position}
                elif direction == 'Short':
                    self.position -= contracts
                    self.commision = self.calculate_commision(contracts=contracts)
                    trade = {
                        'Instrument': self.symbol, 'Direction': direction,  'Contracts': contracts,
                        'Commision': self.commision, 'Price': price, 'Stop': price + self.stop_loss,
                        'Target': price - self.target, 'Time': self.data.index[bar], 'Position': self.position}
                self.profit = self.profit.append(trade, ignore_index=True)
                self.trades()
            else:
                print('Amount is not enough')
                #exits

        else:
            if direction == 'Short':
                price = price
                self.position -= contracts
            elif direction == 'Long':
                self.position += contracts
            trade = {
                'Instrument': self.symbol, 'Direction': direction,  'Contracts': contracts, 'Commision': self.commision,
                'Price': price, 'Stop': 0, 'Target': 0, 'Time': self.data.index[bar], 'Position': self.position}
            self.profit = self.profit.append(trade, ignore_index=True)
            self.trades()


    def trades(self):
        # Calculate the last self.profit of the last trade
        if self.profit['Position'].iloc[-1] == 0:
            if self.profit['Position'].iloc[-1] - self.profit['Position'].iloc[-2] == 1:
                self.profit.loc[self.profit.index[-1], 'Profit'] = ((self.profit['Price'].iloc[-2] - self.profit['Price'].iloc[-1]) * self.point_value) - self.profit['Commision'].iloc[-2] -  self.profit['Commision'].iloc[-1]
                self.profit.loc[self.profit.index[-1], '%_Profit'] = self.profit['Profit'].iloc[-1] / self.profit['Price'].iloc[-2]

            elif self.profit['Position'].iloc[-1] - self.profit['Position'].iloc[-2] == -1:
                self.profit.loc[self.profit.index[-1], 'Profit'] = ((self.profit['Price'].iloc[-1] - self.profit['Price'].iloc[-2]) * self.point_value) - self.profit['Commision'].iloc[-1] -  self.profit['Commision'].iloc[-2]
                self.profit.loc[self.profit.index[-1], '%_Profit'] = self.profit['Profit'].iloc[-1] / self.profit['Price'].iloc[-2]
        else:
            self.profit.loc[self.profit.index[-1], 'Profit'] = 0
            self.profit.loc[self.profit.index[-1], '%_Profit'] = 0
        self.profit.fillna(0)
        #self_amount +=  self.profit.loc[self.profit.index[-1], 'self.profit']



    def metrics(self):
        #Items for evaluate the performance
        print('-' * 50)
        #Net Profit
        profit_copy = self.profit.copy()
        profit_copy['Net_Profit'] = profit_copy['Profit'].cumsum()
        print('Net Profit: {}'.format(profit_copy['Net_Profit'].iloc[-1].round(2)))

        #profit factor
        profit_factor = profit_copy['Profit'][profit_copy['Profit'] > 0].sum().round(2) / abs(profit_copy['Profit'][profit_copy['Profit'] < 0]).sum().round(2)
        print('profit_factor: {:.2f}'.format(profit_factor))

        #Max Drawdown
        max_drawdown = round(((profit_copy['Net_Profit'] / profit_copy['Net_Profit'].cummax() - 1).fillna(0).replace([-np.inf]).dropna()).min(), 2)
        print('max_drawdown: {}%'.format(max_drawdown*100))


        #Sharpe Ratio
        try:
            sharpe_ratio = round(profit_copy['Profit'][profit_copy['Profit'] != 0].mean() / profit_copy['Profit'][profit_copy['Profit'] != 0].std(), 2)
            #print('sharpe_ratio: {:.2f}'.format(sharpe_ratio))
        except:
            sharpe_ratio = round(profit_copy['Profit'][profit_copy['Profit'] != 0].mean() / 1, 2)
            print('NA, Deviation 0')

        annualize_sharpe_ratio = (252 ** 0.5) * sharpe_ratio #252 trading days in the year
        print('annualize_sharpe_ratio: {:.2f}'.format(annualize_sharpe_ratio))

        #Sortino Ratio
        try:
                annualize_sortino_ratio = ((self.reduce(self.operator.mul, (1 + self.profit['%_Profit'].where(self.profit['%_Profit'] != 0).dropna()), 1) - 1)) / \
                (self.statistics.stdev(self.profit['%_Profit'].where(self.profit['%_Profit'] < 0, 0).tolist()) * 252**0.5)
                #print('sortino_ratio: {:.2f}'.format(sortino_ratio))
                print('annualized_sortino_ratio: {:.2f}'.format(annualize_sortino_ratio))
        except:
                #annualize_sortino_ratio = round(profit_copy['Profit'][profit_copy['Profit'] != 0].mean(),2) / 1
                print('annualized_sortino_ratio: NA (Deviation 0)')



        #Ulcer index
        ulcer_index = ((((profit_copy['Net_Profit'] / profit_copy['Net_Profit'].cummax() - 1).fillna(0).replace([-np.inf]).dropna()) ** 2).sum() / profit_copy['Profit'].count()) ** 0.5
        annualized_ulcer_index = (252 ** 0.5) * ulcer_index

        #print('ulcer_index: {:.2f}'.format(ulcer_index))
        print('annualized_ulcer_index: {:.2f}'.format(annualized_ulcer_index))

        #UPI - ulcer performance index
        try:
            upi = round(profit_copy['Profit'][profit_copy['Profit'] != 0].mean() / ulcer_index, 2)
            #print('upi: {:.2f}'.format(upi))
        except:
            upi = round(profit_copy['Profit'][profit_copy['Profit'] != 0].mean() / 1, 2)
            print('NA, Deviation 0')

        annualize_upi = (252 ** 0.5) * upi #252 trading days in the year
        print('annualize_upi: {:.2f}'.format(annualize_upi))


        #Percentaje profitable
        percentaje_profitable = profit_copy['Profit'][profit_copy['Profit'] > 0].count() / profit_copy['Position'][profit_copy['Position'] != 0].count() * 100

        print('percentaje_profitable: {:.2f}'.format(percentaje_profitable))
        print('-' * 50)

        #Equity Curve
        equity_curve = profit_copy[profit_copy['Position'] == 0]['Net_Profit'].plot(figsize=(12,8), title='Equity Curve', marker='o')
        plt.show()




# if __name__ == '__main__':
#     back = Backtesting(symbol='MES', start='2022-06-12', end='2022-08-18', amount=5000, verbose=False)
#     print('test')
#     print(back.data.info())
#     print(back.data.head())
#     print(back.data.tail())


