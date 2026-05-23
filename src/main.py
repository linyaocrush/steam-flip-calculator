import flet as ft
from decimal import Decimal
from utils import safe_float, safe_decimal, safe_int
from utils.i18n import get_text
from services.database import init_db, get_settings, get_records, get_stats, add_record, clear_records
from models import HistoryRecord
from views import (
    create_calculator_view,
    create_history_view,
    create_stats_view,
    create_settings_view,
)
from ui.glassmorphism import (
    create_gradient_background,
    create_floating_orbs,
)
from ui.navigation import create_navigation, AppView
from controllers import setup_settings_controller
from state.app_state import app_state


def main(page: ft.Page):
    page.title = "Steam 倒余额工具箱"
    page.window_width = 1040
    page.window_height = 760
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = ft.Theme(
        use_material3=True,
        color_scheme_seed=ft.Colors.INDIGO,
        visual_density=ft.VisualDensity.COMFORTABLE,
    )

    init_db()
    settings = get_settings()
    page.title = get_text("app_title", settings.language)
    page.bgcolor = ft.Colors.TRANSPARENT

    def get_t():
        return lambda key, **kwargs: get_text(key, app_state.get_settings().language, **kwargs)

    t = get_t()
    snack = ft.SnackBar(content=ft.Text(""))
    page.snack_bar = snack

    # --- Views ---
    def on_add_to_history(tf_item, tf_note, tf_cost, tf_steam_sell, tf_qty, record_data=None):
        item_name = (tf_item.value or "").strip()
        if not item_name:
            snack.content = ft.Text(t("error_empty_item"))
            snack.open = True
            page.update()
            return

        unit_cost = safe_decimal(tf_cost.value)
        unit_sell = safe_decimal(tf_steam_sell.value)
        qty = safe_int(tf_qty.value)
        note = (tf_note.value or "").strip()

        if unit_cost <= 0 or unit_sell <= 0:
            snack.content = ft.Text(t("error_invalid_price"))
            snack.open = True
            page.update()
            return

        payload = {
            "item_name": item_name,
            "note": note,
            "unit_cost": unit_cost,
            "unit_steam_sell": unit_sell,
            "qty": qty,
        }

        if record_data:
            payload.update({
                "discount": record_data.get("discount", Decimal('0')),
                "unit_net": record_data.get("unit_net", Decimal('0')),
                "total_cost": record_data.get("total_cost", Decimal('0')),
                "total_net": record_data.get("total_net", Decimal('0')),
                "total_steam_sell": record_data.get("total_steam_sell", Decimal('0')),
                "total_cost_in_my_currency": record_data.get("total_cost_in_my_currency", Decimal('0')),
                "total_net_in_my_currency": record_data.get("total_net_in_my_currency", Decimal('0')),
                "total_steam_sell_in_my_currency": record_data.get("total_steam_sell_in_my_currency", Decimal('0')),
                "ratio": record_data.get("ratio", Decimal('0')),
            })

        record = HistoryRecord(**payload)
        saved_record = add_record(record, settings)

        if saved_record:
            snack.content = ft.Text(t("save_success"))
            add_row(saved_record, refresh_stats)
        else:
            snack.content = ft.Text(t("save_failed"))
        snack.open = True
        refresh_stats()

    calculator = create_calculator_view(settings, on_add_to_history, t, page)
    calc_card = calculator.view
    recalc = calculator.recalc
    tf_cost = calculator.tf_cost
    tf_steam_sell = calculator.tf_steam_sell

    stats = create_stats_view(settings, t)
    stats_view = stats.view
    update_stats = stats.update_stats

    def refresh_stats():
        stats_data = get_stats()
        update_stats(stats_data)
        page.update()

    history = create_history_view(settings, snack, t, page)
    dt = history.dt
    row_for_record = history.row_for_record
    add_row = history.add_row

    def refresh_history():
        records = get_records()
        dt.rows = [row_for_record(r, refresh_stats) for r in records]
        page.update()

    def refresh_history_and_stats():
        records = get_records()
        stats_data = get_stats()
        dt.rows = [row_for_record(r, refresh_stats) for r in records]
        update_stats(stats_data)
        page.update()

    def clear_all(_):
        success = clear_records()
        if success:
            snack.content = ft.Text(t("clear_success"))
            dt.rows.clear()
        else:
            snack.content = ft.Text(t("clear_failed"))
        snack.open = True
        refresh_stats()

    settings_ui = create_settings_view(settings, snack, t, page)
    settings_view = settings_ui.view

    # --- Navigation ---
    tab_buttons, switch_view, register_view, refresh_nav = create_navigation(t, page)
    register_view(AppView.CALCULATOR, calc_card)
    register_view(AppView.STATS, stats_view)
    register_view(AppView.SETTINGS, settings_view)

    # --- Settings controller ---
    setup_settings_controller(settings_ui, page, snack, t)

    # --- Layout ---
    is_dark = True

    txt_app_title = ft.Text(t("app_title"), size=22, weight=ft.FontWeight.W_700, color=ft.Colors.WHITE)
    txt_history_title = ft.Text(t("history_title"), size=20, weight=ft.FontWeight.W_700)
    btn_refresh = ft.OutlinedButton(
        t("refresh"),
        icon=ft.Icons.REFRESH,
        on_click=lambda _: refresh_history_and_stats(),
        style=ft.ButtonStyle(padding=10, shape=ft.RoundedRectangleBorder(radius=10)),
    )
    btn_clear_all = ft.OutlinedButton(
        t("clear_all"),
        icon=ft.Icons.DELETE_SWEEP_OUTLINED,
        on_click=clear_all,
        style=ft.ButtonStyle(padding=10, shape=ft.RoundedRectangleBorder(radius=10)),
    )

    def refresh_main_language(t):
        txt_app_title.value = t("app_title")
        txt_history_title.value = t("history_title")
        btn_refresh.text = t("refresh")
        btn_clear_all.text = t("clear_all")

    history_view = ft.Column(
        expand=True,
        spacing=14,
        controls=[
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    txt_history_title,
                    ft.Row(
                        spacing=10,
                        controls=[
                            btn_refresh,
                            btn_clear_all,
                        ],
                    ),
                ],
            ),
            ft.Container(
                expand=True,
                border_radius=16,
                padding=14,
                bgcolor=ft.Colors.with_opacity(0.2 if is_dark else 0.4, ft.Colors.SURFACE),
                border=ft.BorderSide(1, ft.Colors.with_opacity(0.2, ft.Colors.WHITE if is_dark else ft.Colors.BLACK)),
                shadow=ft.BoxShadow(
                    blur_radius=25,
                    spread_radius=0,
                    color=ft.Colors.with_opacity(0.25 if is_dark else 0.12, ft.Colors.BLACK),
                    offset=ft.Offset(0, 8),
                ),
                content=ft.Column([dt], expand=True),
            ),
        ],
    )
    register_view(AppView.HISTORY, history_view)

    main_content = ft.Container(
        padding=16,
        content=ft.Column(
            spacing=12,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Row(
                            spacing=12,
                            controls=[
                                ft.Container(
                                    content=ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED, size=28, color=ft.Colors.WHITE),
                                    padding=8,
                                    border_radius=12,
                                    bgcolor=ft.Colors.with_opacity(0.3, ft.Colors.INDIGO),
                                ),
                                txt_app_title,
                            ],
                        ),
                    ],
                ),
                ft.Container(
                    padding=12,
                    border_radius=14,
                    bgcolor=ft.Colors.with_opacity(0.2 if is_dark else 0.4, ft.Colors.SURFACE),
                    content=tab_buttons,
                ),
                calc_card,
                history_view,
                stats_view,
                settings_view,
            ],
        ),
    )

    page.add(
        ft.Stack(
            [
                create_gradient_background(is_dark),
                create_floating_orbs(is_dark),
                ft.Container(content=main_content, padding=20, expand=True),
            ],
            expand=True,
            width=float("inf"),
            height=float("inf"),
        )
    )

    # --- Language refresh ---
    _language_refresh_callbacks = [
        calculator.refresh_language,
        stats.refresh_language,
        history.refresh_language,
        settings_ui.refresh_language,
        refresh_nav,
        refresh_main_language,
    ]

    _last_language = settings.language

    def _on_settings_changed(new_settings):
        nonlocal _last_language
        if new_settings.language != _last_language:
            _last_language = new_settings.language
            _t = get_t()
            for cb in _language_refresh_callbacks:
                cb(_t)
            page.update()

    app_state.subscribe(_on_settings_changed)

    # --- Start ---
    history_view.visible = False
    stats_view.visible = False
    settings_view.visible = False
    refresh_history_and_stats()
    recalc()
    page.update()


if __name__ == "__main__":
    ft.run(main, view=ft.AppView.FLET_APP, port=0)
