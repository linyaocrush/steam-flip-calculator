import flet as ft
from config import CURRENCY_CODES, CURRENCY_NAMES, CURRENCY_SYMBOLS
from utils import safe_float


def create_settings_view(settings, snack):
    settings_saved = True
    save_status_icon = ft.Icon(ft.Icons.CHECK_CIRCLE, size=18, color=ft.Colors.GREEN)
    save_status_label = ft.Text("已保存设置", size=14, weight=ft.FontWeight.W_500, color=ft.Colors.GREEN)
    save_status_text = ft.Row(
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=4,
        controls=[save_status_icon, save_status_label],
    )

    def update_save_status(saved):
        nonlocal settings_saved
        settings_saved = saved
        if saved:
            save_status_label.value = "已保存设置"
            save_status_label.color = ft.Colors.GREEN
            save_status_icon.name = ft.Icons.CHECK_CIRCLE
            save_status_icon.color = ft.Colors.GREEN
        else:
            save_status_label.value = "未保存"
            save_status_label.color = ft.Colors.RED
            save_status_icon.name = ft.Icons.CIRCLE
            save_status_icon.color = ft.Colors.RED
        return True

    def mark_unsaved(_=None):
        if settings_saved:
            update_save_status(False)
        return True

    tf_buy_currency = ft.Dropdown(
        label="买入货币",
        options=[ft.dropdown.Option(code, f"{code} - {CURRENCY_NAMES[code]}") for code in CURRENCY_CODES],
        value=settings["buy_currency"],
        expand=True,
    )

    tf_sell_currency = ft.Dropdown(
        label="卖出货币（Steam 市场）",
        options=[ft.dropdown.Option(code, f"{code} - {CURRENCY_NAMES[code]}") for code in CURRENCY_CODES],
        value=settings["sell_currency"],
        expand=True,
    )

    tf_exchange_rate = ft.TextField(
        label=f"汇率（{settings['buy_currency']} -> {settings['sell_currency']}）",
        value=str(settings["exchange_rate"]),
        keyboard_type=ft.KeyboardType.NUMBER,
        expand=True,
        on_change=mark_unsaved,
    )

    tf_fee_rate = ft.TextField(
        label="Steam 手续费率 (%)",
        value=f"{settings['steam_fee_rate'] * 100:.1f}",
        keyboard_type=ft.KeyboardType.NUMBER,
        width=150,
        on_change=mark_unsaved,
    )

    dd_theme_mode = ft.Dropdown(
        label="默认主题模式",
        options=[
            ft.dropdown.Option("LIGHT", "浅色模式"),
            ft.dropdown.Option("DARK", "深色模式"),
        ],
        value=settings["theme_mode"],
        width=150,
    )

    dd_my_currency = ft.Dropdown(
        label="我的货币",
        options=[ft.dropdown.Option(code, f"{code} - {CURRENCY_NAMES[code]}") for code in CURRENCY_CODES],
        value=settings["my_currency"],
        expand=True,
    )

    btn_fetch_rate = ft.ElevatedButton(
        "获取汇率",
        icon=ft.Icons.DOWNLOAD_OUTLINED,
        width=120,
    )

    def update_exchange_label(_=None):
        buy_code = tf_buy_currency.value if tf_buy_currency.value else "CNY"
        sell_code = tf_sell_currency.value if tf_sell_currency.value else "CNY"
        tf_exchange_rate.label = f"汇率（{buy_code} -> {sell_code}）"
        return True

    tf_buy_currency.on_change = lambda e: (update_exchange_label(e), mark_unsaved())
    tf_sell_currency.on_change = lambda e: (update_exchange_label(e), mark_unsaved())
    dd_theme_mode.on_change = mark_unsaved
    dd_my_currency.on_change = mark_unsaved

    def reset_settings(_):
        tf_buy_currency.value = "CNY"
        tf_sell_currency.value = "CNY"
        tf_exchange_rate.value = "1.0"
        tf_fee_rate.value = "15.0"
        dd_theme_mode.value = "LIGHT"
        dd_my_currency.value = "CNY"
        update_exchange_label()
        mark_unsaved()
        return True

    settings_view = ft.Card(
        elevation=1,
        content=ft.Container(
            padding=18,
            content=ft.Column(
                spacing=14,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text("应用设置", size=18, weight=ft.FontWeight.W_700),
                            save_status_text,
                        ],
                    ),
                    ft.Container(
                        padding=16,
                        border_radius=14,
                        bgcolor=ft.Colors.SURFACE_CONTAINER,
                        content=ft.Column(
                            spacing=14,
                            controls=[
                                ft.Row([tf_buy_currency, tf_sell_currency], spacing=12),
                                ft.Row([tf_exchange_rate, btn_fetch_rate, tf_fee_rate], spacing=12),
                                ft.Row([dd_theme_mode], spacing=12),
                                ft.Row([dd_my_currency], spacing=12),
                            ],
                        ),
                    ),
                    ft.Text("说明：", size=14, weight=ft.FontWeight.W_600),
                    ft.Column(
                        spacing=4,
                        controls=[
                            ft.Text("- 买入货币：在第三方平台购买物品使用的货币", size=12, opacity=0.8),
                            ft.Text("- 卖出货币：Steam 市场所在区域的货币", size=12, opacity=0.8),
                            ft.Text("- 汇率：买入货币兑换为卖出货币的比率（自动获取，12小时缓存）", size=12, opacity=0.8),
                            ft.Text("- 手续费：Steam 市场收取的交易手续费（默认 15%）", size=12, opacity=0.8),
                            ft.Text("- 默认主题模式：应用启动后默认的主题模式", size=12, opacity=0.8),
                            ft.Text("- 我的货币：显示价格时自动转换为此货币", size=12, opacity=0.8),
                        ],
                    ),
                    ft.Row(
                        spacing=10,
                        alignment=ft.MainAxisAlignment.END,
                        controls=[
                            ft.OutlinedButton("重置", icon=ft.Icons.UNDO, on_click=reset_settings),
                            ft.FilledButton("保存设置", icon=ft.Icons.SAVE),
                        ],
                    ),
                ],
            ),
        ),
    )

    return {
        "view": settings_view,
        "tf_buy_currency": tf_buy_currency,
        "tf_sell_currency": tf_sell_currency,
        "tf_exchange_rate": tf_exchange_rate,
        "tf_fee_rate": tf_fee_rate,
        "dd_theme_mode": dd_theme_mode,
        "dd_my_currency": dd_my_currency,
        "btn_fetch_rate": btn_fetch_rate,
        "update_save_status": update_save_status,
        "update_exchange_label": update_exchange_label,
        "mark_unsaved": mark_unsaved,
        "save_button": settings_view.content.content.controls[4].controls[1],
    }