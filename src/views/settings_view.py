import flet as ft
from typing import NamedTuple, Callable
from utils import safe_float
from config import CURRENCY_CODES, CURRENCY_SYMBOLS
from utils.i18n import LANGUAGE_CODES, LANGUAGE_LABELS
from ui.glassmorphism import create_glass_card


class SettingsView(NamedTuple):
    view: ft.Container
    tf_buy_currency: ft.TextField
    tf_sell_currency: ft.TextField
    tf_exchange_rate: ft.TextField
    tf_fee_rate: ft.TextField
    dd_my_currency: ft.Dropdown
    dd_language: ft.Dropdown
    btn_fetch_rate: ft.Control
    update_save_status: Callable
    update_exchange_label: Callable
    mark_unsaved: Callable
    save_button: ft.Control
    refresh_language: Callable


def create_settings_view(settings, snack, t, page):
    is_dark = True

    _unsaved_changes = False

    original_settings = {
        "buy_currency": settings.buy_currency,
        "sell_currency": settings.sell_currency,
        "exchange_rate": settings.exchange_rate,
        "steam_fee_rate": settings.steam_fee_rate,
        "my_currency": settings.my_currency,
        "language": settings.language,
    }

    def check_changes():
        current_exchange_rate = safe_float(tf_exchange_rate.value)
        current_fee_rate = safe_float(tf_fee_rate.value) / 100.0

        return (
            tf_buy_currency.value != original_settings["buy_currency"] or
            tf_sell_currency.value != original_settings["sell_currency"] or
            current_exchange_rate != original_settings["exchange_rate"] or
            current_fee_rate != original_settings["steam_fee_rate"] or
            dd_my_currency.value != original_settings["my_currency"] or
            dd_language.value != original_settings["language"]
        )

    def update_save_status(saved):
        if saved:
            save_status_text.value = t("saved")
            save_status_text.color = ft.Colors.GREEN
        else:
            save_status_text.value = t("unsaved")
            save_status_text.color = ft.Colors.RED
        page.update()

    def mark_unsaved():
        nonlocal _unsaved_changes
        if check_changes():
            _unsaved_changes = True
            update_save_status(False)
        else:
            _unsaved_changes = False
            update_save_status(True)

    def _on_change(_):
        mark_unsaved()

    def update_exchange_label():
        tf_exchange_rate.label = t("exchange_rate", from_curr=tf_buy_currency.value, to_curr=tf_sell_currency.value)

    def _on_currency_change(_):
        mark_unsaved()
        update_exchange_label()

    tf_buy_currency = ft.Dropdown(
        label=t("buy_currency"),
        options=[ft.dropdown.Option(code, f"{code} - {CURRENCY_SYMBOLS[code]}") for code in CURRENCY_CODES],
        value=settings.buy_currency,
        expand=True,
        filled=True,
        bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.SURFACE),
        border_color=ft.Colors.with_opacity(0.2, ft.Colors.WHITE),
        focused_border_color=ft.Colors.with_opacity(0.5, ft.Colors.INDIGO),
        border_radius=12,
        content_padding=12,
    )
    
    tf_sell_currency = ft.Dropdown(
        label=t("sell_currency"),
        options=[ft.dropdown.Option(code, f"{code} - {CURRENCY_SYMBOLS[code]}") for code in CURRENCY_CODES],
        value=settings.sell_currency,
        expand=True,
        filled=True,
        bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.SURFACE),
        border_color=ft.Colors.with_opacity(0.2, ft.Colors.WHITE),
        focused_border_color=ft.Colors.with_opacity(0.5, ft.Colors.INDIGO),
        border_radius=12,
        content_padding=12,
    )
    
    tf_exchange_rate = ft.TextField(
        label=t("exchange_rate", from_curr=settings.buy_currency, to_curr=settings.sell_currency),
        value=str(settings.exchange_rate),
        keyboard_type=ft.KeyboardType.NUMBER,
        expand=True,
        filled=True,
        bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.SURFACE),
        border_color=ft.Colors.with_opacity(0.2, ft.Colors.WHITE),
        focused_border_color=ft.Colors.with_opacity(0.5, ft.Colors.INDIGO),
        border_radius=12,
        content_padding=12,
    )
    
    tf_fee_rate = ft.TextField(
        label=t("fee_rate"),
        value=str(settings.steam_fee_rate * 100),
        keyboard_type=ft.KeyboardType.NUMBER,
        width=150,
        filled=True,
        bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.SURFACE),
        border_color=ft.Colors.with_opacity(0.2, ft.Colors.WHITE),
        focused_border_color=ft.Colors.with_opacity(0.5, ft.Colors.INDIGO),
        border_radius=12,
        content_padding=12,
    )
    
    dd_my_currency = ft.Dropdown(
        label=t("my_currency"),
        options=[ft.dropdown.Option(code, f"{code} - {CURRENCY_SYMBOLS[code]}") for code in CURRENCY_CODES],
        value=settings.my_currency,
        expand=True,
        filled=True,
        bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.SURFACE),
        border_color=ft.Colors.with_opacity(0.2, ft.Colors.WHITE),
        focused_border_color=ft.Colors.with_opacity(0.5, ft.Colors.INDIGO),
        border_radius=12,
        content_padding=12,
    )
    
    dd_language = ft.Dropdown(
        label=t("language"),
        options=[ft.dropdown.Option(code, LANGUAGE_LABELS[code]) for code in LANGUAGE_CODES],
        value=settings.language,
        expand=True,
        filled=True,
        bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.SURFACE),
        border_color=ft.Colors.with_opacity(0.2, ft.Colors.WHITE),
        focused_border_color=ft.Colors.with_opacity(0.5, ft.Colors.INDIGO),
        border_radius=12,
        content_padding=12,
    )
    
    btn_fetch_rate = ft.ElevatedButton(
        t("fetch_rate"),
        icon=ft.Icons.DOWNLOAD_OUTLINED,
        width=120,
        style=ft.ButtonStyle(
            padding=12,
            shape=ft.RoundedRectangleBorder(radius=10),
        ),
    )
    
    save_status_text = ft.Text(t("saved"), color=ft.Colors.GREEN, size=12)

    tf_buy_currency.on_select = _on_currency_change
    tf_sell_currency.on_select = _on_currency_change
    tf_exchange_rate.on_change = _on_change
    tf_fee_rate.on_change = _on_change
    dd_my_currency.on_select = _on_change
    dd_language.on_select = _on_change

    def reset_settings(_):
        tf_buy_currency.value = "CNY"
        tf_sell_currency.value = "CNY"
        tf_exchange_rate.value = "1.0"
        tf_fee_rate.value = "15.0"
        dd_my_currency.value = "CNY"
        dd_language.value = "zh"
        update_exchange_label()
        mark_unsaved()
        page.update()
        return True

    txt_settings_title = ft.Text(t("settings_title"), size=20, weight=ft.FontWeight.W_700)
    txt_settings_desc = ft.Text(t("settings_desc"), size=15, weight=ft.FontWeight.W_600)

    desc_keys = [
        "buy_currency_desc", "sell_currency_desc", "exchange_rate_desc",
        "fee_rate_desc", "my_currency_desc", "language_desc",
    ]
    desc_texts = {key: ft.Text(t(key), size=13, opacity=0.8) for key in desc_keys}

    btn_reset = ft.OutlinedButton(
        t("reset"),
        icon=ft.Icons.UNDO,
        on_click=reset_settings,
        style=ft.ButtonStyle(
            padding=12,
            shape=ft.RoundedRectangleBorder(radius=10),
        ),
    )
    btn_save = ft.FilledButton(
        t("save_settings"),
        icon=ft.Icons.SAVE,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.with_opacity(0.8, ft.Colors.INDIGO),
            color=ft.Colors.WHITE,
            padding=14,
            shape=ft.RoundedRectangleBorder(radius=12),
        ),
    )

    settings_view = create_glass_card(
        ft.Column(
            spacing=16,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        txt_settings_title,
                        save_status_text,
                    ],
                ),
                ft.Container(
                    padding=18,
                    border_radius=16,
                    bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.SURFACE_CONTAINER),
                    border=ft.BorderSide(1, ft.Colors.with_opacity(0.2, ft.Colors.WHITE)),
                    shadow=ft.BoxShadow(
                        blur_radius=20,
                        spread_radius=0,
                        color=ft.Colors.with_opacity(0.2, ft.Colors.BLACK),
                        offset=ft.Offset(0, 5),
                    ),
                    content=ft.Column(
                        spacing=16,
                        controls=[
                            ft.Row([tf_buy_currency, tf_sell_currency], spacing=14),
                            ft.Row([tf_exchange_rate, btn_fetch_rate, tf_fee_rate], spacing=14),
                            ft.Row([dd_my_currency, dd_language], spacing=14),
                        ],
                    ),
                ),
                txt_settings_desc,
                ft.Column(
                    spacing=6,
                    controls=[
                        desc_texts["buy_currency_desc"],
                        desc_texts["sell_currency_desc"],
                        desc_texts["exchange_rate_desc"],
                        desc_texts["fee_rate_desc"],
                        desc_texts["my_currency_desc"],
                        desc_texts["language_desc"],
                    ],
                ),
                ft.Row(
                        spacing=12,
                        alignment=ft.MainAxisAlignment.END,
                        controls=[
                            btn_reset,
                            btn_save,
                        ],
                    ),
            ],
        ),
        padding=20, border_radius=18, elevation=2,
        bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.SURFACE),
    )

    def refresh_language(t_new):
        tf_buy_currency.label = t_new("buy_currency")
        tf_sell_currency.label = t_new("sell_currency")
        tf_exchange_rate.label = t_new("exchange_rate", from_curr=tf_buy_currency.value, to_curr=tf_sell_currency.value)
        tf_fee_rate.label = t_new("fee_rate")
        dd_my_currency.label = t_new("my_currency")
        dd_language.label = t_new("language")
        btn_fetch_rate.text = t_new("fetch_rate")
        btn_reset.text = t_new("reset")
        btn_save.text = t_new("save_settings")
        txt_settings_title.value = t_new("settings_title")
        txt_settings_desc.value = t_new("settings_desc")
        for key in desc_keys:
            desc_texts[key].value = t_new(key)

    return SettingsView(
        view=settings_view,
        tf_buy_currency=tf_buy_currency,
        tf_sell_currency=tf_sell_currency,
        tf_exchange_rate=tf_exchange_rate,
        tf_fee_rate=tf_fee_rate,
        dd_my_currency=dd_my_currency,
        dd_language=dd_language,
        btn_fetch_rate=btn_fetch_rate,
        update_save_status=update_save_status,
        update_exchange_label=update_exchange_label,
        mark_unsaved=mark_unsaved,
        save_button=btn_save,
        refresh_language=refresh_language,
    )