#!/user/bin/env python3
# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import *
from tkinter.ttk import *
from tkinter import messagebox, scrolledtext
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkinter import ttk
from tkcalendar import Calendar
from datetime import datetime, date
from account import Account, temp, find_closest, get_initial_weight, update_signal
import pandas as pd
import matplotlib.pyplot as plt
from ttkbootstrap import Style

plt.rcParams['font.sans-serif'] = ['SimHei']
# 假设的 Excel 数据结构:
# 预期收益 | 最大回撤 | 权益类 | 债券类 | 货币类
df = pd.read_excel(r"./data/权重对照表.xlsx", sheet_name=0)
trade_days = temp['time'].tolist()


def plot_2pie(data1, data2, title1, title2):
    fig, ax = plt.subplots(1, 2, figsize=(6, 4))
    show_pie_chart(ax[0], data1, title1)
    show_pie_chart(ax[1], data2, title2)
    return fig


def show_pie_chart(ax, data, title):

    # 设定一组吸引人的颜色
    colors = ['#ff9999', '#66b2ff', '#99ff99', '#ffcc99', '#c2c2f0', '#ffb3e6', '#c2c2f0', '#ffb366']

    # 根据数据长度决定颜色
    plot_colors = colors[:len(data)]

    # 设定突出效果，这里只突出最大的部分
    explode = [0.1 if value == max(data) else 0 for value in data]

    # 绘制饼图
    wedges, texts, autotexts = ax.pie(data,
                                      labels=data.index,
                                      colors=plot_colors,
                                      autopct='%1.1f%%',
                                      shadow=True,
                                      startangle=140,
                                      explode=explode,
                                      wedgeprops=dict(width=0.3))
    # 使其为圆形
    ax.axis('equal')

    # 设定标题
    ax.set_title(title, fontsize=16, weight='bold')
    # 美化标签和百分比的字体
    plt.setp(texts, size=14)
    plt.setp(autotexts, size=16, color="k", weight="bold")

    return ax


# 假设的学生党的风险偏好：(12, 15); 假设的天选打工人的风险偏好：(9, 12); 假设的新手爸妈的风险偏好：(6, 6)
identity_dict = {"学生党": (2000, 12, 15), "天选打工人": (3000, 9, 12), "新手爸妈": (4000, 6, 6)}
ids = ["学生党", "天选打工人", "新手爸妈"]


class AssetCalc:
    def __init__(self, master):
        self.root = master
        self.root.config()
        self.root.title("你的全程陪伴式【三笔钱】配置指南")
        Page1(self.root)  # 第一页，填身份和风险偏好

        # 窗体设置
        self.center_window(800, 800)
        self.root.resizable(False, False)

    # 窗体居中
    def center_window(self, width, height):
        screenwidth = self.root.winfo_screenwidth()
        screenheight = self.root.winfo_screenheight()
        # 宽高及宽高的初始点坐标
        size = '%dx%d+%d+%d' % (width, height, (screenwidth - width) / 2, (screenheight - height) / 2)
        self.root.geometry(size)


