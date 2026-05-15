import flet as ft
from utils import money, pct
from api import api_delete


def create_history_view(settings, snack, t):
    dt = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text(t("time"))),
            ft.DataColumn(ft.Text(t("item"))),
            ft.DataColumn(ft.Text(t("quantity")), numeric=True),
            ft.DataColumn(ft.Text(t("cost_unit")), numeric=True),
            ft.DataColumn(ft.Text(t("sell_unit")), numeric=True),
            ft.DataColumn(ft.Text(t("net_unit")), numeric=True),
            ft.DataColumn(ft.Text(t("cost_total")), numeric=True),
            ft.DataColumn(ft.Text(t("net_total")), numeric=True),
            ft.DataColumn(ft.Text(t("discount_pct")), numeric=True),
            ft.DataColumn(ft.Text(t("action"))),
        ],
        rows=[],
    )

    def row_for_record(r, on_refresh):
        ratio = (r["total_cost"] / r["total_net"]) if r["total_net"] > 0 else 0.0
        discount = (1.0 - ratio) if r["total_net"] > 0 else 0.0

        def do_delete(_):
            _, status = api_delete(f"/records/{r['id']}")
            if status == 200:
                snack.content = ft.Text(t("delete_success"))
            else:
                snack.content = ft.Text(t("delete_failed"))
            snack.open = True
            on_refresh()

        item_col = ft.Column(
            spacing=2,
            controls=[
                ft.Text(r["item_name"], weight=ft.FontWeight.W_600),
                ft.Text(r["note"] or "", size=12, opacity=0.7),
            ],
        )

        return ft.DataRow(
            cells=[
                ft.DataCell(ft.Text(r["ts"])),
                ft.DataCell(item_col),
                ft.DataCell(ft.Text(str(r["qty"]))),
                ft.DataCell(ft.Text(money(r["unit_cost"]))),
                ft.DataCell(ft.Text(money(r["unit_steam_sell"]))),
                ft.DataCell(ft.Text(money(r["unit_net"]))),
                ft.DataCell(ft.Text(money(r["total_cost"]))),
                ft.DataCell(ft.Text(money(r["total_net"]))),
                ft.DataCell(ft.Text(pct(discount))),
                ft.DataCell(ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, tooltip=t("delete"), on_click=do_delete)),
            ]
        )

    return {
        "dt": dt,
        "row_for_record": row_for_record,
    }