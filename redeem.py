import tkinter as tk
from tkinter import messagebox, scrolledtext
from ttkbootstrap import Style


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


# # 示例
# portfolio = {"权益类": 6000, "债券类": 4000, "货币类": 950}
# redemption_amount = 3000  # 假设赎回3000元
# optimal_allocation = {"权益类": 0.6, "债券类": 0.4}  # 当期最优的资产配置比例
#
# updated_portfolio = redeem_funds(portfolio, redemption_amount, optimal_allocation)
# print(updated_portfolio)


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


# # 示例
# portfolio = {"权益类": 6000, "债券类": 4000, "货币类": 950}
# redemption_amount = 5000  # 假设赎回5000元
#
# updated_portfolio = redeem_funds_cba_order(portfolio, redemption_amount)
# print(updated_portfolio)


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


# # 示例
# portfolio = {"权益类": 6000, "债券类": 4000, "货币类": 950}
# yields = {"权益类": 0.05, "债券类": 0.03, "货币类": 0.04}  # 假设这是收益率
# redemption_amount = 3000  # 假设赎回
# updated_portfolio = redeem_funds_by_order_and_yield(portfolio, redemption_amount, yields)
# print(updated_portfolio)


# 你的赎回逻辑
# ... [放置前面的赎回函数] ...

# 示例的初始资产配置
portfolio = {"权益类": 86464.14, "债券类": 97006.92, "货币类": 15506.52}
yields = {"权益类": 0.3061, "债券类": 0.0613, "货币类": 0.0407}  # 假设这是收益率
optimal_allocation = {"权益类": 0.35276953,  "债券类": 0.56120211}  # 当期最优的资产配置比例


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


if __name__ == '__main__':
    # 创建基本窗口
    window = tk.Tk()
    style = Style(theme='journal')
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

    window.mainloop()
