#!/user/bin/env python3
# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import math
import matplotlib.pyplot as plt
from datetime import datetime
from scipy.optimize import minimize
import warnings

warnings.filterwarnings('ignore')

plt.rcParams['font.sans-serif'] = ['SimHei']
root = r'.\小组课题\code'

"""
1、输入：预期收益、最大回撤、定投金额（固定）、定投频率、预计可投资金额、单月消费（国家统计局：人均消费支出）——初始配置比例
2、定投金额，观点更新（定投不够起投金额）
3、来一大笔钱：
4、取一小笔钱（从零钱宝取，低于零钱宝阈值）
5、取一大笔钱：零钱宝取完，最小交易费用/止盈/等比例
6、根据估值信号确定定投量
8、和个人随便配的策略对比回测
"""

# 假设的 Excel 数据结构:
# 预期收益 | 最大回撤 | 权益类 | 债券类 | 货币类
df = pd.read_excel(r"./data/权重对照表.xlsx", sheet_name=0)

# equity = pd.read_excel(root + r'\data\指数收益\国证A指日度行情.xlsx', sheet_name=0, dtype={'time': str})
# bond = pd.read_excel(root + r'\data\指数收益\10年国债日度行情.xlsx', sheet_name=0, dtype={'time': str})
# money = pd.read_excel(root + r'\data\指数收益\货币基金指数.xlsx', sheet_name=0, dtype={'time': str})
# days = pd.read_csv(root + r'\data\交易日期.csv')
# days['weekly'] = days['isWeekEnd']
# days['monthly'] = days['isMonthEnd']
# biweek = days[days['weekly'] == 1]['weekly'].reset_index()
# for i in range(len(biweek)):
#     if i % 2 == 1:
#         biweek.loc[i, 'weekly'] = 0
# biweek = biweek.set_index('index')
# days['biweekly'] = biweek
# days['biweekly'] = days['biweekly'].fillna(0)
# days['calendarDate'] = pd.to_datetime(days['calendarDate'])
# days['calendarDate'] = days['calendarDate'].apply(lambda x: x.strftime("%Y%m%d"))
# days = days.rename(columns={'calendarDate': 'time'})
# temp = pd.read_excel(root + r'\data\宽基指数估值.xlsx', sheet_name=0, header=1)
# temp = temp[['time', '399317.SZ']].rename(columns={'399317.SZ': 'value'})
# temp['time'] = temp['time'].apply(lambda x: x.strftime("%Y%m%d"))
# temp['value'] = temp['value'].shift(1)
# temp = pd.merge(temp, days[['time', 'weekly', 'biweekly', 'monthly']], on='time', how='left')
# temp = pd.merge(temp, equity[['time', 'chgPct']], on='time', how='left').rename(columns={'chgPct': 'Equity'})
# temp = pd.merge(temp, bond[['time', 'chgPct']], on='time', how='left').rename(columns={'chgPct': 'Bond'})
# temp = pd.merge(temp, money[['time', 'chgPct']], on='time', how='left').rename(columns={'chgPct': 'Money'})
# temp = temp.dropna().reset_index(drop=True)
# temp.to_excel(root + r'\data\15-23年基础数据.xlsx', index=False)
# temp.to_feather(root + r'\data\15-23年基础数据.feather')

temp = pd.read_feather(root + r'\data\15-23年基础数据.feather')
trade_days = temp['time'].tolist()


def get_initial_weight(exp_return, max_drawdown):
    row = df[(df['预期收益'] == exp_return / 100) & (df['最大回撤'] == max_drawdown / 100)]
    if not row.empty:
        return row.iloc[0][['权益类', '债券类', '货币类']]
    else:
        return None


