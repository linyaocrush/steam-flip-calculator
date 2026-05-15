import flet as ft
from utils import money, pct
from api import api_delete


def create_history_view(settings, snack):
    dt = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("时间")),
            ft.DataColumn(ft.Text("物品")),
            ft.DataColumn(ft.Text("数量"), numeric=True),
            ft.DataColumn(ft.Text("成本(单)"), numeric=True),
            ft.DataColumn(ft.Text("售出(单)"), numeric=True),
            ft.DataColumn(ft.Text("到账(单)"), numeric=True),
            ft.DataColumn(ft.Text("花费(总)"), numeric=True),
            ft.DataColumn(ft.Text("到手(总)"), numeric=True),
            ft.DataColumn(ft.Text("折扣%"), numeric=True),
            ft.DataColumn(ft.Text("操作")),
        ],
        rows=[],
    )

    def row_for_record(r, on_refresh):
        ratio = (r["total_cost"] / r["total_net"]) if r["total_net"] > 0 else 0.0
        discount = (1.0 - ratio) if r["total_net"] > 0 else 0.0

        def do_delete(_):
            _, status = api_delete(f"/records/{r['id']}")
            if status == 200:
                snack.content = ft.Text("已删除记录")
            else:
                snack.content = ft.Text("删除失败")
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
                ft.DataCell(ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, tooltip="删除", on_click=do_delete)),
            ]
        )

    return {
        "dt": dt,
        "row_for_record": row_for_record,
    }