class Page1:
    def __init__(self, master):
        self.master = master
        self.master.geometry('800x1000')
        self.frame_top = tk.Frame(width=600, height=100)
        self.frame_center = tk.Frame(width=600, height=600)
        self.frame_bottom = tk.Frame(width=600, height=100)
        self.frame_top.pack()
        self.frame_center.pack()
        self.frame_bottom.pack()

        # 定义上部分区域
        tip = tk.Label(self.frame_top,
                       text="为了给你量身定制【三笔钱】规划方案，\n需要你花 30 秒时间，确认和完善一些信息。", font=("微软雅黑", 20, "bold"))
        tip.grid(row=0, column=0, pady=(20, 5))

        # 定义中间区域
        # self.identity_var = tk.StringVar()
        self.identity_var = tk.IntVar()
        tk.Label(self.frame_center, text="你的身份是：", font=("微软雅黑", 20, "bold")).pack()
        for i in range(3):
            tk.Radiobutton(self.frame_center, text=ids[i], font=("微软雅黑", 16),
                           variable=self.identity_var, value=i,
                           command=self.identity_set).pack()
        self.identity_var.set(0)
        tk.Label(self.frame_center, text="您可直接选取预设身份，我们将按照身份对应的推荐模型参数给出配置建议。", bg='pink',
                 font=("微软雅黑", 14, "underline", "italic")).pack()
        # 平均月消费金额
        tk.Label(self.frame_center, text="你每月的平均消费支出大概有多少？", font=("微软雅黑", 20, "bold")).pack(pady=(10, 0))
        tk.Label(self.frame_center, text="（不包括非经常性大额支出）", font=("微软雅黑", 14)).pack()
        self.consume = tk.Scale(self.frame_center, from_=1000, to=6000, font=("微软雅黑", 12),
                                resolution=50, orient=tk.HORIZONTAL, label="元", fg='white', showvalue=True,
                                activebackground='pink')
        self.consume.pack()
        
        # 输入预期收益
        tk.Label(self.frame_center, text="你的预期收益是多少？", font=("微软雅黑", 20, "bold")).pack(pady=(10 ,0))
        self.exp_return_slider = tk.Scale(self.frame_center, from_=3, to=25, font=("微软雅黑", 12),
                                          resolution=0.5, orient=tk.HORIZONTAL, label="%", fg='white', showvalue=True,
                                          activebackground='pink')
        self.exp_return_slider.pack()

        # 输入最大回撤
        def get_max_drawdown_range(exp_return):
            # 获取滑块的范围
            filtered_df = df[df['预期收益'] == exp_return / 100]
            min_val = filtered_df['最大回撤'].min() * 100
            max_val = filtered_df['最大回撤'].max() * 100
            return min_val, max_val

        def update_max_drawdown_range(val):
            min_val, max_val = get_max_drawdown_range(float(val))
            self.max_drawdown_slider.config(from_=min_val, to=max_val)
            self.flag = 1

        min_drawdown, max_drawdown = get_max_drawdown_range(self.exp_return_slider.get())
        tk.Label(self.frame_center, text="你能接受的最大回撤是多少？", font=("微软雅黑", 20, "bold")).pack(pady=(10, 0))
        self.max_drawdown_slider = tk.Scale(self.frame_center, from_=min_drawdown, to=max_drawdown, resolution=1,
                                            orient=tk.HORIZONTAL, label="%", fg='white', activebackground='pink',
                                            showvalue=True, font=("微软雅黑", 12))
        self.max_drawdown_slider.pack()
        self.exp_return_slider.config(command=update_max_drawdown_range)

        # 添加next按钮
        btn_next = tk.Button(self.frame_bottom, text="下一步", font=("微软雅黑", 14), command=self.next_page)
        btn_next.pack(pady=10)

    # 根据身份预设参数
    def identity_set(self):
        # self.flag = 0
        set_consume, set_return, set_drawdown = identity_dict[ids[self.identity_var.get()]]
        self.consume.set(set_consume)
        self.exp_return_slider.set(set_return)
        # if self.flag == 1:
        #     self.max_drawdown_slider.set(set_drawdown)  # TODO 根据身份的默认最大回撤无法设置，原因是最大回撤会根据收益率更改范围，两个函数打架？

    # 单击下一步按钮触发的事件方法
    def next_page(self):
        exp_return = self.exp_return_slider.get()
        max_drawdown = self.max_drawdown_slider.get()
        consume = self.consume.get()
        self.frame_top.destroy()
        self.frame_center.destroy()
        self.frame_bottom.destroy()
        # self.consume.destroy()
        # self.exp_return_slider.destroy()
        # self.max_drawdown_slider.destroy()
        Page2(self.master, exp_return, max_drawdown, consume)


