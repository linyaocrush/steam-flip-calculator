import flet as ft
from src.utils import money, pct
from src.config import CURRENCY_SYMBOLS


def create_history_view(settings, snack, t):
    dt = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text(t("time"), size=12)),
            ft.DataColumn(ft.Text(t("item"), size=12)),
            ft.DataColumn(ft.Text(t("cost_unit"), size=12)),
            ft.DataColumn(ft.Text(t("sell_unit"), size=12)),
            ft.DataColumn(ft.Text(t("net_unit"), size=12)),
            ft.DataColumn(ft.Text(t("cost_total"), size=12)),
            ft.DataColumn(ft.Text(t("net_total"), size=12)),
            ft.DataColumn(ft.Text(t("flip_ratio"), size=12)),
            ft.DataColumn(ft.Text(t("discount_pct"), size=12)),
            ft.DataColumn(ft.Text(t("action"), size=12)),
        ],
        rows=[],
        border_radius=8,
        show_checkbox_column=False,
        expand=True,
        width=float("inf"),
    )

    def row_for_record(record, refresh_callback):
        buy_symbol = CURRENCY_SYMBOLS.get(record.buy_currency, "¥")
        sell_symbol = CURRENCY_SYMBOLS.get(record.sell_currency, "¥")
        
        return ft.DataRow(
            cells=[
                ft.DataCell(ft.Text(record.ts, size=11)),
                ft.DataCell(
                    ft.Column(
                        spacing=2,
                        tight=True,
                        controls=[
                            ft.Text(record.item_name, size=12, weight=ft.FontWeight.W_500),
                            ft.Text(record.note, size=10, color=ft.Colors.GREY) if record.note else ft.Container(),
                        ],
                    )
                ),
                ft.DataCell(ft.Text(f"{buy_symbol} {money(record.unit_cost)}", size=11)),
                ft.DataCell(ft.Text(f"{sell_symbol} {money(record.unit_steam_sell)}", size=11)),
                ft.DataCell(ft.Text(f"{sell_symbol} {money(record.unit_net)}", size=11)),
                ft.DataCell(ft.Text(f"{buy_symbol} {money(record.total_cost)}", size=11)),
                ft.DataCell(ft.Text(f"{sell_symbol} {money(record.total_net)}", size=11)),
                ft.DataCell(ft.Text(pct(record.ratio), size=11)),
                ft.DataCell(ft.Text(pct(record.discount), size=11)),
                ft.DataCell(
                    ft.IconButton(
                        ft.Icons.DELETE_OUTLINE,
                        icon_color=ft.Colors.RED,
                        tooltip=t("delete"),
                        on_click=lambda _, rid=record.id: delete_record(rid, refresh_callback),
                    )
                ),
            ],
        )

    def delete_record(record_id, refresh_callback):
        from src.services.database import delete_record as db_delete_record
        
        def yes(_):
            success = db_delete_record(record_id)
            if success:
                snack.content = ft.Text(t("delete_success"))
            else:
                snack.content = ft.Text(t("delete_failed"))
            snack.open = True
            refresh_callback()
            snack.page.update()

        def no(_):
            snack.page.dialog = None
            snack.page.update()

        snack.page.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(t("confirm")),
            content=ft.Text(t("confirm_clear_msg")),
            actions=[
                ft.TextButton(t("cancel"), on_click=no),
                ft.FilledButton(t("confirm"), on_click=yes)
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        snack.page.dialog.open = True
        snack.page.update()

    return {
        "dt": dt,
        "row_for_record": row_for_record,
    }