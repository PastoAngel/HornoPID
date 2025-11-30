# src/components/sidebar.py
import flet as ft
from src.utils.theme import AppTheme

class SidebarItem(ft.Container):
    def __init__(self, icon, title, page_ref, on_click_func, nav_data):
        super().__init__()
        self.page_ref = page_ref
        self.on_click = on_click_func
        self.data = nav_data
        
        self.content_text = ft.Text(title, size=14, weight="bold", opacity=0, no_wrap=True)
        
        self.content = ft.Row(
            controls=[
                ft.Icon(icon, size=24),
                self.content_text
            ]
        )
        self.padding = ft.padding.only(left=15, top=10, bottom=10)
        self.border_radius = 10
        self.on_hover = self.highlight_item
        self.animate = ft.Animation(200, "decelerate")

    def highlight_item(self, e):
        # Highlight sutil
        highlight = "#1AFFFFFF" 
        self.bgcolor = highlight if e.data == "true" else None
        self.update()

class AnimatedSidebar(ft.Container):
    def __init__(self, page: ft.Page, on_nav_change, on_width_change=None):
        super().__init__()
        self.page = page
        self.on_nav_change = on_nav_change
        self.on_width_change = on_width_change
        
        # --- CONFIGURACIÓN ---
        self.min_width = 72
        self.max_width = 280 
        self.is_open_flag = False 
        
        self.width = self.min_width 
        self.expand = False 
        
        # --- ESTILO INICIAL ---
        self.bgcolor = "transparent" 
        self.gradient = None
        
        # Borde sutil a la derecha
        self.border = ft.border.only(
            right=ft.border.BorderSide(1, "#1AFFFFFF")
        )
        
        self.padding = 0
        self.animate = ft.Animation(300, "decelerate")

        # Items
        self.items = [
            SidebarItem(ft.Icons.DASHBOARD, "Dashboard", page, self.handle_nav_click, "dashboard"),
            SidebarItem(ft.Icons.ANALYTICS, "Sintonización", page, self.handle_nav_click, "graphs"),
            SidebarItem(ft.Icons.TIMER, "Alarmas", page, self.handle_nav_click, "alarms"),
            SidebarItem(ft.Icons.SETTINGS, "Ajustes", page, self.handle_nav_click, "settings"),
        ]
        
        # --- CORRECCIÓN AQUÍ: page.window.close() ---
        self.logout_item = SidebarItem(ft.Icons.LOGOUT, "Salir", page, lambda e: page.window.close(), "logout")

        self.inner_column = ft.Column(
            controls=[
                ft.Container(height=70), 
                *self.items,
                ft.Container(expand=True),
                self.logout_item,
                ft.Container(height=20)
            ],
            scroll=None,
            spacing=5
        )

        self.content = ft.GestureDetector(
            on_pan_start=self.drag_start,
            on_pan_update=self.drag_update,
            on_pan_end=self.drag_end,
            content=ft.Container(
                content=self.inner_column,
                bgcolor="transparent",
                padding=ft.padding.symmetric(horizontal=10),
                expand=True 
            )
        )

    def handle_nav_click(self, e):
        self.on_nav_change(e.control.data)

    # --- LÓGICA VISUAL (FONDO AURORA EXACTO) ---
    def set_solid_background(self, make_solid: bool):
        """
        Controla la visibilidad del fondo del sidebar.
        """
        if make_solid:
            # Fondo base de seguridad
            self.bgcolor = "#000000" 
            
            # COPIA EXACTA DEL GRADIENTE DE MAIN.PY
            self.gradient = ft.RadialGradient(
                center=ft.Alignment(0.0, -0.8), # Foco arriba al centro
                radius=1.6, 
                colors=[
                    "#1a0525", # Morado Ultra Oscuro (Foco)
                    "#050814", # Azul Noche (Halo)
                    "#000000", # Negro (Fondo)
                ],
                stops=[0.0, 0.25, 0.6] # Corte agresivo a negro
            )
        else:
            # Modo transparente
            self.gradient = None
            self.bgcolor = "transparent"
            
        self.update()

    def toggle_sidebar(self, expand: bool = None):
        if expand is None:
            expand = not self.is_open_flag
            
        self.width = self.max_width if expand else self.min_width
        self.is_open_flag = expand
        
        final_opacity = 1 if expand else 0
        self.update_text_opacity(final_opacity)
        
        self.update()
        
        if self.on_width_change:
            self.on_width_change(self.width)

    def update_text_opacity(self, opacity):
        for item in self.items:
            item.content_text.opacity = opacity
            item.update()
        self.logout_item.content_text.opacity = opacity
        self.logout_item.update()

    # --- Gestos ---
    def drag_start(self, e):
        self.animate = None 
        self.update()

    def drag_update(self, e: ft.DragUpdateEvent):
        new_width = self.width + e.delta_x
        if new_width < self.min_width: new_width = self.min_width
        if new_width > self.max_width: new_width = self.max_width
        self.width = new_width
        
        progress = (self.width - self.min_width) / (self.max_width - self.min_width)
        text_opacity = max(0, min(1, (progress - 0.3) * 2)) 
        self.update_text_opacity(text_opacity)
        
        self.update()
        
        if self.on_width_change:
            self.on_width_change(self.width)

    def drag_end(self, e):
        self.animate = ft.Animation(300, "decelerate")
        threshold = (self.max_width + self.min_width) / 2
        final_state = self.width > threshold
        self.toggle_sidebar(final_state)

    def update_theme(self):
        self.update()