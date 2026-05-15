import flet as ft
import requests

# API 配置
API_BASE_URL = "http://localhost:5000/api"


def money(x: float) -> str:
    return f"{x:,.2f}"


def pct(x: float) -> str:
    return f"{x * 100:,.2f}%"


def safe_float(s: str) -> float:
    try:
        s = (s or "").strip().replace(",", "")
        if s == "":
            return 0.0
        return float(s)
    except Exception:
        return 0.0


def safe_int(s: str) -> int:
    try:
        s = (s or "").strip().replace(",", "")
        if s == "":
            return 1
        v = int(float(s))
        return max(v, 1)
    except Exception:
        return 1


def api_post(endpoint, data=None):
    try:
        response = requests.post(f"{API_BASE_URL}{endpoint}", json=data, timeout=5)
        return response.json(), response.status_code
    except Exception as e:
        return {"error": str(e)}, 500


def api_get(endpoint):
    try:
        response = requests.get(f"{API_BASE_URL}{endpoint}", timeout=5)
        return response.json(), response.status_code
    except Exception as e:
        return {"error": str(e)}, 500


def api_delete(endpoint):
    try:
        response = requests.delete(f"{API_BASE_URL}{endpoint}", timeout=5)
        return response.json(), response.status_code
    except Exception as e:
        return {"error": str(e)}, 500


def check_api_connection():
    """检查后端API连接状态"""
    try:
        response = requests.get(f"{API_BASE_URL}/stats", timeout=3)
        return response.status_code == 200
    except Exception:
        return False


