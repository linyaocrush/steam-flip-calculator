import flet as ft


def create_loading_view(on_retry):
    loading_text = ft.Text("正在连接后端服务...", size=16)
    loading_progress = ft.ProgressBar(width=400, color=ft.Colors.INDIGO)
    loading_error = ft.Text("", size=14, color=ft.Colors.RED)
    retry_button = ft.Button("重试连接", icon=ft.Icons.REFRESH, visible=False)
    
    retry_button.on_click = on_retry

    loading_view = ft.Column(
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=20,
        controls=[
            ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED, size=64, color=ft.Colors.INDIGO),
            ft.Text("Steam 倒余额工具箱", size=24, weight=ft.FontWeight.W_700),
            loading_progress,
            loading_text,
            loading_error,
            retry_button,
        ],
    )

    return {
        "view": loading_view,
        "loading_text": loading_text,
        "loading_progress": loading_progress,
        "loading_error": loading_error,
        "retry_button": retry_button,
    }