class Page2:  # 第二页，给出初始配置建议
    def __init__(self, master, exp_return, max_drawdown, consume):
        self.master = master
        self.exp_return = exp_return
        self.max_drawdown = max_drawdown
        self.consume = consume

        self.frame_top = ttk.Frame(width=600, height=80)
        self.frame_center = ttk.Frame(width=600, height=400)
        self.frame_bottom = ttk.Frame(width=600, height=200)
        self.frame_top.pack()
        self.frame_center.pack()
        self.frame_bottom.pack()

        self.start_calendar()
        self.startdate = None
        set_date = tk.Button(self.frame_top, text="设置日期", font=("微软雅黑", 14), command=self.start_calendar)
        set_date.place(x=10, y=10)
        self.start_time_text = tk.Entry(self.frame_top, width=20, font=("微软雅黑", 14))
        self.start_time_text.place(x=100, y=15)

    def start_calendar(self):
        # 清空Frame
        for widget in self.frame_top.winfo_children():
            widget.pack_forget()
        for widget in self.frame_center.winfo_children():
            widget.pack_forget()
        for widget in self.frame_bottom.winfo_children():
            widget.pack_forget()

        def print_sel():
            self.start_time_text.configure(state="normal")
            s_data = str(cal.selection_get())
            self.start_time_text.delete(0, len(self.start_time_text.get()))
            self.start_time_text.insert("0", s_data)
            self.start_time_text.configure(state="disabled")
            top.destroy()
            self.startdate = self.start_time_text.get().replace('-', '')
            self.set_widget()

        top = tk.Toplevel()
        top.geometry("300x250")
        mindate = date(year=2015, month=1, day=1)
        maxdate = date(year=2023, month=7, day=31)

        cal = Calendar(top, font=("微软雅黑", 12), selectmode='day', locale='zh_CN', mindate=mindate, maxdate=maxdate,
                       background="red", foreground="white", bordercolor="red", selectbackground="red",
                       selectforeground="red", disabledselectbackground=False)
        cal.place(x=0, y=0, width=300, height=200)
        tk.Button(top, text="确定", command=print_sel, font=("微软雅黑", 12)).place(x=240, y=205)

    def set_widget(self):
        initial_weight = get_initial_weight(self.exp_return, self.max_drawdown)
        signals = update_signal(self.startdate, self.startdate)
        self.canvas = tk.Canvas()  # 创建一块显示图形的画布
        weight = find_closest(initial_weight, signals.iloc[0, :], 0.1)
        weight = pd.Series(weight, index=['权益类', '债券类', '货币类'])
        # 返回matplotlib所画图形的figure对象
        fig = plot_2pie(initial_weight, weight, '基于收益-风险的配置建议', '观点调整后的配置建议')
        self.create_form(fig)  # 将figure显示在tkinter窗体上面
        temp_date = trade_days[trade_days.index(self.startdate) - 1]
        time_text = tk.Label(self.frame_center,
                             text=f"基于{temp_date}的省心温度计："
                                  f"{round(temp[temp['time'] == temp_date]['value'].iloc[0] * 100, 2)}%",
                             font=("微软雅黑", 14))
        time_text.pack(pady=0, side='right', expand=1, fill=tk.Y, anchor='se')

        # 添加back/confirm按钮
        btn_back = tk.Button(self.frame_bottom, text='返回上一页', font=("微软雅黑", 14), command=self.back)
        btn_back.pack(ipadx=20, pady=10, padx=10, fill='x', side='left', expand=1)
        btn_next = tk.Button(self.frame_bottom, text="去配置资金", font=("微软雅黑", 14), command=self.next_page)
        btn_next.pack(ipadx=20, pady=10, padx=10, fill='x', side='right', expand=1)

    def create_form(self, figure):
        # 把绘制的图形显示到tkinter窗口上
        self.canvas = FigureCanvasTkAgg(figure, self.frame_center)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(pady=(40, 5), ipadx=50, padx=40, side=tk.TOP, fill=tk.BOTH, expand=1)
        self.canvas.draw()

    def back(self):
        self.frame_top.destroy()
        self.frame_center.destroy()
        self.frame_bottom.destroy()

        Page1(self.master)

    def next_page(self):
        self.frame_top.destroy()
        self.frame_center.destroy()
        self.frame_bottom.destroy()
        Page3(self.master, self.startdate, self.exp_return, self.max_drawdown, self.consume)


