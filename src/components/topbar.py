# src/components/topbar.py
import flet as ft
from datetime import datetime
from src.utils.theme import AppTheme

class TopBar(ft.Container):
    def __init__(self, page: ft.Page, on_nav_toggle):
        super().__init__()
        self.page = page
        self.on_nav_toggle = on_nav_toggle
        
        # --- LISTA DE HISTORIAL ---
        self.notification_log = []
        
        # --- CONFIGURACIÓN VISUAL ---
        self.bgcolor = None 
        self.height = 60
        self.padding = ft.padding.only(left=15, right=15)
        
        # --- CONTROLES IZQUIERDA ---
        self.menu_btn = ft.IconButton(
            icon=ft.Icons.MENU,
            icon_size=24,
            icon_color="white",
            on_click=self.trigger_menu_toggle,
            tooltip="Menú"
        )

        self.app_title = ft.Text(
            "Dashboard PID", 
            size=20, 
            weight="bold",
            color="white"
        )

        # --- CONTROLES DERECHA (NOTIFICACIONES) ---
        self.bell_icon = ft.IconButton(
            icon=ft.Icons.NOTIFICATIONS_NONE,
            icon_size=24,
            icon_color="white",
            on_click=self.show_notifications
        )
        
        # Punto Rojo (Badge)
        self.badge = ft.Container(
            width=10, height=10,
            bgcolor=AppTheme.color_alarm, # Rojo
            border_radius=5,
            visible=False,
            border=ft.border.all(1, "black")
        )

        self.notification_stack = ft.Stack(
            controls=[
                self.bell_icon,
                ft.Container(content=self.badge, right=5, top=5)
            ]
        )

        # --- LAYOUT PRINCIPAL ---
        self.content = ft.Row(
            controls=[
                # Izquierda
                ft.Row([self.menu_btn, ft.Container(width=10), self.app_title]),
                
                # Espaciador
                ft.Container(expand=True), 
                
                # Derecha
                self.notification_stack
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )

    def trigger_menu_toggle(self, e):
        self.on_nav_toggle(e)

    # --- LÓGICA DE NOTIFICACIONES ---

    def add_notification(self, message="Evento del Sistema"):
        """Agrega un mensaje al historial y prende la campana"""
        
        # Marca de tiempo
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_msg = f"[{timestamp}] {message}"
        
        # Agregar al inicio de la lista (LIFO)
        self.notification_log.insert(0, full_msg)
        
        # Activar indicador visual
        self.bell_icon.icon = ft.Icons.NOTIFICATIONS_ACTIVE
        self.bell_icon.icon_color = AppTheme.color_alarm # Cambia a rojo
        self.badge.visible = True
        self.update()

    def show_notifications(self, e):
        """Muestra el historial en un Dialog"""
        
        # Apagar indicador de "Nuevo"
        self.badge.visible = False
        self.bell_icon.icon = ft.Icons.NOTIFICATIONS_NONE
        self.bell_icon.icon_color = "white"
        self.update()
        
        # Construir contenido del Dialog
        if not self.notification_log:
            content = ft.Text("No hay notificaciones recientes.", color="grey", italic=True)
            actions = [ft.TextButton("Cerrar", on_click=self.close_dialog)]
        else:
            # Lista scrolleable de mensajes
            msg_list_controls = []
            for msg in self.notification_log:
                msg_list_controls.append(
                    ft.Container(
                        content=ft.Text(msg, size=14, color="white"),
                        padding=10,
                        border=ft.border.only(bottom=ft.border.BorderSide(1, "#333333"))
                    )
                )
            
            content = ft.Column(
                controls=msg_list_controls,
                height=300, # Altura máxima antes de scroll
                scroll=ft.ScrollMode.AUTO
            )
            
            actions = [
                ft.TextButton("Borrar Todo", icon=ft.Icons.DELETE_SWEEP, 
                              style=ft.ButtonStyle(color="red"), 
                              on_click=self.clear_history),
                ft.TextButton("Cerrar", on_click=self.close_dialog)
            ]

        # Mostrar Dialog
        self.dlg = ft.AlertDialog(
            title=ft.Text("Centro de Notificaciones"),
            content=content,
            actions=actions,
            bgcolor="#1a1a1a",
            shape=ft.RoundedRectangleBorder(radius=10)
        )
        self.page.dialog = self.dlg
        self.dlg.open = True
        self.page.update()

    def clear_history(self, e):
        self.notification_log.clear()
        self.close_dialog(e)
        
        self.page.snack_bar = ft.SnackBar(ft.Text("Historial borrado"))
        self.page.snack_bar.open = True
        self.page.update()

    def close_dialog(self, e):
        self.dlg.open = False
        self.page.update()