def update_signal(start, end='88888888'):
    start_idx = max(0, min(temp[temp['time'] >= start].index) - 1)
    data = temp.loc[start_idx:]
    data = data[data['time'] <= end]
    data = data.reset_index(drop=True)
    data['equ_ratio'] = np.nan
    # for idx, row in data.iterrows():
    #     if row['value'] < 0.25:
    #         data.loc[idx, 'equ_ratio'] = 0.7
    #     elif row['value'] > 0.75:
    #         data.loc[idx, 'equ_ratio'] = 0.1
    #     else:
    #         data.loc[idx, 'equ_ratio'] = 0.5
    for idx, row in data.iterrows():
        if row['value'] < 0.1:
            data.loc[idx, 'equ_ratio'] = 0.9
        elif (row['value'] >= 0.1) & (row['value'] < 0.35):
            data.loc[idx, 'equ_ratio'] = 0.7
        elif (row['value'] >= 0.35) & (row['value'] < 0.65):
            data.loc[idx, 'equ_ratio'] = 0.5
        elif (row['value'] >= 0.65) & (row['value'] < 0.8):
            data.loc[idx, 'equ_ratio'] = 0.3
        elif row['value'] >= 0.8:
            data.loc[idx, 'equ_ratio'] = 0.1

    data['equ_ratio'] = data['equ_ratio'].fillna(method='pad')
    data['equ_ratio'] = data['equ_ratio'].shift(1)  # * 0.9
    output = data[['time']]
    output['权益类'] = data['equ_ratio'] * 0.9
    output['债券类'] = (1 - data['equ_ratio']) * 0.9
    return output.dropna().reset_index(drop=True)


def find_closest(initial, signal, money_lb, bias=0.1):
    """
    结合观点和初始收益-风险所得权重，优化求解一定偏离限制内的权重分配
    Args:
        initial: 初始收益-风险所得权重
        signal: 最新观点对应权重
        money_lb: 最低货币占比，一般取为3 * 月消费金额 / 当前资产总额
        bias: 偏差限制，权重点距离

    Returns:

    """
    a = signal['权益类'] / signal['债券类']
    x0 = np.array(initial)

    def func(x):
        return (x[0] - a * x[1]) ** 2

    def func_J(x):
        dfdx0 = 2 * (x[0] - a * x[1])
        dfdx1 = -2 * a * (x[0] - a * x[1])
        return np.array([dfdx0, dfdx1])

    def cons_f(x):
        return bias ** 2 - ((x[0] - x0[0]) ** 2 + (x[1] - x0[1]) ** 2 + (x0[0] + x0[1] - x[0] - x[1]) ** 2)

    def cons_J(x):
        dfdx0 = 4 * (x[0] - x0[0]) + 2 * (x[1] - x0[1])
        dfdx1 = 4 * (x[1] - x0[1]) + 2 * (x[0] - x0[0])
        return -1 * np.array([dfdx0, dfdx1])

    cons = (
        {'type': 'ineq', 'fun': cons_f, 'jac': cons_J},  # 约束偏离程度
        {'type': 'ineq', 'fun': lambda x: 1 - x[0] - x[1] - money_lb}  # 货币占比
    )
    res = minimize(func, x0[0:2], jac=func_J, constraints=cons, method='SLSQP',
                   options={'disp': False, 'ftol': 0.01})
    if res.success:
        weight = res.x
        return np.append(weight, values=1 - weight[0] - weight[1])
    else:
        print('迭代终止原因：', res.message)
        return None


