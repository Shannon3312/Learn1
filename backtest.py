# -*- coding: utf-8 -*-
"""
Created on Mon Aug 14 16:13:50 2017

@author: EicW
"""

import pandas as pd
import shutil
import datetime

DATETIME_STR = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
shutil.copy(__file__, r'backup\\'+'.'.join((__file__,DATETIME_STR,'bak')))

filename = 'rb_hour.csv'
df = pd.read_csv(filename, index_col=0)
df = df[df['volume']>0] # 删除无成交时段
df = df.set_index(pd.DatetimeIndex(pd.to_datetime(df.index)))
df = df[df.index.hour != 9] # 删除结束时间为9点的盘前集合竞价数据
# 合并12点和14点的bar
for row in df.iterrows():
    if row[0].hour == 12:
        open_ = row[1]['open']
        high = row[1]['high']
        low = row[1]['low']
#        close = row[1]['close']
        volume = row[1]['volume']
        amt = row[1]['amt']
    elif row[0].hour == 14:
        df.ix[row[0], 'open'] = open_
        df.ix[row[0], 'high'] = max(high, row[1]['high'])
        df.ix[row[0], 'low'] = min(low, row[1]['low'])
        df.ix[row[0], 'volume'] += volume
        df.ix[row[0], 'amt'] += amt
df = df[df.index.hour != 12]
        
import talib

FASTPERIOD = 12
SLOWPERIOD = 26
SIGNALPERIOD = 9
macd = talib.MACD(df['close'].values, FASTPERIOD, SLOWPERIOD, SIGNALPERIOD)
df['macd'] = macd[0] # macd dif, ema之差
df['macdsignal'] = macd[1] # signal dea，diff之ema
df['macdhist'] = macd[2] # diff-dea
kd = talib.STOCH(df['high'].values, df['low'].values, df['close'].values)
df['slowk'] = kd[0]
df['slowd'] = kd[1]

# macd顶背离、底背离
df['macd_bl1'] = (df.close > df.close.shift(1)) & (df.macd < df.macd.shift(1)) 
df['macd_bl2'] = (df.close < df.close.shift(1)) & (df.macd > df.macd.shift(1))

df['macd_glod'] = (df.macd > df.macdsignal) & (df.macd.shift(1)<df.macdsignal.shift(1))
df['macd_dead'] = (df.macd > df.macdsignal) & (df.macd.shift(1)>df.macdsignal.shift(1))

df['kd_glod'] = (df.slowk > df.slowd) & (df.slowk.shift(1)<df.slowd.shift(1))
df['kd_dead'] = (df.slowk > df.slowd) & (df.slowk.shift(1)>df.slowd.shift(1))

df['close1'] = df['close'].shift(1)  
df['atr'] = df.apply(lambda x: max(x['high']-x['low'], \
  abs(x['close']-x['close1'])), 1)
df['atr6'] = df['atr'].rolling(6).mean()

df['ma21'] = df.close.rolling(21).mean()
df['high6'] = df.high.rolling(6).max()
df['high4'] = df.high.rolling(4).max()
df['high61'] = df['high6'].shift(1)
df['high41'] = df['high4'].shift(1)
df['low6'] =df.low.rolling(6).min()
df['low4'] =df.low.rolling(4).min()
df['low61'] = df['low6'].shift(1)
df['low41'] = df['low4'].shift(1)

df['pos'] = 0
df['cost'] = None
pos = 0
cost = None
for row in df.iterrows():
    if row[1]['atr'] >= 1.2*row[1]['atr6'] and \
    row[1]['high'] > row[1]['high61'] and \
    row[1]['close'] > row[1]['low'] + 0.5*(row[1]['high']- row[1]['low']) and \
    row[1]['close'] > row[1]['ma21'] and \
    row[1]['close'] - row[1]['low6'] > row[1]['atr'] *2/3 + 2 and\
    pos <= 0:
        pos = 1
        cost= row[1]['close']
    elif pos>0 and row[1]['close'] < row[1]['low6'] - 2:
        pos = 0
        cost =None
    elif pos == 1 and row[1]['high'] < row[1]['high41']:
        pos = 0.5
    elif pos>0 and row[1]['close'] < row[1]['ma21']:
        pos = 0
        cost = None
    elif row[1]['atr'] >= 1.2*row[1]['atr6'] and \
    row[1]['low'] < row[1]['low61'] and \
    row[1]['close'] < row[1]['high'] - 0.5*(row[1]['high']- row[1]['low']) and \
    row[1]['close'] < row[1]['ma21'] and \
    row[1]['high6'] - row[1]['close'] > row[1]['atr'] *2/3 + 2 and\
    pos >= 0:
        pos = -1
        cost= row[1]['close']
    elif pos<0 and row[1]['close'] > row[1]['high6'] + 2:
        pos = 0
        cost =None
    elif pos == -1 and row[1]['low'] > row[1]['low41']:
        pos = -0.5
    elif pos<0 and row[1]['close'] > row[1]['ma21']:
        pos = 0
        cost = None
        
    df.ix[row[0],'pos'] = pos
    df.ix[row[0],'cost'] = cost
    
df['ret1'] = df['close'].pct_change().shift(-1)
df['pnl'] = df['ret1']*df['pos']
df['pnl_cum'] = df['pnl'].cumsum()
df[['close','pnl_cum']].plot(secondary_y='close', title=filename)
#df[['close','pnl_cum','pos']].plot(secondary_y='close', ylim=(-1.2,1.2))
df.to_csv(filename+'.backtest.csv')
