import flet as ft


def get_glassmorphism_style(is_dark=False):
    """获取毛玻璃效果样式"""
    if is_dark:
        return {
            "bgcolor": ft.Colors.with_opacity(0.15, ft.Colors.BLACK),
            "blur": 20,
            "border": ft.BorderSide(1, ft.Colors.with_opacity(0.2, ft.Colors.WHITE)),
            "shadow": ft.BoxShadow(
                blur_radius=30,
                spread_radius=0,
                color=ft.Colors.with_opacity(0.3, ft.Colors.BLACK),
                offset=ft.Offset(0, 10),
            ),
        }
    else:
        return {
            "bgcolor": ft.Colors.with_opacity(0.6, ft.Colors.WHITE),
            "blur": 20,
            "border": ft.BorderSide(1, ft.Colors.with_opacity(0.3, ft.Colors.WHITE)),
            "shadow": ft.BoxShadow(
                blur_radius=30,
                spread_radius=0,
                color=ft.Colors.with_opacity(0.15, ft.Colors.BLACK),
                offset=ft.Offset(0, 10),
            ),
        }


def create_glass_container(content, border_radius=16, padding=16, is_dark=False):
    """创建毛玻璃容器"""
    style = get_glassmorphism_style(is_dark)
    
    return ft.Container(
        content=content,
        border_radius=border_radius,
        padding=padding,
        bgcolor=style["bgcolor"],
        border=style["border"],
        shadow=style["shadow"],
    )


def create_gradient_background(is_dark=False):
    """创建渐变背景"""
    if is_dark:
        return ft.Container(
            width=float("inf"),
            height=float("inf"),
            gradient=ft.LinearGradient(
                begin=ft.Alignment(-1, -1),
                end=ft.Alignment(1, 1),
                colors=[
                    "#1a1a2e",
                    "#16213e",
                    "#0f3460",
                    "#1a1a2e",
                ],
                stops=[0.0, 0.3, 0.7, 1.0],
            ),
        )
    else:
        return ft.Container(
            width=float("inf"),
            height=float("inf"),
            gradient=ft.LinearGradient(
                begin=ft.Alignment(-1, -1),
                end=ft.Alignment(1, 1),
                colors=[
                    "#667eea",
                    "#764ba2",
                    "#f093fb",
                    "#f5576c",
                ],
                stops=[0.0, 0.3, 0.7, 1.0],
            ),
        )


def create_floating_orbs(is_dark=False):
    """创建浮动装饰球体"""
    if is_dark:
        colors = [
            ft.Colors.with_opacity(0.15, ft.Colors.PURPLE),
            ft.Colors.with_opacity(0.12, ft.Colors.BLUE),
            ft.Colors.with_opacity(0.1, ft.Colors.CYAN),
            ft.Colors.with_opacity(0.08, ft.Colors.PINK),
        ]
    else:
        colors = [
            ft.Colors.with_opacity(0.25, ft.Colors.PURPLE),
            ft.Colors.with_opacity(0.2, ft.Colors.PINK),
            ft.Colors.with_opacity(0.15, ft.Colors.BLUE),
            ft.Colors.with_opacity(0.1, ft.Colors.CYAN),
        ]
    
    orbs = []
    
    orb_configs = [
        {"width": 300, "height": 300, "left": -100, "top": -100, "color": colors[0]},
        {"width": 250, "height": 250, "right": -80, "top": 100, "color": colors[1]},
        {"width": 200, "height": 200, "left": 50, "bottom": -50, "color": colors[2]},
        {"width": 180, "height": 180, "right": 100, "bottom": -80, "color": colors[3]},
    ]
    
    for config in orb_configs:
        orb = ft.Container(
            width=config["width"],
            height=config["height"],
            bgcolor=config["color"],
            border_radius=config["width"] // 2,
            animate_position=1000,
            animate_scale=1000,
        )
        
        if "left" in config:
            orb.left = config["left"]
        if "right" in config:
            orb.right = config["right"]
        if "top" in config:
            orb.top = config["top"]
        if "bottom" in config:
            orb.bottom = config["bottom"]
        
        orbs.append(orb)
    
    return ft.Stack(
        orbs,
        width=float("inf"),
        height=float("inf"),
        expand=True,
    )


