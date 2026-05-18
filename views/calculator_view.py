import flet as ft
from utils import money, pct, safe_float, safe_int
from calculator import calculate_local
from glassmorphism import create_glass_card, get_glassmorphism_style


def create_calculator_view(settings, on_add_to_history, t):
    is_dark = True
    
    tf_item = ft.TextField(
        label=t("item_name"), 
        value="CS2 刀/皮肤", 
        expand=True,
        filled=True,
        bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.SURFACE),
        border_color=ft.Colors.with_opacity(0.2, ft.Colors.WHITE),
        focused_border_color=ft.Colors.with_opacity(0.5, ft.Colors.INDIGO),
        border_radius=12,
        content_padding=12,
    )
    tf_note = ft.TextField(
        label=t("note"), 
        expand=True,
        filled=True,
        bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.SURFACE),
        border_color=ft.Colors.with_opacity(0.2, ft.Colors.WHITE),
        focused_border_color=ft.Colors.with_opacity(0.5, ft.Colors.INDIGO),
        border_radius=12,
        content_padding=12,
    )

    tf_cost = ft.TextField(
        label=t("cost"),
        value="70",
        prefix=ft.Text(settings.buy_currency_symbol),
        keyboard_type=ft.KeyboardType.NUMBER,
        expand=True,
        filled=True,
        bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.SURFACE),
        border_color=ft.Colors.with_opacity(0.2, ft.Colors.WHITE),
        focused_border_color=ft.Colors.with_opacity(0.5, ft.Colors.INDIGO),
        border_radius=12,
        content_padding=12,
    )
    tf_steam_sell = ft.TextField(
        label=t("steam_sell"),
        value="100",
        prefix=ft.Text(settings.sell_currency_symbol),
        keyboard_type=ft.KeyboardType.NUMBER,
        expand=True,
        filled=True,
        bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.SURFACE),
        border_color=ft.Colors.with_opacity(0.2, ft.Colors.WHITE),
        focused_border_color=ft.Colors.with_opacity(0.5, ft.Colors.INDIGO),
        border_radius=12,
        content_padding=12,
    )
    tf_qty = ft.TextField(
        label=t("quantity"),
        value="1",
        keyboard_type=ft.KeyboardType.NUMBER,
        width=120,
        filled=True,
        bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.SURFACE),
        border_color=ft.Colors.with_opacity(0.2, ft.Colors.WHITE),
        focused_border_color=ft.Colors.with_opacity(0.5, ft.Colors.INDIGO),
        border_radius=12,
        content_padding=12,
    )

    out_unit_net = ft.Text(value="-")
    out_total_cost = ft.Text(value="-")
    out_total_net = ft.Text(value="-")
    out_ratio = ft.Text(value="-")
    out_discount = ft.Text(value="-")
    out_need_sell = ft.Text(value="-")

    tf_target_amount = ft.TextField(
        label=t("target_amount"),
        value="",
        prefix=ft.Text(settings.sell_currency_symbol),
        keyboard_type=ft.KeyboardType.NUMBER,
        expand=True,
        hint_text=t("target_amount_desc"),
        filled=True,
        bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.SURFACE),
        border_color=ft.Colors.with_opacity(0.2, ft.Colors.WHITE),
        focused_border_color=ft.Colors.with_opacity(0.5, ft.Colors.INDIGO),
        border_radius=12,
        content_padding=12,
    )
    
    out_required_qty = ft.Text(value="-")
    out_required_cost = ft.Text(value="-")

    def format_price(amount, currency_symbol, currency_code):
        my_currency = settings.my_currency
        my_symbol = settings.my_currency_symbol
        
        if currency_code == my_currency:
            return f"{currency_symbol} {money(amount)}"
        
        exchange_rate = settings.exchange_rate
        if settings.buy_currency == my_currency:
            converted = amount / exchange_rate
        else:
            converted = amount * exchange_rate
        
        return f"{currency_symbol} {money(amount)} ({my_symbol} {money(converted)})"

    def recalc(_=None):
        unit_cost = safe_float(tf_cost.value)
        unit_sell = safe_float(tf_steam_sell.value)
        qty = safe_int(tf_qty.value)

        use_exchange = settings.buy_currency != settings.sell_currency

        data = calculate_local(
            unit_cost,
            unit_sell,
            qty,
            use_exchange,
            settings.exchange_rate,
            settings.steam_fee_rate,
            settings.buy_currency,
            settings.sell_currency,
            settings.my_currency,
        )

        out_unit_net.value = format_price(data.unit_net, settings.sell_currency_symbol, settings.sell_currency)
        out_total_cost.value = format_price(data.total_cost, settings.sell_currency_symbol, settings.sell_currency)
        out_total_net.value = format_price(data.total_net, settings.sell_currency_symbol, settings.sell_currency)
        out_ratio.value = f"{pct(data.ratio)} ({t('ratio_desc')})"
        out_discount.value = f"{pct(data.discount)}"
        out_need_sell.value = f"{format_price(data.need_sell, settings.sell_currency_symbol, settings.sell_currency)} ({t('unit')})"
        
        calc_target_qty()
        return True

    def calc_target_qty(_=None):
        target_amount = safe_float(tf_target_amount.value)
        unit_cost = safe_float(tf_cost.value)
        unit_sell = safe_float(tf_steam_sell.value)
        
        if target_amount <= 0 or unit_sell <= 0:
            out_required_qty.value = "-"
            out_required_cost.value = "-"
            return
        
        net_rate = 1.0 - settings.steam_fee_rate
        unit_net = unit_sell * net_rate
        required_qty = int((target_amount / unit_net) + 0.999)
        required_cost = unit_cost * required_qty
        
        use_exchange = settings.buy_currency != settings.sell_currency
        if use_exchange:
            required_cost_display = required_cost * settings.exchange_rate
        else:
            required_cost_display = required_cost
        
        out_required_qty.value = str(required_qty)
        out_required_cost.value = format_price(required_cost_display, settings.sell_currency_symbol, settings.sell_currency)

    def on_add(_):
        item_name = (tf_item.value or "").strip()
        if not item_name:
            return
        
        unit_cost = safe_float(tf_cost.value)
        unit_sell = safe_float(tf_steam_sell.value)
        qty = safe_int(tf_qty.value)
        note = (tf_note.value or "").strip()

        if unit_cost <= 0 or unit_sell <= 0:
            return

        use_exchange = settings.buy_currency != settings.sell_currency

        data = calculate_local(
            unit_cost,
            unit_sell,
            qty,
            use_exchange,
            settings.exchange_rate,
            settings.steam_fee_rate,
            settings.buy_currency,
            settings.sell_currency,
            settings.my_currency,
        )

        record_data = {
            "item_name": item_name,
            "note": note,
            "unit_cost": unit_cost,
            "unit_steam_sell": unit_sell,
            "qty": qty,
            "discount": data.discount,
            "unit_net": data.unit_net,
            "total_cost": data.total_cost,
            "total_net": data.total_net,
            "total_steam_sell": data.total_cost + data.total_net,
            "total_cost_in_my_currency": data.total_cost,
            "total_net_in_my_currency": data.total_net,
            "total_steam_sell_in_my_currency": data.total_cost + data.total_net,
        }

        on_add_to_history(tf_item, tf_note, tf_cost, tf_steam_sell, tf_qty, record_data)

    tf_cost.on_change = recalc
    tf_steam_sell.on_change = recalc
    tf_qty.on_change = recalc
    tf_target_amount.on_change = calc_target_qty

    calc_card = ft.Container(
        padding=20,
        border_radius=18,
        bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.SURFACE),
        border=ft.BorderSide(1, ft.Colors.with_opacity(0.2, ft.Colors.WHITE)),
        shadow=ft.BoxShadow(
            blur_radius=30,
            spread_radius=0,
            color=ft.Colors.with_opacity(0.3, ft.Colors.BLACK),
            offset=ft.Offset(0, 10),
        ),
        content=ft.Column(
            spacing=14,
            controls=[
                ft.Row(
                    spacing=14,
                    controls=[
                        tf_item,
                        tf_note,
                    ],
                ),
                ft.Row(
                    spacing=14,
                    controls=[
                        tf_cost,
                        tf_steam_sell,
                        tf_qty,
                    ],
                ),
                ft.Container(height=1, bgcolor=ft.Colors.with_opacity(0.3, ft.Colors.SURFACE)),
                ft.Row(
                    spacing=16,
                    expand=True,
                    controls=[
                        ft.Container(
                            expand=True,
                            content=ft.Column(
                                spacing=8,
                                controls=[
                                    ft.Text(t("result_title"), size=16, weight=ft.FontWeight.W_600),
                                    ft.Column(
                                        spacing=6,
                                        controls=[
                                            ft.Row(
                                                spacing=10,
                                                controls=[
                                                    ft.Text(t("unit_net"), size=12, width=100),
                                                    out_unit_net,
                                                ],
                                            ),
                                            ft.Row(
                                                spacing=10,
                                                controls=[
                                                    ft.Text(t("total_cost"), size=12, width=100),
                                                    out_total_cost,
                                                ],
                                            ),
                                            ft.Row(
                                                spacing=10,
                                                controls=[
                                                    ft.Text(t("total_net"), size=12, width=100),
                                                    out_total_net,
                                                ],
                                            ),
                                            ft.Row(
                                                spacing=10,
                                                controls=[
                                                    ft.Text(t("flip_ratio"), size=12, width=100),
                                                    out_ratio,
                                                ],
                                            ),
                                            ft.Row(
                                                spacing=10,
                                                controls=[
                                                    ft.Text(t("discount"), size=12, width=100),
                                                    out_discount,
                                                ],
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        ),
                        ft.Container(
                            expand=True,
                            content=ft.Column(
                                spacing=8,
                                controls=[
                                    ft.Text("反推数量", size=16, weight=ft.FontWeight.W_600),
                                    tf_target_amount,
                                    ft.Column(
                                        spacing=6,
                                        controls=[
                                            ft.Row(
                                                spacing=10,
                                                controls=[
                                                    ft.Text(t("required_qty"), size=12, width=100),
                                                    out_required_qty,
                                                ],
                                            ),
                                            ft.Row(
                                                spacing=10,
                                                controls=[
                                                    ft.Text(t("required_cost"), size=12, width=100),
                                                    out_required_cost,
                                                ],
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        ),
                        ft.Container(
                            expand=True,
                            content=ft.Column(
                                spacing=8,
                                controls=[
                                    ft.Text(t("reverse_title"), size=16, weight=ft.FontWeight.W_600),
                                    ft.Column(
                                        spacing=6,
                                        controls=[
                                            ft.Text(t("steam_fee", fee=settings.steam_fee_rate * 100), size=12),
                                            ft.Row(
                                                spacing=10,
                                                controls=[
                                                    ft.Text(t("break_even_price"), size=12, width=100),
                                                    out_need_sell,
                                                ],
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        ),
                    ],
                ),
                ft.Row(
                    alignment=ft.MainAxisAlignment.END,
                    controls=[
                        ft.FilledButton(
                            t("add_to_history"), 
                            icon=ft.Icons.ADD_OUTLINED, 
                            on_click=on_add,
                            style=ft.ButtonStyle(
                                bgcolor=ft.Colors.with_opacity(0.8, ft.Colors.INDIGO),
                                color=ft.Colors.WHITE,
                                padding=14,
                                shape=ft.RoundedRectangleBorder(radius=12),
                            ),
                        ),
                    ],
                ),
            ],
        ),
    )

    return {
        "view": calc_card,
        "recalc": recalc,
        "tf_cost": tf_cost,
        "tf_steam_sell": tf_steam_sell,
    }