def main(page: ft.Page):
    page.title = "Steam 倒余额计算器"
    page.window_width = 1040
    page.window_height = 760
    page.theme_mode = ft.ThemeMode.LIGHT

    page.theme = ft.Theme(
        use_material3=True,
        color_scheme_seed=ft.Colors.INDIGO,
        visual_density=ft.VisualDensity.COMFORTABLE,
    )

    # 加载状态变量
    loading_text = ft.Text("正在连接后端服务...", size=16)
    loading_progress = ft.ProgressBar(width=400, color=ft.Colors.INDIGO)
    loading_error = ft.Text("", size=14, color=ft.Colors.RED)
    retry_button = ft.Button("重试连接", icon=ft.Icons.REFRESH, visible=False)

    # 加载界面
    loading_view = ft.Column(
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=20,
        controls=[
            ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED, size=64, color=ft.Colors.INDIGO),
            ft.Text("Steam 倒余额计算器", size=24, weight=ft.FontWeight.W_700),
            loading_progress,
            loading_text,
            loading_error,
            retry_button,
        ],
    )

    page.add(loading_view)
    page.update()

    def init_app():
        """初始化应用主界面"""
        snack = ft.SnackBar(content=ft.Text(""))
        page.snack_bar = snack

        # ---- Inputs
        tf_item = ft.TextField(label="物品名称", value="CS2 刀/皮肤", expand=True)
        tf_note = ft.TextField(label="备注（可选）", expand=True)

        tf_cost = ft.TextField(
            label="第三方成本（单价）",
            value="70",
            prefix=ft.Text("¥"),
            keyboard_type=ft.KeyboardType.NUMBER,
            expand=True,
        )
        tf_steam_sell = ft.TextField(
            label="Steam 售出金额（单价）",
            value="100",
            prefix=ft.Text("¥"),
            keyboard_type=ft.KeyboardType.NUMBER,
            expand=True,
        )
        tf_qty = ft.TextField(
            label="数量",
            value="1",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=120,
        )

        # ---- Outputs
        out_unit_net = ft.Text(value="-")
        out_total_cost = ft.Text(value="-")
        out_total_net = ft.Text(value="-")
        out_ratio = ft.Text(value="-")
        out_discount = ft.Text(value="-")
        out_need_sell = ft.Text(value="-")

        def recalc(_=None):
            unit_cost = safe_float(tf_cost.value)
            unit_sell = safe_float(tf_steam_sell.value)
            qty = safe_int(tf_qty.value)

            data, status = api_post("/calculate", {
                "unit_cost": unit_cost,
                "unit_steam_sell": unit_sell,
                "qty": qty
            })

            if status == 200:
                out_unit_net.value = f"¥ {money(data['unit_net'])}"
                out_total_cost.value = f"¥ {money(data['total_cost'])}"
                out_total_net.value = f"¥ {money(data['total_net'])}"
                out_ratio.value = f"{pct(data['ratio'])}（成本/到手余额）"
                out_discount.value = f"{pct(data['discount'])}"
                out_need_sell.value = f"¥ {money(data['need_sell'])}（单价）"
            else:
                out_unit_net.value = "-"
                out_total_cost.value = "-"
                out_total_net.value = "-"
                out_ratio.value = "-"
                out_discount.value = "-"
                out_need_sell.value = "-"
            page.update()

        for t in (tf_cost, tf_steam_sell, tf_qty):
            t.on_change = recalc

        # ---- DataTable
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

        def row_for_record(r):
            ratio = (r["total_cost"] / r["total_net"]) if r["total_net"] > 0 else 0.0
            discount = (1.0 - ratio) if r["total_net"] > 0 else 0.0

            def do_delete(_):
                _, status = api_delete(f"/records/{r['id']}")
                if status == 200:
                    snack.content = ft.Text("已删除记录")
                else:
                    snack.content = ft.Text("删除失败")
                snack.open = True
                refresh_history()
                refresh_stats()
                page.update()

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

        def refresh_history():
            records, status = api_get("/records")
            if status == 200:
                dt.rows = [row_for_record(r) for r in records]
            else:
                dt.rows = []
            page.update()

        # ---- Stats
        st_total_cost = ft.Text("-")
        st_total_net = ft.Text("-")
        st_total_sell = ft.Text("-")
        st_total_qty = ft.Text("-")
        st_ratio = ft.Text("-")
        st_discount = ft.Text("-")

        def refresh_stats():
            stats, status = api_get("/stats")
            if status == 200:
                st_total_cost.value = f"¥ {money(stats['total_cost'])}"
                st_total_net.value = f"¥ {money(stats['total_net'])}"
                st_total_sell.value = f"¥ {money(stats['total_steam_sell'])}"
                st_total_qty.value = f"{stats['total_qty']}"
                st_ratio.value = pct(stats["ratio"]) if stats["total_net"] > 0 else "-"
                st_discount.value = pct(stats["discount"]) if stats["total_net"] > 0 else "-"
            else:
                st_total_cost.value = "-"
                st_total_net.value = "-"
                st_total_sell.value = "-"
                st_total_qty.value = "-"
                st_ratio.value = "-"
                st_discount.value = "-"
            page.update()

        # ---- Dialog
        dlg = ft.AlertDialog(modal=True, title=ft.Text("清空全部历史？"), content=ft.Text("此操作不可撤销。"), actions=[])
        page.dialog = dlg

        def clear_all(_):
            def yes(_):
                _, status = api_delete("/records")
                if status == 200:
                    snack.content = ft.Text("已清空全部历史")
                else:
                    snack.content = ft.Text("清空失败")
                snack.open = True
                refresh_history()
                refresh_stats()
                dlg.open = False
                page.update()

            def no(_):
                dlg.open = False
                page.update()

            dlg.actions = [ft.TextButton("取消", on_click=no), ft.FilledButton("确认清空", on_click=yes)]
            dlg.open = True
            page.update()

        def add_to_history(_):
            item_name = (tf_item.value or "").strip()
            if not item_name:
                snack.content = ft.Text("请填写物品名称")
                snack.open = True
                page.update()
                return

            unit_cost = safe_float(tf_cost.value)
            unit_sell = safe_float(tf_steam_sell.value)
            qty = safe_int(tf_qty.value)
            note = (tf_note.value or "").strip()

            if unit_cost <= 0 or unit_sell <= 0:
                snack.content = ft.Text("单价必须大于 0")
                snack.open = True
                page.update()
                return

            data, status = api_post("/records", {
                "item_name": item_name,
                "note": note,
                "unit_cost": unit_cost,
                "unit_steam_sell": unit_sell,
                "qty": qty
            })

            if status == 201:
                snack.content = ft.Text("已记录到历史")
            else:
                snack.content = ft.Text(data.get("error", "记录失败"))
            snack.open = True
            refresh_history()
            refresh_stats()
            page.update()

        def kv_row(k: str, v: ft.Control):
            return ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text(k), v])

        calc_result_box = ft.Container(
            expand=True,
            padding=14,
            border_radius=14,
            bgcolor=ft.Colors.SURFACE_CONTAINER,
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Text("计算结果（按单价与数量）", size=14, weight=ft.FontWeight.W_600),
                    kv_row("Steam 实际到账(单价):", out_unit_net),
                    kv_row("总花费:", out_total_cost),
                    kv_row("总到手余额:", out_total_net),
                    kv_row("倒余额比例:", out_ratio),
                    kv_row("折扣(越大越好):", out_discount),
                ],
            ),
        )

        reverse_box = ft.Container(
            width=340,
            padding=14,
            border_radius=14,
            bgcolor=ft.Colors.SURFACE_CONTAINER,
            content=ft.Column(
                spacing=10,
                controls=[
                    ft.Text("反推挂刀价（规则）", size=14, weight=ft.FontWeight.W_600),
                    ft.Text("Steam 市场固定 15% 手续费：卖 100 到账 85", size=12, opacity=0.8),
                    kv_row("保本售卖价(单价):", out_need_sell),
                    ft.FilledButton("记录到历史", icon=ft.Icons.ADD_CIRCLE_OUTLINE, on_click=add_to_history),
                ],
            ),
        )

        calc_card = ft.Card(
            elevation=1,
            content=ft.Container(
                padding=18,
                content=ft.Column(
                    spacing=14,
                    controls=[
                        ft.Row([tf_item, tf_note], spacing=12),
                        ft.Row([tf_cost, tf_steam_sell, tf_qty], spacing=12),
                        ft.Divider(height=1),
                        ft.Row([calc_result_box, reverse_box], spacing=14),
                    ],
                ),
            ),
        )

        history_view = ft.Column(
            expand=True,
            spacing=12,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text("倒余额历史", size=18, weight=ft.FontWeight.W_700),
                        ft.Row(
                            spacing=8,
                            controls=[
                                ft.OutlinedButton("刷新", icon=ft.Icons.REFRESH, on_click=lambda _: (refresh_history(), refresh_stats())),
                                ft.OutlinedButton("清空全部", icon=ft.Icons.DELETE_SWEEP_OUTLINED, on_click=clear_all),
                            ],
                        ),
                    ],
                ),
                ft.Container(expand=True, border_radius=14, padding=10, bgcolor=ft.Colors.SURFACE, content=ft.Column([dt], expand=True)),
            ],
        )

        stats_view = ft.Card(
            elevation=1,
            content=ft.Container(
                padding=18,
                content=ft.Column(
                    spacing=14,
                    controls=[
                        ft.Text("统计汇总（基于历史记录）", size=18, weight=ft.FontWeight.W_700),
                        ft.Container(
                            padding=16,
                            border_radius=14,
                            bgcolor=ft.Colors.SURFACE_CONTAINER,
                            content=ft.Column(
                                spacing=10,
                                controls=[
                                    kv_row("总数量:", st_total_qty),
                                    kv_row("总花费:", st_total_cost),
                                    kv_row("Steam 售出总额(未扣费):", st_total_sell),
                                    kv_row("总到手余额(已扣15%):", st_total_net),
                                    ft.Divider(height=1),
                                    kv_row("整体倒余额比例(花费/到手):", st_ratio),
                                    kv_row("整体折扣:", st_discount),
                                ],
                            ),
                        ),
                        ft.Text("提示：整体折扣=1-（总花费/总到手余额）。例如花 70 得 85，折扣≈17.65%。", opacity=0.8),
                    ],
                ),
            ),
        )

        def toggle_theme(_):
            page.theme_mode = ft.ThemeMode.DARK if page.theme_mode == ft.ThemeMode.LIGHT else ft.ThemeMode.LIGHT
            page.update()

        def switch_view(view_name):
            calc_card.visible = (view_name == "calculator")
            history_view.visible = (view_name == "history")
            stats_view.visible = (view_name == "stats")
            page.update()

        tab_buttons = ft.Row([
            ft.Button(
                "计算器",
                icon=ft.Icons.CALCULATE_OUTLINED,
                on_click=lambda _: switch_view("calculator"),
            ),
            ft.Button(
                "历史",
                icon=ft.Icons.HISTORY,
                on_click=lambda _: switch_view("history"),
            ),
            ft.Button(
                "统计",
                icon=ft.Icons.INSIGHTS_OUTLINED,
                on_click=lambda _: switch_view("stats"),
            ),
        ])

        main_content = ft.Container(
            padding=12,
            content=ft.Column(
                spacing=10,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Row(
                                spacing=10,
                                controls=[ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED),
                                          ft.Text("Steam 倒余额工具箱", size=20, weight=ft.FontWeight.W_700)],
                            ),
                            ft.OutlinedButton("切换明/暗", icon=ft.Icons.DARK_MODE_OUTLINED, on_click=toggle_theme),
                        ],
                    ),
                    tab_buttons,
                    calc_card,
                    history_view,
                    stats_view,
                ],
            ),
        )

        # 替换加载界面为主界面
        page.controls.clear()
        page.add(main_content)

        history_view.visible = False
        stats_view.visible = False
        refresh_history()
        refresh_stats()
        recalc()
        page.update()

    def connect_to_backend():
        """连接后端服务"""
        loading_error.value = ""
        retry_button.visible = False
        loading_text.value = "正在连接后端服务..."
        page.update()

        for attempt in range(5):
            loading_text.value = f"正在连接后端服务... ({attempt + 1}/5)"
            loading_progress.value = (attempt + 1) / 5
            page.update()

            if check_api_connection():
                loading_text.value = "连接成功！正在初始化..."
                loading_progress.value = 1.0
                page.update()
                init_app()
                return

        loading_text.value = "连接失败"
        loading_error.value = "无法连接到后端服务，请确保后端已启动\n服务地址: http://localhost:5000"
        loading_progress.value = 0
        retry_button.visible = True
        page.update()

    def on_retry(_):
        """重试连接"""
        connect_to_backend()

    retry_button.on_click = on_retry

    # 开始连接后端
    connect_to_backend()


if __name__ == "__main__":
    ft.run(main, view=ft.AppView.FLET_APP, port=0)