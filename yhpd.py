'''
这个是基于资金，关注的
選股條件:
1.今日成交量是10 日均量的3-5倍
2.换手率在15%-20%之间
3.涨幅在7%以上
4.成交量问题，是89天内最大成交量

你如果写回测的话，买点是5MA+1%,并且大于大阳线底部
加上突破日线布林和周线布林，并且日线布林的价格大于周线布林的价格。就是上轨

跌破放量阳线就踢出股票池。
入股票池10天后出，除非条件再次达成
10天换仓，不恋战
最长持仓时间10个自然日
跌破那个放量的线(跌破选股那天的前一天收盘价）就止损，还有5%止损
'''

import talib
import numpy as np
import pandas as pd
import tradestat
'''
================================================================================
总体回测前
================================================================================
'''
# 初始化函数，设定要操作的股票、基准等等
#总体回测前要做的事情
def initialize(context):
    set_params()                             # 设置策略常量
    set_variables()                          # 设置中间变量
    set_backtest()                           # 设置回测条件
    # 加载统计模块
    if g.flag_stat:
        g.trade_stat = tradestat.trade_stat()

#1 
#设置策略参数
def set_params():
    g.stocks=['601398.XSHG', '601939.XSHG']  # 设置银行股票 工行，建行
    g.flag_stat = False                      # 默认不开启统计
    g.a = 1
    g.b = 1
    g.c = 1
    g.d = 1
    g.fzbz = 1                               # 阀值标准
    

#2
#设置中间变量
def set_variables():
    return None
#3
#设置回测条件
def set_backtest():
    set_option('use_real_price',True)        # 用真实价格交易
    log.set_level('order','debug')           # 设置报错等级

    
'''
================================================================================
每天开盘前
================================================================================
'''
#每天开盘前要做的事情
def before_trading_start(context):
    set_slip_fee(context)                 # 设置手续费与手续费
    # 设置可行股票池
    g.feasible_stocks = set_feasible_stocks(g.stocks,context)# 得到所有股票昨日收盘价, 每天只需要取一次, 所以放在 before_trading_start 中
    g.last_df = history(1,'1d','close', security_list=g.stocks)
    
    g.fz = 0                              # 每天重置
    

    
# 过滤停牌股票
def filter_paused_stock(stock_list):
    current_data = get_current_data()
    return [stock for stock in stock_list if not current_data[stock].paused]

# 停牌返回True，    
def is_paused(stock):
    current_data = get_current_data()
    return current_data[stock].paused
    
# 过滤ST及其他具有退市标签的股票
def filter_st_stock(stock_list):
    current_data = get_current_data()
    return [stock for stock in stock_list 
        if not current_data[stock].is_st 
        and 'ST' not in current_data[stock].name 
        and '*' not in current_data[stock].name 
        and '退' not in current_data[stock].name]
        
#4
# 设置可行股票池：过滤掉当日停牌的股票
# 输入：initial_stocks为list类型,表示初始股票池； context（见API）
# 输出：unsuspened_stocks为list类型，表示当日未停牌的股票池，即：可行股票池
def set_feasible_stocks(initial_stocks,context):
    # 判断初始股票池的股票是否停牌，返回list
    pick_stock = filter_paused_stock(initial_stocks)
    # 去除ST
    pick_stock = filter_st_stock(pick_stock)
    return pick_stock

    
#5
# 根据不同的时间段设置滑点与手续费
# 输入：context（见API）
# 输出：none
def set_slip_fee(context):
    # 将滑点设置为0
    set_slippage(FixedSlippage(0)) 
    # 根据不同的时间段设置手续费
    set_commission(PerTrade(buy_cost=0.00025, sell_cost=0.00125, min_cost=5)) 

'''
================================================================================
开盘前选股
================================================================================
'''
    
# 计算股票池，存入g.df_pick
def stocks_to_buy(context, data):
    list_can_buy = []
    
    
        
'''
================================================================================
每分钟交易时
================================================================================
'''
# 回测时做的事情
def handle_data(context,data):
    # 工行   g.stocks[0]
    # 建行   g.stocks[1]
    '''
    工行和建行的涨幅
    工行预测涨幅=建行涨幅*a+b
    建行预测=工行*c+d
    工行实际-工行预测=误差0
    建行实际-建行预测=误差1
    误差0-误差1=阀值
    阀值变量
    阀值变量负数那就买入工行0卖出建行1（要是有持仓的话）
    正数就是买入建行卖出工行
    买入挂单和卖出挂单都是按照买一或者卖一
    '''
    # 得到当前资金余额
    cash = context.portfolio.cash
    price0 = data[g.stocks[0]].close
    price1 = data[g.stocks[0]].close
    last_close0 = g.last_df[g.stocks[0]][0]
    last_close1 = g.last_df[g.stocks[1]][0]
    zf0 = (price0-last_close0)/last_close0
    zf1 = (price1-last_close1)/last_close1
    yczf0 = zf1*g.a+g.b
    yczf1 = zf0*g.c+g.d
    wc0 = zf0 - yczf0
    wc1 = zf1 - yczf1
    g.fz_before = g.fz
    g.fz = wc0 - wc1
    if g.fz_before > 0 and g.fz < -1*g.fzbz:
        # 惊天大逆转
        orders = get_open_orders()
    elif g.fz_before < 0 and g.fz > g.fzbz:
        orders = get_open_orders()
    if g.fz < -1*g.fzbz:                          # 跟阀值标准比
        #return g.stocks[0]
        if context.portfolio.positions[g.stocks[1]].sellable_amount > 0:
            order_target(g.stocks[1], 0, LimitOrderStyle(price1+0.01))
        order_value(g.stocks[0], cash, LimitOrderStyle(price0-0.01))
        '''
        if g.fz < g.fz_before and g.fz_before < g.fzbz: #更低估 撤单追买卖
            orders = get_open_orders()
            for _order in orders.values():
                cancel_order(_order)
            if context.portfolio.positions[g.stocks[1]].sellable_amount > 0:
        '''
        
    elif g.fz > g.fzbz:
        #return g.stocks[1]
        if context.portfolio.positions[g.stocks[0]].sellable_amount > 0:
            order_target(g.stocks[0], 0)
        order_value(g.stocks[1], cash, LimitOrderStyle(price1-0.01))
    
    
    

    
