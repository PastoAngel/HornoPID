# src/main.py
import flet as ft
import random
import asyncio
import time
from src.utils.theme import AppTheme
from src.core.esp_interface import ESP32Interface
from src.core.updater import check_for_updates
# --- IMPORTS CORE ---
from src.core.alarm_manager import AlarmManager
from src.core.data_store import DataStore
from src.core.tuner import StepResponseAnalyzer

# --- IMPORTS VISTAS ---
from src.views.alarms import AlarmsView
from src.views.dashboard import DashboardView
from src.views.tuning import TuningView
from src.views.settings import SettingsView

# --- IMPORTS COMPONENTES ---
from src.components.sidebar import AnimatedSidebar
from src.components.topbar import TopBar

def main(page: ft.Page):
    # --- 1. CONFIGURACIÓN GLOBAL ---
    page.title = "PID Control Suite"
    page.padding = 0
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#000000"
    page.scroll = None
    page.keep_screen_on = True

    page.fonts = {
        "Roboto Mono": "https://github.com/google/fonts/raw/main/apache/robotomono/RobotoMono-Regular.ttf"
    }

    # --- 2. INICIALIZAR NÚCLEO ---
    esp_interface = ESP32Interface()
    app_data = DataStore()
    
    # --- NUEVO: TUNER GLOBAL (Persistencia) ---
    global_tuner = StepResponseAnalyzer()

    # Placeholder
    topbar = None

    def on_alarm_trigger_callback():
        if topbar: topbar.add_notification("¡Tiempo Finalizado!")
        try:
            page.snack_bar = ft.SnackBar(
                content=ft.Text("¡TIEMPO FINALIZADO!", weight="bold"),
                bgcolor=AppTheme.color_alarm, duration=5000
            )
            page.snack_bar.open = True
            page.update()
        except: pass

    alarm_manager = AlarmManager(page, esp_interface, on_alarm_trigger_callback)

    # --- 3. FONDO AURORA ---
    center_x = random.uniform(-0.1, 0.5)
    ambient_background = ft.Container(
        expand=True,
        bgcolor=None,
        gradient=ft.RadialGradient(
            center=ft.Alignment(center_x, -0.8),
            radius=1.8,
            colors=[
                "#2d0835", # Morado Aurora
                "#0d1021", # Azul Noche
                "#000000", # Negro
            ],
            stops=[0.0, 0.35, 0.7]
        )
    )

    # --- 4. CONTENEDOR DE CONTENIDO ---
    content_container = ft.Container(
        expand=True,
        bgcolor=None, 
        padding=ft.padding.only(top=70, left=72, right=20, bottom=20),
        animate=ft.Animation(300, "decelerate")
    )

    content_view = ft.Column(expand=True, scroll="auto")

    # --- 5. NAVEGACIÓN ---
    def navigate(route_name):
        content_view.controls.clear()

        if route_name == "dashboard":
            content_view.controls.append(DashboardView(esp_interface, page, app_data))
        
        elif route_name == "graphs":
            # Pasamos la instancia global para ver datos en tiempo real sin reiniciar
            content_view.controls.append(TuningView(esp_interface, page, global_tuner))
        
        elif route_name == "alarms":
            content_view.controls.append(AlarmsView(alarm_manager, page))
        
        elif route_name == "settings":
            content_view.controls.append(SettingsView(esp_interface, page))
        
        elif route_name == "logout":
            # Seguridad: Apagar tuning si salimos de la app
            if global_tuner.recording:
                esp_interface.send_auto_tune_cmd(False)
            
            esp_interface.disconnect()
            page.window.close()
            return

        if content_view.page:
            content_view.update()

    content_container.content = content_view

    # --- 6. COMPONENTES DE UI ---
    sidebar = AnimatedSidebar(page, on_nav_change=navigate)

    def toggle_sidebar_action(e):
        sidebar.toggle_sidebar()

    topbar = TopBar(page, on_nav_toggle=toggle_sidebar_action)

    overlay = ft.Container(
        bgcolor="#80000000", 
        expand=True,
        visible=False,
        opacity=0,
        animate_opacity=300,
        on_click=lambda e: sidebar.toggle_sidebar(False)
    )

    # --- 7. LÓGICA RESPONSIVA ---
    def handle_sidebar_resize(new_width):
        is_mobile = page.width < 800
        is_open = new_width > sidebar.min_width

        if is_mobile:
            content_container.padding.left = 72
            if is_open:
                overlay.visible = True
                overlay.opacity = 1
                sidebar.set_solid_background(True)
            else:
                overlay.opacity = 0
                overlay.visible = False
                sidebar.set_solid_background(False)
        else:
            content_container.padding.left = new_width
            overlay.opacity = 0
            overlay.visible = False
            sidebar.set_solid_background(False)

        content_container.update()
        overlay.update()

    sidebar.on_width_change = handle_sidebar_resize

    # --- 8. TAREA GLOBAL (CENTRALIZADA) ---
    async def global_monitoring_loop():
        while True:
            try:
                # A) Gestión de Conexión
                if not esp_interface.connected and esp_interface.auto_reconnect:
                    if int(time.time()) % 5 == 0: esp_interface.attempt_reconnect()
                
                # B) Lectura UNIFICADA de Telemetría
                if esp_interface.connected:
                    telemetry = esp_interface.read_telemetry()
                    
                    if telemetry:
                        t_now = time.time()
                        temp = float(telemetry.get('temp', 0))
                        sp = float(telemetry.get('sp', 0))
                        out = int(telemetry.get('out', 0))
                        
                        # 1. Alimentar Dashboard (CORREGIDO: SE PASA EL VALOR 'out')
                        if app_data.start_time is None: app_data.start_time = t_now
                        elapsed = t_now - app_data.start_time
                        app_data.add_data(elapsed, temp, sp, power=out)

                        # 2. Alimentar Tuner (Siempre actualizamos live data para el dimmer)
                        global_tuner.update_live_data(temp, out)

                        # 3. SEGURIDAD: Límite 80°C durante Tuning
                        if global_tuner.recording:
                            if temp >= 80.0:
                                print(f"[Safety] Temp {temp}°C > 80°C. Abortando Tuning.")
                                global_tuner.stop_recording()
                                esp_interface.send_auto_tune_cmd(False)
                                
                                page.snack_bar = ft.SnackBar(
                                    content=ft.Text("¡PARADA EMERGENCIA! Temp > 80°C"),
                                    bgcolor="red"
                                )
                                page.snack_bar.open = True
                                page.update()

                # C) Chequeo de Alarmas
                alarm_manager.check_status()

            except Exception as e:
                print(f"Error loop global: {e}")
            
            # Frecuencia de muestreo global (0.5s es suficiente)
            await asyncio.sleep(0.5)

    page.run_task(global_monitoring_loop)

    # --- TAREA DE ACTUALIZACIÓN (NUEVO) ---
    async def run_update_check():
        # Esperamos 2 segundos para que la UI cargue primero y no se sienta lento
        await asyncio.sleep(2)
        try:
            # Consultamos GitHub
            check_for_updates(page)
        except Exception as e:
            print(f"Error checking updates: {e}")

    page.run_task(run_update_check)

    # --- 9. ARRANQUE ---
    navigate("dashboard")

    page.add(
        ft.Stack(
            controls=[
                ambient_background,
                content_container,
                overlay,
                ft.Container(content=sidebar, top=0, left=0, bottom=0),
                topbar
            ],
            expand=True
        )
    )

    def handle_page_resize(e):
        handle_sidebar_resize(sidebar.width)
        if page.width < 600 and sidebar.is_open_flag:
            sidebar.toggle_sidebar(False)

    page.on_resized = handle_page_resize
    page.update()

if __name__ == "__main__":
    ft.app(target=main)