class Page3:  # 第三页，填资金和定投频率
    def __init__(self, master, start_date, exp_return, max_drawdown, consume):
        self.master = master
        self.master.geometry("800x1000")
        self.frame_center = ttk.Frame(width=600, height=400)
        self.frame_bottom = ttk.Frame(width=600, height=400)
        self.frame_center.pack()
        self.frame_bottom.pack()
        self.startdate = start_date
        self.exp_return = exp_return
        self.max_drawdown = max_drawdown
        self.consume = consume

        # 输入初始投资金额
        tk.Label(self.frame_center, text="请选择你本次计划投入的金额（元）：", font=("微软雅黑", 20, "bold")).pack(pady=10)
        self.inital_entry = ttk.Entry(self.frame_center, font=("微软雅黑", 16))
        self.inital_entry.pack(pady=10)

        def func(event):
            if self.auto_freq.get() == '暂不开启':
                self.auto_invest.config(from_=0, to=0)
            else:
                self.auto_invest.config(from_=0, to=20000)
                self.auto_invest.set(3000)

        # 定投频率
        tk.Label(self.frame_center, text="请选择你后续的定投频率：", font=("微软雅黑", 20, "bold")).pack(pady=(10, 0))
        self.auto_freq = ttk.Combobox(self.frame_center, font=("微软雅黑", 14, "bold"))
        self.auto_freq.pack(pady=10)
        self.auto_freq['value'] = ('暂不开启', '每周定投', '双周定投', '每月定投')
        self.auto_freq.current(3)
        self.auto_freq.bind("<<ComboboxSelected>>", func)

        # 定投金额
        tk.Label(self.frame_center, text="请选择你后续每次定投的金额：",  font=("微软雅黑", 20, "bold")).pack(pady=(5, 0))
        tk.Label(self.frame_center, text="（建议不小于1000元）", font=("微软雅黑", 12)).pack()
        self.auto_invest = tk.Scale(self.frame_center, from_=0, to=20000, resolution=500,
                                    orient=tk.HORIZONTAL, label="元", fg='white', showvalue=True,
                                    activebackground='pink', font=("微软雅黑", 12))
        self.auto_invest.set(3000)
        self.auto_invest.pack()
        self.output_text = scrolledtext.ScrolledText(self.frame_bottom, width=60, height=8, font=("微软雅黑", 16))
        self.output_text.pack(pady=20, side='top', expand=1)
        # 添加back/confirm按钮
        btn_home = tk.Button(self.frame_bottom, text='重新规划', font=("微软雅黑", 14), command=self.home)
        btn_home.pack(ipadx=10, pady=10, padx=5, fill='x', side='left', expand=1)
        btn_back = tk.Button(self.frame_bottom, text='返回上一页', font=("微软雅黑", 14), command=self.back)
        btn_back.pack(ipadx=10, pady=10, padx=5, fill='x', side='left', expand=1)
        btn_confirm = tk.Button(self.frame_bottom, text="确认建仓及定投金额", font=("微软雅黑", 14), command=self.confirm)
        btn_confirm.pack(ipadx=10, pady=10, padx=5, fill='x', side='left', expand=1)
        self.account = None

    def home(self):
        self.frame_center.destroy()
        self.frame_bottom.destroy()
        Page1(self.master)

    def back(self):
        self.frame_center.destroy()
        self.frame_bottom.destroy()
        Page2(self.master, self.exp_return, self.max_drawdown, self.consume)

    def confirm(self):
        inital_entry = self.inital_entry.get()
        if inital_entry == '':
            messagebox.showinfo("错误", "请输入初始投资金额！")
        else:
            if int(inital_entry) < 3 * self.consume:
                messagebox.showinfo("警告", "初始投资金额相较月均消费过低，可能导致投资效果不及预期。")
            auto_invest = self.auto_invest.get()
            freq_dict = dict(zip(['暂不开启', '每周定投', '双周定投', '每月定投'],
                                 [None, 'weekly', 'biweekly', 'monthly']))
            auto_freq = freq_dict[self.auto_freq.get()]
            self.account = Account(self.startdate, self.exp_return,
                                   self.max_drawdown, int(inital_entry), auto_invest, auto_freq, self.consume)
            # 创建一个用于显示结果的文本框

            self.output_text.insert(tk.END, f"初始配置于{self.account.startdate}建仓完成，配置金额如下："
                                    f"\n总资产：{self.account.asset['Asset'].values[0]}"
                                    f"\n权益类：{self.account.asset['Equity'].values[0]}"
                                    f"\n债券类：{self.account.asset['Bond'].values[0]}"
                                    f"\n货币类：{self.account.asset['Money'].values[0]}\n")
            btn_next = tk.Button(self.frame_bottom, text="追踪组合收益及最新配置情况",
                                 font=("微软雅黑", 14), command=self.next_page)
            btn_next.pack(ipadx=10, pady=10, padx=5, fill='x', side='bottom', expand=1)

    def next_page(self):
        self.frame_center.destroy()
        self.frame_bottom.destroy()
        Page4(self.master, self.account)