#8
# 获得卖出信号
# 输入：context（见API文档）, list_to_buy为list类型，代表待买入的股票
# 输出：list_to_sell为list类型，表示待卖出的股票
def stocks_to_sell(context, data):
    list_to_sell = []
    list_hold = context.portfolio.positions.keys()
    if len(list_hold) == 0:
        return list_to_sell
    
    for i in list_hold:
        if context.portfolio.positions[i].sellable_amount == 0:
            continue
        if context.portfolio.positions[i].avg_cost *0.95 >= data[i].close:
            #亏损 5% 卖出
            list_to_sell.append(i)
            continue
        if context.portfolio.positions[i].avg_cost *1.2 <= data[i].close:
            #赚 20% 卖出
            list_to_sell.append(i)
            continue
        if g.df_hold.loc[i]['buy_days'] > g.hold_days:
            # 持股g.hold_days以上卖出
            list_to_sell.append(i)
            continue
        if g.df_hold.loc[i]['price_yang'] >= data[i].close:
            # 跌破放量阳线卖出
            list_to_sell.append(i)
            
    for i in list_to_sell:
        if i in g.df_pick.index:
            g.df_pick = g.df_pick.drop(i)
            
    return list_to_sell
    
# 获得买入的list_to_buy
# 股票池由df.pick_stock 维护
# 输出list_to_buy 为list，买入的队列
def pick_buy_list(context, data, list_to_sell):
    list_to_buy = []
    # 要买数 = 可持数 - 持仓数 + 要卖数
    buy_num = g.num_stocks - len(context.portfolio.positions.keys()) + len(list_to_sell)
    if buy_num <= 0:
        return list_to_buy
    # 得到一个dataframe：index为股票代码，data为相应的PEG值
    # 处理-------------------------------------------------
    current_data = get_current_data()
    ad_num = 0;
    for i in g.df_pick.index:
        if i not in context.portfolio.positions.keys():
            # 没有持仓这股票, 买点是5MA+1%
            if data[i].close <= count_ma(i,5)*1.01 and data[i].close > g.df_pick.loc[i]['price_yang']:
                list_to_buy.append(i)
                ad_num = ad_num + 1
        if ad_num >= buy_num:
            break
    return list_to_buy

# 自定义下单
# 根据Joinquant文档，当前报单函数都是阻塞执行，报单函数（如order_target_value）返回即表示报单完成
# 报单成功返回报单（不代表一定会成交），否则返回None
def order_target_value_(security, value):
    if value == 0:
        log.debug("Selling out %s" % (security))
    else:
        log.debug("Order %s to value %f" % (security, value))
        
    # 如果股票停牌，创建报单会失败，order_target_value 返回None
    # 如果股票涨跌停，创建报单会成功，order_target_value 返回Order，但是报单会取消
    # 部成部撤的报单，聚宽状态是已撤，此时成交量>0，可通过成交量判断是否有成交
    return order_target_value(security, value)
    
# 平仓，卖出指定持仓
# 平仓成功并全部成交，返回True
# 报单失败或者报单成功但被取消（此时成交量等于0），或者报单非全部成交，返回False
def close_position(context, position):
    security = position.security
    order = order_target_value_(security, 0) # 可能会因停牌失败
    if order != None:
        if order.filled > 0 and g.flag_stat:
            # 只要有成交，无论全部成交还是部分成交，则统计盈亏
            g.trade_stat.watch(security, order.filled, position.avg_cost, position.price)
    
    if not order is None:
        dict_stock = context.portfolio.positions[security]
        if dict_stock.total_amount == dict_stock.sellable_amount:
            g.df_hold = g.df_hold.drop(security)
    return False
    
#9
# 执行卖出操作
# 输入：list_to_sell为list类型，表示待卖出的股票
# 输出：none
'''
def sell_operation(context, list_to_sell):
'''
        
#10
# 执行买入操作
# 输入：context(见API)；list_to_buy为list类型，表示待买入的股票
# 输出：none
def buy_operation(context, list_to_buy):
    for stock_buy in list_to_buy:
        # 为每个持仓股票分配资金
        g.capital_unit=context.portfolio.portfolio_value/g.num_stocks
        # 买入在"待买股票列表"的股票
        order_now = order_target_value(stock_buy, g.capital_unit)
        if not order_now is None:
            # ['price_yang', 'buy_days']
            df_now = pd.DataFrame([[g.df_pick.loc[stock_buy]['price_yang'], 1]], \
                    index=[stock_buy], columns=['price_yang', 'buy_days'])
            # price 是买入价，并不是成本价
            g.df_hold = g.df_hold.append(df_now)
        
'''
================================================================================
每天交易后
================================================================================
'''
def after_trading_end(context):
    if g.flag_stat:
        g.trade_stat.report(context)
        