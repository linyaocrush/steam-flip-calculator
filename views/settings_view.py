import flet as ft
from utils import safe_float
from config import CURRENCY_CODES, CURRENCY_SYMBOLS
from exchange_rate import fetch_exchange_rate
from database import save_settings
from i18n import LANGUAGE_CODES, LANGUAGE_LABELS


def create_settings_view(settings, snack, t, page):
    tf_buy_currency = ft.Dropdown(
        label=t("buy_currency"),
        options=[ft.dropdown.Option(code, f"{code} - {CURRENCY_SYMBOLS[code]}") for code in CURRENCY_CODES],
        value=settings["buy_currency"],
        expand=True,
    )
    
    tf_sell_currency = ft.Dropdown(
        label=t("sell_currency"),
        options=[ft.dropdown.Option(code, f"{code} - {CURRENCY_SYMBOLS[code]}") for code in CURRENCY_CODES],
        value=settings["sell_currency"],
        expand=True,
    )
    
    tf_exchange_rate = ft.TextField(
        label=t("exchange_rate", from_curr=settings["buy_currency"], to_curr=settings["sell_currency"]),
        value=str(settings["exchange_rate"]),
        keyboard_type=ft.KeyboardType.NUMBER,
        expand=True,
    )
    
    tf_fee_rate = ft.TextField(
        label=t("fee_rate"),
        value=str(settings["steam_fee_rate"] * 100),
        keyboard_type=ft.KeyboardType.NUMBER,
        width=150,
    )
    
    dd_theme_mode = ft.Dropdown(
        label=t("theme_mode"),
        options=[
            ft.dropdown.Option("LIGHT", t("theme_light")),
            ft.dropdown.Option("DARK", t("theme_dark")),
        ],
        value=settings["theme_mode"],
        width=150,
    )
    
    dd_my_currency = ft.Dropdown(
        label=t("my_currency"),
        options=[ft.dropdown.Option(code, f"{code} - {CURRENCY_SYMBOLS[code]}") for code in CURRENCY_CODES],
        value=settings["my_currency"],
        expand=True,
    )
    
    dd_language = ft.Dropdown(
        label=t("language"),
        options=[ft.dropdown.Option(code, LANGUAGE_LABELS[code]) for code in LANGUAGE_CODES],
        value=settings.get("language", "zh"),
        expand=True,
    )
    
    btn_fetch_rate = ft.ElevatedButton(
        t("fetch_rate"),
        icon=ft.Icons.DOWNLOAD_OUTLINED,
        width=120,
    )
    
    save_status_text = ft.Text(t("unsaved"), color=ft.Colors.RED, size=12)
    
    _unsaved_changes = False

    def mark_unsaved():
        nonlocal _unsaved_changes
        _unsaved_changes = True
        update_save_status(False)

    def update_save_status(saved):
        if saved:
            save_status_text.value = t("saved")
            save_status_text.color = ft.Colors.GREEN
        else:
            save_status_text.value = t("unsaved")
            save_status_text.color = ft.Colors.RED
        page.update()

    def check_unsaved():
        def on_change(_):
            mark_unsaved()
        
        tf_buy_currency.on_change = on_change
        tf_sell_currency.on_change = on_change
        tf_exchange_rate.on_change = on_change
        tf_fee_rate.on_change = on_change
        dd_theme_mode.on_change = on_change
        dd_my_currency.on_change = on_change
        dd_language.on_change = on_change

    def update_exchange_label():
        tf_exchange_rate.label = t("exchange_rate", from_curr=tf_buy_currency.value, to_curr=tf_sell_currency.value)

    def on_buy_currency_change(_):
        mark_unsaved()
        update_exchange_label()

    def on_sell_currency_change(_):
        mark_unsaved()
        update_exchange_label()

    tf_buy_currency.on_change = on_buy_currency_change
    tf_sell_currency.on_change = on_sell_currency_change

    def reset_settings(_):
        tf_buy_currency.value = "CNY"
        tf_sell_currency.value = "CNY"
        tf_exchange_rate.value = "1.0"
        tf_fee_rate.value = "15.0"
        dd_theme_mode.value = "LIGHT"
        dd_my_currency.value = "CNY"
        dd_language.value = "zh"
        update_exchange_label()
        mark_unsaved()
        page.update()
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
                            ft.Text(t("settings_title"), size=18, weight=ft.FontWeight.W_700),
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
                                ft.Row([dd_theme_mode, dd_language], spacing=12),
                                ft.Row([dd_my_currency], spacing=12),
                            ],
                        ),
                    ),
                    ft.Text(t("settings_desc"), size=14, weight=ft.FontWeight.W_600),
                    ft.Column(
                        spacing=4,
                        controls=[
                            ft.Text(t("buy_currency_desc"), size=12, opacity=0.8),
                            ft.Text(t("sell_currency_desc"), size=12, opacity=0.8),
                            ft.Text(t("exchange_rate_desc"), size=12, opacity=0.8),
                            ft.Text(t("fee_rate_desc"), size=12, opacity=0.8),
                            ft.Text(t("theme_mode_desc"), size=12, opacity=0.8),
                            ft.Text(t("my_currency_desc"), size=12, opacity=0.8),
                            ft.Text(t("language_desc"), size=12, opacity=0.8),
                        ],
                    ),
                    ft.Row(
                        spacing=10,
                        alignment=ft.MainAxisAlignment.END,
                        controls=[
                            ft.OutlinedButton(t("reset"), icon=ft.Icons.UNDO, on_click=reset_settings),
                            ft.FilledButton(t("save_settings"), icon=ft.Icons.SAVE),
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
        "dd_language": dd_language,
        "btn_fetch_rate": btn_fetch_rate,
        "update_save_status": update_save_status,
        "update_exchange_label": update_exchange_label,
        "mark_unsaved": mark_unsaved,
        "check_unsaved": check_unsaved,
        "save_button": settings_view.content.content.controls[4].controls[1],
    }