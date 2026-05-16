def calculate_local(unit_cost, unit_sell, qty, use_exchange, exchange_rate, fee_rate, buy_currency=None, sell_currency=None, my_currency=None):
    net_rate = 1.0 - fee_rate
    unit_net = unit_sell * net_rate

    # 原始金额（买入货币）
    total_cost_buy = unit_cost * qty
    
    # 如果使用汇率，转换为售出货币
    if use_exchange:
        total_cost = total_cost_buy * exchange_rate
    else:
        total_cost = total_cost_buy

    total_net = unit_net * qty
    total_steam_sell = unit_sell * qty
    ratio = (total_cost / total_net) if total_net > 0 else 0.0
    discount = (1.0 - ratio) if total_net > 0 else 0.0

    if use_exchange:
        need_sell = (unit_cost * exchange_rate / net_rate) if net_rate > 0 else 0.0
    else:
        need_sell = (unit_cost / net_rate) if net_rate > 0 else 0.0
    
    # 计算转换为我的货币的金额
    total_cost_in_my = total_cost_buy  # 成本已经是买入货币
    total_net_in_my = total_net
    total_steam_sell_in_my = total_steam_sell
    
    if use_exchange and my_currency:
        if my_currency == buy_currency:
            # 我的货币是买入货币，需要将售出货币转换为买入货币
            total_net_in_my = total_net / exchange_rate
            total_steam_sell_in_my = total_steam_sell / exchange_rate
        elif my_currency == sell_currency:
            # 我的货币是售出货币，金额已经是正确的
            pass
        else:
            # 默认情况
            total_net_in_my = total_net
            total_steam_sell_in_my = total_steam_sell

    return {
        "unit_net": unit_net,
        "total_cost": total_cost,
        "total_net": total_net,
        "total_steam_sell": total_steam_sell,
        "ratio": ratio,
        "discount": discount,
        "need_sell": need_sell,
        "total_cost_in_my_currency": total_cost_in_my,
        "total_net_in_my_currency": total_net_in_my,
        "total_steam_sell_in_my_currency": total_steam_sell_in_my,
    }