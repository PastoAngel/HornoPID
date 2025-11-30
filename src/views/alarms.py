# src/views/alarms.py
import flet as ft
import asyncio
from src.utils.theme import AppTheme

class AlarmsView(ft.Container):
    def __init__(self, alarm_manager, page: ft.Page):
        super().__init__()
        self.manager = alarm_manager
        self.page = page
        self.expand = True
        self.padding = 20
        self.ui_running = True 
        
        self.build_ui()
        
        # Iniciamos tarea visual para actualizar el cronómetro
        self.page.run_task(self.update_timer_visuals)

    def did_unmount(self):
        # Detener el bucle visual al salir de la pantalla
        self.ui_running = False

    def build_ui(self):
        # --- INPUTS ---
        self.tf_sp = ft.TextField(
            label="Setpoint", 
            value=str(self.manager.target_sp),
            suffix_text="°C", 
            width=100,
            text_size=14,
            keyboard_type=ft.KeyboardType.NUMBER, 
            border_color="white54",
            color="white",
            cursor_color="white"
        )

        self.tf_minutes = ft.TextField(
            label="Tiempo", 
            value=str(self.manager.initial_minutes),
            suffix_text="min", 
            width=100,
            text_size=14,
            keyboard_type=ft.KeyboardType.NUMBER, 
            border_color="white54",
            color="white",
            cursor_color="white"
        )

        # --- CRONÓMETRO GIGANTE ---
        self.lbl_timer = ft.Text(
            "00:00", 
            size=90, 
            weight="bold", 
            color="white", 
            font_family=AppTheme.font_mono
        )
        
        self.lbl_status = ft.Text("Listo", color="grey", size=16)

        # --- ESTILO DE BOTONES (GHOST / TRANSPARENTES) ---
        ghost_style = ft.ButtonStyle(
            color="white",
            bgcolor=ft.Colors.TRANSPARENT, 
            overlay_color="#22ffffff",     
            side=ft.border.BorderSide(1, "white"),
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=20
        )

        # --- 3 BOTONES ---
        self.btn_on = ft.OutlinedButton(
            "ON", 
            icon=ft.Icons.PLAY_ARROW,
            style=ghost_style,
            on_click=self.handle_on
        )
        
        self.btn_stop = ft.OutlinedButton(
            "STOP", 
            icon=ft.Icons.STOP,
            style=ghost_style,
            on_click=self.handle_stop
        )

        self.btn_delete = ft.OutlinedButton(
            "DELETE", 
            icon=ft.Icons.DELETE_OUTLINE,
            style=ghost_style,
            on_click=self.handle_delete
        )

        # --- CONTENEDOR DEL TIMER ---
        timer_box = ft.Container(
            content=ft.Column(
                [self.lbl_status, self.lbl_timer], 
                horizontal_alignment="center",
                spacing=0
            ),
            # --- CAMBIO REALIZADO: NEGRO SÓLIDO ---
            bgcolor="black", 
            padding=30, 
            border_radius=20,
            border=ft.border.all(1, "white24"), 
            alignment=ft.alignment.center
        )

        # --- LAYOUT PRINCIPAL ---
        self.content = ft.Column(
            [
                ft.Text("Temporizador de Proceso", size=24, weight="bold", color="white"),
                ft.Divider(color="white24"),
                ft.Container(height=10),
                
                # Fila de Inputs
                ft.Row([self.tf_sp, self.tf_minutes], alignment=ft.MainAxisAlignment.CENTER, spacing=20),
                
                ft.Container(height=20),
                timer_box,
                ft.Container(height=30),
                
                # Fila de Botones
                ft.Row([self.btn_on, self.btn_stop, self.btn_delete], alignment=ft.MainAxisAlignment.CENTER, spacing=20)
            ], 
            horizontal_alignment="center"
        )

    # --- LÓGICA DE BOTONES ---

    def handle_on(self, e):
        """Botón ON: Envía SP y arranca el Timer"""
        try:
            sp = float(self.tf_sp.value)
            mins = float(self.tf_minutes.value)
            
            self.manager.start_process(sp, mins)
            
            self.lbl_status.value = f"Ejecutando (SP: {sp}°C)"
            self.lbl_status.color = AppTheme.color_stable
            self.lbl_status.update()
            
            self.show_snack("Proceso INICIADO", "green")
        except ValueError:
            self.show_snack("Error: Revisa los números", "red")

    def handle_stop(self, e):
        """Botón STOP: Detiene el buzzer y la lógica"""
        self.manager.stop_process()
        self.lbl_status.value = "Detenido por usuario"
        self.lbl_status.color = "orange"
        self.update()
        self.show_snack("Proceso DETENIDO", "orange")

    def handle_delete(self, e):
        """Botón DELETE: Detiene y resetea visualmente a 00:00"""
        self.manager.stop_process()
        self.lbl_timer.value = "00:00"
        self.lbl_status.value = "Reset"
        self.lbl_status.color = "grey"
        self.update()
        self.show_snack("Temporizador Borrado", "grey")

    def show_snack(self, msg, color):
        self.page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=color, duration=1000)
        self.page.snack_bar.open = True
        self.page.update()

    async def update_timer_visuals(self):
        """Bucle que actualiza el texto del cronómetro cada 0.2s"""
        while self.ui_running:
            if self.manager.is_running:
                # 1. Obtener segundos restantes reales
                secs_left = self.manager.get_remaining_seconds()
                
                # 2. Formato MM:SS
                m = secs_left // 60
                s = secs_left % 60
                self.lbl_timer.value = f"{m:02d}:{s:02d}"
                
                # 3. Colores de estado
                if secs_left <= 0:
                    self.lbl_timer.color = AppTheme.color_alarm # Rojo
                    self.lbl_status.value = "¡FINALIZADO!"
                    self.lbl_status.color = AppTheme.color_alarm
                else:
                    self.lbl_timer.color = "white"
                    # Mantenemos el status que puso el botón ON

                # 4. Actualizar solo si el control sigue vivo
                if self.lbl_timer.page:
                    self.lbl_timer.update()
                    self.lbl_status.update()
            
            await asyncio.sleep(0.2)