class Account:
    def __init__(self,
                 startdate,
                 exp_return,
                 max_drawdown,
                 initial_invest,
                 auto_invest,
                 auto_freq: str,
                 consume: int):
        """
        startdate: YYYYmmdd
        exp_return
        max_drawdown
        iniial_invest:
        auto_invest: 定投金额，必须大于1000
        auto_freq: {'weekly', 'biweekly', 'monthly'}
        consume: 消费金额
        bias偏离权重限额
        """
        if startdate not in trade_days:
            startdate = min([x for x in trade_days if x >= startdate])
        self.startdate = startdate
        self.exp_return = exp_return
        self.max_drawdown = max_drawdown
        self.initial_invest = initial_invest
        self.asset = pd.DataFrame()  # 账户总资金量&资产配置情况
        self.records = pd.DataFrame()
        self.benchmark_asset = pd.DataFrame()
        # if auto_invest < 1000:
        #     raise ValueError('定投金额须大于1000元，请重新输入！')
        self.auto_invest = auto_invest
        self.auto_freq = auto_freq
        self.consume = consume
        self.initial_weight = get_initial_weight(self.exp_return, self.max_drawdown)
        self.signals = update_signal(startdate).set_index('time')
        weight = find_closest(self.initial_weight, self.signals.iloc[0, :], self.consume * 3 / initial_invest)
        if weight is None:
            weight = find_closest(self.initial_weight,
                                  self.signals.iloc[0, :], 0.1)
        initial_record = pd.DataFrame([[startdate, initial_invest, round(initial_invest * weight[0] / 100) * 100,
                                        round(initial_invest * weight[1] / 100) * 100,
                                        initial_invest - (round(initial_invest * weight[0] / 100) + round(
                                            initial_invest * weight[1] / 100)) * 100]],
                                      columns=['time', 'Asset', 'Equity', 'Bond', 'Money']).set_index('time')
        self.records = self.records.append(initial_record)
        self.asset = self.asset.append(initial_record)  # 建仓当日
        self.benchmark_asset = pd.concat([self.benchmark_asset, initial_record])
        # # 同步建立基准组合
        # weight = self.initial_weight
        # equity_w = weight[0] / (1 - weight[2])
        # bond_w = weight[1] / (1 - weight[2])
        # initial_invest = self.asset.iloc[0, :]['Asset']
        # if initial_invest * weight[2] > 3 * self.consume:
        #     new_asset = pd.DataFrame([[startdate, initial_invest, round(initial_invest * weight[0] / 100) * 100,
        #                                round(initial_invest * weight[1] / 100) * 100,
        #                                initial_invest - (round(initial_invest * weight[0] / 100) + round(
        #                                    initial_invest * weight[1] / 100)) * 100]],
        #                              columns=['time', 'Asset', 'Equity', 'Bond', 'Money']).set_index('time')
        #     self.benchmark_asset = pd.concat([self.benchmark_asset, new_asset])
        # else:
        #     money = 3 * self.consume
        #     new_asset = pd.DataFrame([[startdate, initial_invest,
        #                                round((initial_invest - money) * equity_w / 100) * 100,
        #                                round((initial_invest - money) * bond_w / 100) * 100,
        #                                money]],
        #                              columns=['time', 'Asset', 'Equity', 'Bond', 'Money']).set_index('time')
        #     self.benchmark_asset = pd.concat([self.benchmark_asset, new_asset])
        startdate = datetime.strptime(startdate, '%Y%m%d').strftime('%Y-%m-%d')
        print(f"初始配置于{startdate}建仓完成，配置金额如下："
              f"\n总资产：{self.asset['Asset'].values[0]}"
              f"\n权益类：{self.asset['Equity'].values[0]}"
              f"\n债券类：{self.asset['Bond'].values[0]}"
              f"\n货币类：{self.asset['Money'].values[0]}")
        
    def find_allocation(self, current_portf: np.array, objective_portf: np.array, amount: int):
        """
        最优化求解资金分配情况
        Args:
            current_portf: 当前资产配置情况
            objective_portf: 目标资产配置情况
            amount: 待投资金量

        Returns:

        """

        def func(x):
            # 二维函数
            return (current_portf[0] - objective_portf[0] + x[0]) ** 2 + \
                (current_portf[1] - objective_portf[1] + x[1]) ** 2 + \
                (x[0] + x[1] - current_portf[2] + objective_portf[2] - amount) ** 2

        def func_J(x):
            dfdx0 = 2 * (x[0] + current_portf[0] - objective_portf[0]) + \
                    2 * (x[0] + x[1] - current_portf[2] + objective_portf[2] - amount)
            dfdx1 = 2 * (x[1] + current_portf[1] - objective_portf[1]) + \
                    2 * (x[0] + x[1] - current_portf[2] + objective_portf[2] - amount)
            return np.array([dfdx0, dfdx1])

        cons = (
            # {'type': 'ineq', 'fun': lambda x: x[0] * (x[0] -1000)},  # >=1000
            {'type': 'ineq', 'fun': lambda x: current_portf[2] + amount - x[0] - x[1] - 3 * self.consume}
            # 货币类大于阈值
        )
        res = minimize(func, np.array([amount, 0]), jac=func_J, constraints=cons, bounds=((0, None), (0, None)),
                       method='SLSQP', options={'disp': False, 'ftol': 100})
        if res.success:
            allocation = res.x
            # TODO 买入权益类不足1000元怎么处理？
            for i in range(len(allocation)):
                allocation[i] = round(allocation[i] / 1000) * 1000
            allocation = np.append(allocation, values=amount - allocation[0] - allocation[1])
            return allocation
        else:
            print('迭代终止原因：', res.message)
            return None

    def add_money(self, date, amount):
        """
        日中加仓，返回加仓分配记录，到T+1日才计算收益
        Args:
            date: 加仓日期
            amount: 加入金额

        Returns: 加仓记录

        """

        if date not in trade_days:
            date = min([x for x in trade_days if x >= date])
        date_1 = trade_days[trade_days.index(date) - 1]  # 前一个交易日
        current_asset = self.asset.loc[date_1].copy()
        current_asset['Asset'] += amount
        if current_asset['Money'] + amount <= 3 * self.consume:
            record = pd.DataFrame([[date, 'in', amount, 0, 0, amount]],
                                columns=[['time', 'type', 'Asset', 'Equity', 'Bond', 'Money']])
            self.records = pd.concat([self.records, record])
            return
        elif current_asset['Money'] <= 3 * self.consume:
            money_amount = math.ceil((3 * self.consume - current_asset['Money']) / 1000) * 1000
            amount = amount - money_amount
            current_asset['Money'] += money_amount
        else:
            money_amount = 0
        signal = self.signals.loc[date]
        money_lb = 3 * self.consume / current_asset['Asset']
        weight = find_closest(self.initial_weight, signal, money_lb)
        objective_portf = current_asset['Asset'] * weight
        allocation = self.find_allocation(np.array(current_asset[['Equity', 'Bond', 'Money']]),
                                          objective_portf, amount)
        record = pd.DataFrame(
            [[date, amount + money_amount, allocation[0], allocation[1], allocation[2] + money_amount]],
            columns=['time', 'Asset', 'Equity', 'Bond', 'Money']).set_index('time')
        self.records = pd.concat([self.records, record])
        return

    # def get_money(amount, weight, method='最小交易费用'):
    # TODO

    def update_returns(self, date):
        """
        每个交易日初更新*前一天*的收益，当日新增资产暂不计算收益，直接加
        Args:
            date:

        Returns:

        """
        date_1 = trade_days[trade_days.index(date) - 1]
        return_chg = temp.loc[temp['time'] == date_1, ['Equity', 'Bond', 'Money']]
        new_asset = self.asset.loc[date_1].copy()  # Series
        for x in ['Equity', 'Bond', 'Money']:
            new_asset[x] = new_asset[x] * (1 + return_chg[x].values)  # round(value, 2) 保留两位小数
        new_asset['Asset'] = new_asset['Equity'] + new_asset['Bond'] + new_asset['Money']
        if (date_1 in self.records.index.tolist()) & (date_1 != self.startdate):  # 检查前一天有无日内交易
            find_records = self.records.loc[date_1]  # Series
            for x in ['Asset', 'Equity', 'Bond', 'Money']:
                new_asset[x] += find_records[x]
        self.asset.loc[date_1] = new_asset
        self.asset.loc[date] = new_asset
        return

    def auto_run(self, start=None, end=None):
        """

        Args:
            start:
            end: 持有期末

        Returns:

        """
        if start is None:
            start = self.startdate
            start = min([x for x in trade_days if x > start])
        else:
            start = min([x for x in trade_days if x > start])
        if end is None:
            end = datetime.now().strftime('%Y%m%d')
        if start not in self.asset.index.tolist():
            add = self.asset.iloc[[-1], :].copy()
            add.index = [start]
            self.asset = self.asset.append(add)
        holding_days = [x for x in trade_days if (x > start) & (x <= end)]
        if self.auto_freq is not None:
            auto_invest_days = temp.loc[(temp['time'] > start) & (temp[self.auto_freq] == 1), 'time'].tolist()  # 定投日
            for day in holding_days:
                self.update_returns(day)  # 日初更新收益
                if day in auto_invest_days:
                    self.add_money(day, self.auto_invest)
            if end in holding_days:
                self.asset = self.asset.drop(index=holding_days[-1])
        else:
            for day in holding_days:
                self.update_returns(day)  # 日初更新收益
            if end in holding_days:
                self.asset = self.asset.drop(index=holding_days[-1])
            # last_asset = self.asset.loc[start].copy()
            # return_chg = temp.loc[(temp['time'] < end) & (temp['time'] > start), ['time', 'Equity', 'Bond', 'Money']]
            # value_chg = (return_chg[['Equity', 'Bond', 'Money']] + 1).cumprod()
            # new_asset = pd.DataFrame(columns=['Equity', 'Bond', 'Money'], index=return_chg['time'].tolist())
            # for x in ['Equity', 'Bond', 'Money']:
            #     new_asset[x] = last_asset[x] * value_chg[x].values  # round(value, 2) 保留两位小数
            # assets = new_asset['Equity'] + new_asset['Bond'] + new_asset['Money']
            # new_asset.insert(0, 'Asset', assets)
            # self.asset = pd.concat([self.asset, new_asset])
        return

    def add_benchmark(self, date, amount):
        if date not in trade_days:
            date = min([x for x in trade_days if x >= date])
        date_1 = trade_days[trade_days.index(date) - 1]  # 前一个交易日
        current_asset = self.benchmark_asset.loc[date_1].copy()
        if current_asset['Money'] + amount <= 3 * self.consume:
            money_amount = amount
        elif current_asset['Money'] <= 3 * self.consume:
            money_amount = math.ceil((3 * self.consume - current_asset['Money']) / 1000) * 1000
        else:
            money_amount = 0
        return_chg = temp.loc[temp['time'] == date, ['time', 'Equity', 'Bond', 'Money']]
        value_chg = return_chg[['Equity', 'Bond', 'Money']] + 1
        for x in ['Equity', 'Bond', 'Money']:
            current_asset[x] = current_asset[x] * value_chg[x].values
        current_asset['Asset'] = current_asset[['Equity', 'Bond', 'Money']].sum() + amount
        current_asset['Money'] += money_amount
        weight = self.initial_weight
        equity_w = weight[0] / (1 - weight[2])
        current_asset['Equity'] += round((amount - money_amount) * equity_w / 1000) * 1000
        current_asset['Bond'] += amount - money_amount - round((amount - money_amount) * equity_w / 1000) * 1000
        current_asset['time'] = date
        current_asset = pd.DataFrame([current_asset.values.T], columns=current_asset.index).set_index('time')
        self.benchmark_asset.loc[date] = current_asset.iloc[0]
        return

    def run_benchmarks(self, start=None, end=None):
        """

        Args:
            start:
            end: 持有期末+1天（因为要更新最后一天的收益）

        Returns:

        """
        if start is None:
            start = self.startdate
        else:
            start = min([x for x in trade_days if x >= start])
        if end is None:
            end = datetime.now().strftime('%Y%m%d')
        if start == end:
            return
        if self.auto_freq is not None:
            auto_invest_days = temp.loc[(temp['time'] < end) &
                                        (temp['time'] > start) & (temp[self.auto_freq] == 1), 'time'].tolist()  # 定投日
            auto_invest_days.append(start)
            if len(auto_invest_days) > 2:
                weight = self.initial_weight
                equity_w = weight[0] / (1 - weight[2])
                bond_w = weight[1] / (1 - weight[2])
                for i in range(len(auto_invest_days) - 1):
                    last_asset = self.benchmark_asset.loc[auto_invest_days[i - 1]].copy()
                    return_chg = temp.loc[(temp['time'] <= auto_invest_days[i]) &
                                          (temp['time'] > auto_invest_days[i - 1]), ['time', 'Equity', 'Bond', 'Money']]
                    value_chg = (return_chg[['Equity', 'Bond', 'Money']] + 1).cumprod()
                    new_asset = pd.DataFrame(columns=['Equity', 'Bond', 'Money'], index=return_chg['time'].tolist())
                    for x in ['Equity', 'Bond', 'Money']:
                        new_asset[x] = last_asset[x] * value_chg[x].values  # round(value, 2) 保留两位小数
                    new_asset.loc[auto_invest_days[i], 'Equity'] += round(self.auto_invest * equity_w / 1000) * 1000
                    new_asset.loc[auto_invest_days[i], 'Bond'] += round(self.auto_invest * bond_w / 1000) * 1000
                    assets = new_asset['Equity'] + new_asset['Bond'] + new_asset['Money']
                    new_asset.insert(0, 'Asset', assets)
                    self.benchmark_asset = pd.concat([self.benchmark_asset, new_asset])

                # 最后一次定投之后的收益变化
                last_asset = self.benchmark_asset.loc[auto_invest_days[-2]].copy()
                return_chg = temp.loc[(temp['time'] < end) &
                                      (temp['time'] > auto_invest_days[-2]), ['time', 'Equity', 'Bond', 'Money']]
                value_chg = (return_chg[['Equity', 'Bond', 'Money']] + 1).cumprod()
                new_asset = pd.DataFrame(columns=['Equity', 'Bond', 'Money'], index=return_chg['time'].tolist())
                for x in ['Equity', 'Bond', 'Money']:
                    new_asset[x] = last_asset[x] * value_chg[x].values  # round(value, 2) 保留两位小数
                assets = new_asset['Equity'] + new_asset['Bond'] + new_asset['Money']
                new_asset.insert(0, 'Asset', assets)
                self.benchmark_asset = pd.concat([self.benchmark_asset, new_asset])
            else:
                last_asset = self.benchmark_asset.loc[start].copy()
                return_chg = temp.loc[(temp['time'] < end) &
                                      (temp['time'] > start), ['time', 'Equity', 'Bond', 'Money']]
                value_chg = (return_chg[['Equity', 'Bond', 'Money']] + 1).cumprod()
                new_asset = pd.DataFrame(columns=['Equity', 'Bond', 'Money'], index=return_chg['time'].tolist())
                for x in ['Equity', 'Bond', 'Money']:
                    new_asset[x] = last_asset[x] * value_chg[x].values  # round(value, 2) 保留两位小数
                assets = new_asset['Equity'] + new_asset['Bond'] + new_asset['Money']
                new_asset.insert(0, 'Asset', assets)
                self.benchmark_asset = pd.concat([self.benchmark_asset, new_asset])
        else:
            last_asset = self.benchmark_asset.loc[start].copy()
            return_chg = temp.loc[(temp['time'] < end) &
                                  (temp['time'] > start), ['time', 'Equity', 'Bond', 'Money']]
            value_chg = (return_chg[['Equity', 'Bond', 'Money']] + 1).cumprod()
            new_asset = pd.DataFrame(columns=['Equity', 'Bond', 'Money'], index=return_chg['time'].tolist())
            for x in ['Equity', 'Bond', 'Money']:
                new_asset[x] = last_asset[x] * value_chg[x].values  # round(value, 2) 保留两位小数
            assets = new_asset['Equity'] + new_asset['Bond'] + new_asset['Money']
            new_asset.insert(0, 'Asset', assets)
            self.benchmark_asset = pd.concat([self.benchmark_asset, new_asset])
        return