def create_glass_button(text, icon=None, on_click=None, is_dark=False, is_filled=False):
    """创建毛玻璃按钮"""
    style = get_glassmorphism_style(is_dark)
    
    if is_filled:
        button = ft.FilledButton(
            content=ft.Text(text),
            icon=icon,
            on_click=on_click,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.with_opacity(0.8, ft.Colors.INDIGO if is_dark else ft.Colors.PURPLE),
                color=ft.Colors.WHITE,
                padding=16,
                shape=ft.RoundedRectangleBorder(radius=12),
            ),
        )
    else:
        button = ft.OutlinedButton(
            content=ft.Text(text),
            icon=icon,
            on_click=on_click,
            style=ft.ButtonStyle(
                side=ft.BorderSide(1, ft.Colors.with_opacity(0.3, ft.Colors.WHITE if is_dark else ft.Colors.BLACK)),
                padding=16,
                shape=ft.RoundedRectangleBorder(radius=12),
            ),
        )
    
    return button


def create_glass_card(content, is_dark=False, elevation=2):
    """创建毛玻璃卡片"""
    style = get_glassmorphism_style(is_dark)
    
    if elevation == 1:
        shadow = ft.BoxShadow(
            blur_radius=20,
            spread_radius=0,
            color=ft.Colors.with_opacity(0.2 if is_dark else 0.1, ft.Colors.BLACK),
            offset=ft.Offset(0, 5),
        )
    elif elevation == 2:
        shadow = ft.BoxShadow(
            blur_radius=30,
            spread_radius=0,
            color=ft.Colors.with_opacity(0.3 if is_dark else 0.15, ft.Colors.BLACK),
            offset=ft.Offset(0, 10),
        )
    else:
        shadow = ft.BoxShadow(
            blur_radius=40,
            spread_radius=0,
            color=ft.Colors.with_opacity(0.4 if is_dark else 0.2, ft.Colors.BLACK),
            offset=ft.Offset(0, 15),
        )
    
    return ft.Container(
        content=content,
        border_radius=16,
        padding=16,
        bgcolor=style["bgcolor"],
        border=style["border"],
        shadow=shadow,
    )


def create_glass_text_field(label, value="", prefix=None, keyboard_type=None, expand=True, width=None, hint_text=None, is_dark=False):
    """创建毛玻璃文本框"""
    style = get_glassmorphism_style(is_dark)
    
    return ft.TextField(
        label=label,
        value=value,
        prefix=prefix,
        keyboard_type=keyboard_type,
        expand=expand,
        width=width,
        hint_text=hint_text,
        filled=True,
        bgcolor=ft.Colors.with_opacity(0.3 if is_dark else 0.5, ft.Colors.SURFACE),
        border_color=ft.Colors.with_opacity(0.2, ft.Colors.WHITE if is_dark else ft.Colors.BLACK),
        focused_border_color=ft.Colors.with_opacity(0.5, ft.Colors.INDIGO),
        border_radius=12,
        content_padding=12,
    )


def create_glass_dropdown(label, options, value, expand=True, width=None, is_dark=False):
    """创建毛玻璃下拉框"""
    style = get_glassmorphism_style(is_dark)
    
    return ft.Dropdown(
        label=label,
        options=options,
        value=value,
        expand=expand,
        width=width,
        filled=True,
        bgcolor=ft.Colors.with_opacity(0.3 if is_dark else 0.5, ft.Colors.SURFACE),
        border_color=ft.Colors.with_opacity(0.2, ft.Colors.WHITE if is_dark else ft.Colors.BLACK),
        focused_border_color=ft.Colors.with_opacity(0.5, ft.Colors.INDIGO),
        border_radius=12,
        content_padding=12,
    )