class Page4:  # 第四页，更新组合收益情况并给出最新配置建议
    def __init__(self, master, account):

        self.master = master
        self.account = account
        self.show_date = None

        def start_calendar():

            def print_sel():
                self.start_time_text.configure(state="normal")
                s_data = str(cal.selection_get())
                self.start_time_text.delete(0, len(self.start_time_text.get()))
                self.start_time_text.insert("0", s_data)
                self.start_time_text.configure(state="disabled")
                top.destroy()
                startdate = self.start_time_text.get().replace('-', '')
                if startdate <= self.account.startdate:
                    messagebox.showinfo("错误", "输入日期应大于建仓日期！")
                else:
                    self.show_date = startdate
                    self.showpage()

            top = tk.Toplevel()
            top.geometry("300x250")
            mindate = date(year=2015, month=1, day=1)
            maxdate = date(year=2023, month=7, day=31)

            cal = Calendar(top, font=("微软雅黑", 12), selectmode='day', locale='zh_CN', mindate=mindate, maxdate=maxdate,
                           background="red", foreground="blue", bordercolor="red", selectbackground="red",
                           selectforeground="red", disabledselectbackground=False)
            cal.place(x=0, y=0, width=300, height=200)
            tk.Button(top, text="确定", command=print_sel, font=("微软雅黑", 14)).place(x=240, y=205)

        start_calendar()
        self.master.geometry('1000x800')
        self.frame_center = ttk.Frame(width=1000, height=700)
        self.frame_bottom = ttk.Frame(width=1000, height=100)
        self.frame_center.pack()
        self.frame_bottom.pack()

        start_date = tk.Button(self.frame_center, text="设置日期", font=("微软雅黑", 14), command=start_calendar)
        start_date.place(x=10, y=10)
        self.start_time_text = tk.Entry(self.frame_center, width=20, font=("微软雅黑", 14))
        self.start_time_text.place(x=100, y=15)

        # 创建总资产金额标签
        self.total_value_label = ttk.Label(self.frame_center, text="当日资产总金额：", font=("微软雅黑", 20, 'bold'))
        self.total_value_label.pack(side="top", pady=(60, 5))
        # 创建资产权重饼状图画布
        self.figure = plt.Figure(figsize=(4, 3), dpi=100)
        self.subplot = self.figure.add_subplot(111)
        self.pie_chart_canvas = FigureCanvasTkAgg(self.figure, master=self.frame_center)
        self.pie_chart_canvas.get_tk_widget().pack(side="left", anchor='nw', pady=10, padx=10)

        # 创建资产金额标签
        assets = ['权益类', '债券类', '货币类']
        self.asset_values = []
        for i in range(3):
            asset_label = ttk.Label(self.frame_center, text=assets[i], font=("微软雅黑", 16))
            asset_label.pack(side="top", pady=5, anchor='center')
            self.asset_values.append(asset_label)

        # 创建资产组合净值曲线图画布
        self.figure2 = plt.Figure(figsize=(6, 4), dpi=100)
        self.subplot2 = self.figure2.add_subplot(111)
        self.net_value_canvas = FigureCanvasTkAgg(self.figure2, master=self.frame_center)
        self.net_value_canvas.get_tk_widget().pack(side="bottom", fill=tk.X, pady=10, padx=10)
        self.temp_text = tk.Entry(self.frame_center, font=("微软雅黑", 14), width=40)
        self.temp_text.pack(pady=0, side='right', expand=1, fill=tk.Y, anchor='se')
        # 添加back/confirm按钮
        btn_home = tk.Button(self.frame_bottom, text='重新规划', font=("微软雅黑", 14), command=self.home)
        btn_home.pack(ipadx=20, pady=10, padx=10, fill='x', side='left', expand=1)
        btn_back = tk.Button(self.frame_bottom, text='返回上一页', font=("微软雅黑", 14), command=self.back)
        btn_back.pack(ipadx=20, pady=10, padx=10, fill='x', side='left', expand=1)
        btn_add = tk.Button(self.frame_bottom, text="智能加仓", font=("微软雅黑", 14), command=self.add)
        btn_add.pack(ipadx=20, pady=10, padx=10, fill='x', side='right', expand=1)
        btn_redeem = tk.Button(self.frame_bottom, text="智能赎回", font=("微软雅黑", 14), command=self.redeem)
        btn_redeem.pack(ipadx=20, pady=10, padx=10, fill='x', side='right', expand=1)

    def home(self):
        self.frame_center.destroy()
        self.frame_bottom.destroy()
        self.master.geometry("800x1000")
        self.account = None
        Page1(self.master)

    def back(self):
        self.frame_center.destroy()
        self.frame_bottom.destroy()
        Page3(self.master, self.account.startdate,
              self.account.exp_return, self.account.max_drawdown, self.account.consume)
        self.account = None

    def showpage(self):
        run_date = min([x for x in trade_days if x > self.show_date])
        lastend = str(self.account.asset.index[-1])
        if self.show_date > lastend:
            self.account.run_benchmarks(start=self.account.benchmark_asset.index[-1], end=run_date)
            self.account.auto_run(start=lastend, end=run_date)
        invest_amount = pd.DataFrame(self.account.records.cumsum(),
                                     index=self.account.asset.index.tolist()).fillna(method='pad')
        timeline = self.account.asset.index.tolist()
        timeline = [x for x in timeline if x <= self.show_date]
        invest_amount = invest_amount.loc[timeline]
        portf = self.account.asset.loc[[self.show_date]]
        assets = ['权益类', '债券类', '货币类']
        # 更新总资产金额标签
        self.total_value_label.configure(text="当日资产总金额：{:.2f} 元".format(portf['Asset'].values[0]))
        # 更新资产权重饼状图
        weight = portf[['Equity', 'Bond', 'Money']] / portf['Asset'].values[0]
        self.subplot.clear()
        self.subplot.pie(weight.values.flatten(), labels=assets, autopct='%1.1f%%',
                         startangle=90, textprops={'fontsize': 12})
        self.subplot.axis('equal')
        self.figure.canvas.draw()
        # 更新各资产金额标签
        # 各资产持有收益
        chgs = [portf['Equity'] / invest_amount.loc[[self.show_date]]['Equity'].values[0] - 1,
                portf['Bond'] / invest_amount.loc[[self.show_date]]['Bond'].values[0] - 1,
                portf['Money'] / invest_amount.loc[[self.show_date]]['Money'].values[0] - 1]
        self.chgs = dict(zip(['权益类', '债券类', '货币类'], [x.values[0] for x in chgs]))
        for i in range(3):
            self.asset_values[i].configure(text=assets[i]+": {:.2f} 元，".format(portf.iloc[:, i+1].values[0]) +
                                           "累计收益率: {:.2f}%".format(chgs[i].values[0] * 100))

        # 更新资产组合净值曲线图
        self.subplot2.clear()
        self.subplot2.plot([datetime.strptime(x, '%Y%m%d') for x in timeline],
                           self.account.asset.loc[timeline, 'Asset'] / invest_amount['Asset'].values.flatten(),
                           label='组合')
        self.subplot2.plot([datetime.strptime(x, '%Y%m%d') for x in timeline],
                           self.account.benchmark_asset.loc[timeline, 'Asset'] / invest_amount['Asset'].values.flatten(),
                           label='基准')
        self.subplot2.legend()
        self.subplot2.set_xlabel("时间")
        self.subplot2.set_ylabel("组合单位净值")
        self.subplot2.set_title(f"截至{self.show_date}的组合vs基准业绩表现")
        self.net_value_canvas.draw()
        self.temp_text.configure(state="normal")
        self.temp_text.delete(0, tk.END)
        self.temp_text.insert(tk.END, f"{self.show_date}的省心温度计："
                                      f"{round(temp[temp['time'] == self.show_date]['value'].iloc[0] * 100, 2)}%" )
        self.temp_text.configure(state="disabled")

    def add(self):  # TODO
        add_top = tk.Toplevel()
        add_top.geometry("600x800")
        add_top.title('智能加仓')
        # add_frame = ttk.Frame(add_top, width=600, height=400)
        add_date = min([x for x in trade_days if x > self.show_date])

        def execute_add():
            self.account.add_money(add_date, int(add_amount.get()))
            self.account.add_benchmark(add_date, int(add_amount.get()))
            # self.account.auto_run(self.show_date, add_date)

            add_text.delete(1.0, tk.END)  # 清空前一个结果
            add_result = self.account.records.iloc[-1][['Equity', 'Bond', 'Money']]
            add_result.index = ['权益类', '债券类', '货币类']
            add_text.insert(tk.END, f"您加仓的{int(add_amount.get())}元建议如下分配：\n")
            for k, v in add_result.items():
                add_text.insert(tk.END, f"{k}: {v:.2f}\n")
            self.show_date = add_date
            self.showpage()

        # 输入加仓金额
        tk.Label(add_top, text="请输入你本次计划加仓的金额（元）：", font=("微软雅黑", 20, "bold")).pack(pady=10)
        add_amount = ttk.Entry(add_top, font=("微软雅黑", 16))
        add_amount.pack(pady=20)
        # 创建确认按钮
        submit_button = tk.Button(add_top, text="确认", font=("微软雅黑", 14), command=execute_add)
        submit_button.pack(pady=10)

        add_text = scrolledtext.ScrolledText(add_top, width=60, height=8, font=("微软雅黑", 14))
        add_text.pack(pady=20, side='bottom', expand=1)
        add_text.insert(tk.END, "加仓配置建议会在这里显示...")

    def redeem(self):  # TODO
        # 示例的初始资产配置
        portfolio = self.account.asset.iloc[-1][['Equity', 'Bond', 'Money']]
        portfolio.index = ['权益类', '债券类', '货币类']
        portfolio = dict(portfolio)
        # {"权益类": 86464.14, "债券类": 97006.92, "货币类": 15506.52}
        yields = self.chgs
        # yields = {"权益类": 0.3061, "债券类": 0.0613, "货币类": 0.0407}  # 假设这是收益率
        optimal_allocation = {"权益类": 0.35276953, "债券类": 0.56120211}  # 当期最优的资产配置比例

        # 按照股债比
        def redeem_funds(portfolio, redemption_amount, optimal_allocation):
            # 先从货币类赎回
            if portfolio['货币类'] >= redemption_amount:
                portfolio['货币类'] -= redemption_amount
                return portfolio

            redemption_amount -= portfolio['货币类']
            portfolio['货币类'] = 0

            # 计算权益类和债券类在没有赎回前的总额
            total_AB = portfolio['权益类'] + portfolio['债券类']
            new_total_AB = total_AB - redemption_amount

            # 根据最优比例计算权益类和债券类赎回后应有的金额
            desired_values = {asset: new_total_AB * ratio for asset, ratio in optimal_allocation.items()}

            # 计算赎回金额
            redeem_values = {
                "权益类": portfolio['权益类'] - desired_values['权益类'],
                "债券类": portfolio['债券类'] - desired_values['债券类']
            }

            # 更新资产配置
            portfolio['权益类'] -= redeem_values['权益类']
            portfolio['债券类'] -= redeem_values['债券类']

            return portfolio

        ###按照交易费用
        def redeem_funds_cba_order(portfolio, redemption_amount):
            # 先从货币类赎回
            if portfolio['货币类'] >= redemption_amount:
                portfolio['货币类'] -= redemption_amount
                return portfolio

            redemption_amount -= portfolio['货币类']
            portfolio['货币类'] = 0

            # 如果货币类不足以满足赎回金额，从债券类赎回
            if portfolio['债券类'] >= redemption_amount:
                portfolio['债券类'] -= redemption_amount
                return portfolio

            redemption_amount -= portfolio['债券类']
            portfolio['债券类'] = 0

            # 最后从权益类赎回
            portfolio['权益类'] -= redemption_amount
            return portfolio

        # 按照收益率
        def redeem_funds_by_order_and_yield(portfolio, redemption_amount, yields):
            # 首先尝试赎回货币类
            if portfolio["货币类"] >= redemption_amount:
                portfolio["货币类"] -= redemption_amount
                return portfolio

            redemption_amount -= portfolio["货币类"]
            portfolio["货币类"] = 0

            # 如果货币类不足，则选择权益类和债券类中收益率较高的进行赎回
            higher_yield_asset = "权益类" if yields["权益类"] > yields["债券类"] else "债券类"

            if portfolio[higher_yield_asset] >= redemption_amount:
                portfolio[higher_yield_asset] -= redemption_amount
                return portfolio

            # 如果较高收益率的资产还是不足，那么将其全部赎回，然后赎回另一资产
            redemption_amount -= portfolio[higher_yield_asset]
            portfolio[higher_yield_asset] = 0

            other_asset = "债券类" if higher_yield_asset == "权益类" else "权益类"

            if portfolio[other_asset] >= redemption_amount:
                portfolio[other_asset] -= redemption_amount
                return portfolio

            # 如果全部资产还是不足，返回错误提示
            print("Error: Redemption amount exceeds total assets.")
            return portfolio

        def execute_redemption():
            try:
                amount = float(redemption_amount_entry.get())
                if amount > sum(portfolio.values()):
                    messagebox.showerror("错误", "赎回金额不能超过持仓金额")
                    return
                method = redemption_method_var.get()
                if method == 1:
                    result = redeem_funds(portfolio.copy(), amount, optimal_allocation)
                elif method == 2:
                    result = redeem_funds_cba_order(portfolio.copy(), amount)
                elif method == 3:
                    result = redeem_funds_by_order_and_yield(portfolio.copy(), amount, yields)
                else:
                    messagebox.showerror("错误", "请选择赎回方式")
                    return
                # 准备美化后的输出
                output_text.delete(1.0, tk.END)  # 清空前一个结果
                output_text.insert(tk.END, "目前持有的资产情况：\n")
                for k, v in portfolio.items():
                    output_text.insert(tk.END, f"{k}: {v:.2f}\n")
                output_text.insert(tk.END, "\n赎回后的资产情况：\n")
                for k, v in result.items():
                    output_text.insert(tk.END, f"{k}: {v:.2f}\n")

            except ValueError:
                messagebox.showerror("错误", "请输入有效的赎回金额")

        window = tk.Toplevel()
        window.title("资产赎回工具")
        window.geometry("600x600")

        # 创建输入金额的部分
        redemption_amount_label = tk.Label(window, text="赎回金额:", font=("微软雅黑", 14, 'bold'))
        redemption_amount_label.pack(pady=10)

        redemption_amount_entry = tk.Entry(window, font=("微软雅黑", 14))
        redemption_amount_entry.pack(pady=10)

        # 创建选择赎回方式的部分
        redemption_method_var = tk.IntVar()
        redemption_method_label = tk.Label(window, text="选择赎回方式:", font=("微软雅黑", 14, 'bold'))
        redemption_method_label.pack(pady=10)

        rb1 = tk.Radiobutton(window, text="【建议配比】优先", font=("微软雅黑", 12), variable=redemption_method_var,
                             value=1)
        rb1.pack()
        rb2 = tk.Radiobutton(window, text="【交易费用】优先", font=("微软雅黑", 12), variable=redemption_method_var,
                             value=2)
        rb2.pack()
        rb3 = tk.Radiobutton(window, text="【止盈】优先", font=("微软雅黑", 12), variable=redemption_method_var,
                             value=3)
        rb3.pack()

        # 创建提交按钮
        submit_button = tk.Button(window, text="确认", font=("微软雅黑", 14), command=execute_redemption)
        submit_button.pack(pady=10)

        # 创建一个用于显示结果的文本框
        output_text = scrolledtext.ScrolledText(window, width=50, height=12, font=("微软雅黑", 14))
        output_text.pack(pady=10)
        output_text.insert(tk.END, "结果会在这里显示...")


if __name__ == '__main__':
    root = tk.Tk()
    style = Style(theme='journal')
    AssetCalc(root)
    root.mainloop()