if __name__ == '__main__':
    account = Account('20210706', 8, 6, 50000, 2000, 'biweekly', 3000)
    account.run_benchmarks('20210706', '20230709')
    account.auto_run('20210706', '20230709')
    timeline = account.asset.index.tolist()
    timeline = [datetime.strptime(x, '%Y%m%d') for x in timeline]
    invest_amount = pd.DataFrame(account.records.cumsum(),
                                 index=account.asset.index.tolist()).fillna(method='pad')
    plt.clf()
    plt.rcParams['font.sans-serif'] = ['SimHei']  # 显示汉字
    plt.xlabel('时间')  # x轴标题
    plt.ylabel('组合总资产')  # y轴标题
    plt.plot(timeline, account.asset['Asset'] / invest_amount['Asset'].values.flatten(), label='组合')
    plt.plot(timeline, account.benchmark_asset['Asset'] / invest_amount['Asset'].values.flatten(), label='基准')
    plt.legend()
    plt.savefig('组合收益.png', dpi=300)
    # account.add_money('20210709', 20000)
    # account.add_benchmark('20210709', 20000)
    # para_lst = [[5, 5], [8, 6], [9, 10], [12, 12], [15, 16]]
    # for i in range(5):
    #     account = Account('20170102', para_lst[i][0], para_lst[i][1], 50000, 2000, 'monthly', 2000)
    #     account.run_benchmarks('20170102', '20230731')
    #     account.auto_run('20170102', '20230731')
    #     # account.add_money('20210803', 20000)
    #     # account.add_benchmark('20210803', 20000)
    #     # account.run_benchmarks('20210803', '20230731')
    #     # account.auto_run('20210803', '20230731')
    #     timeline = account.asset.index.tolist()
    #     timeline = [datetime.strptime(x, '%Y%m%d') for x in timeline]
    #     invest_amount = pd.DataFrame(account.records.cumsum(),
    #                                  index=account.asset.index.tolist()).fillna(method='pad')
    #     plt.clf()
    #     plt.rcParams['font.sans-serif'] = ['SimHei']  # 显示汉字
    #     plt.xlabel('时间')  # x轴标题
    #     plt.ylabel('组合总资产')  # y轴标题
    #     plt.plot(timeline, account.asset['Asset'] / invest_amount['Asset'].values.flatten(), label='组合')
    #     plt.plot(timeline, account.benchmark_asset['Asset'] / invest_amount['Asset'].values.flatten(), label='基准')
    #     plt.legend()
    #     plt.savefig('./output1/组合收益' + str(i) + '.png', dpi=300)
    #     portf = account.asset.copy()
    #     portf = pd.concat([portf, invest_amount], axis=1)
    #     portf.to_excel('./output1/定投资产'+str(i)+'.xlsx')
    #     benchmark = account.benchmark_asset.copy()
    #     benchmark = pd.concat([benchmark, invest_amount], axis=1)
    #     benchmark.to_excel('./output1/基准资产'+str(i)+'.xlsx')
    print(account.records)
