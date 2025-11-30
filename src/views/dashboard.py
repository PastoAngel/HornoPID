# src/views/dashboard.py
import flet as ft
import asyncio
import time
import csv
import datetime
from src.utils.theme import AppTheme
from src.components.kpi_card import KPICard
from src.utils.validators import InputValidator

class DashboardView(ft.Container):
    def __init__(self, esp_interface, page: ft.Page, data_store):
        super().__init__()
        self.esp = esp_interface
        self.page = page
        self.data_store = data_store
        self.expand = True
        self.padding = 10
        
        self.running = True
        
        # Gestor de archivos
        self.file_picker = ft.FilePicker(on_result=self.handle_save_csv)
        self.page.overlay.append(self.file_picker)
        self.page.update()

        self.build_ui()
        self.page.run_task(self.update_loop)

    def did_unmount(self):
        self.running = False

    def build_ui(self):
        # 1. TARJETAS KPI
        self.card_temp = KPICard(ft.Icons.THERMOSTAT, "TEMP ACTUAL", "--", "°C", AppTheme.color_pv)
        self.card_sp = KPICard(ft.Icons.FLAG, "SETPOINT", "--", "°C", AppTheme.color_sp)
        # Nota: La potencia requiere que main.py inyecte 'latest_out' en data_store
        self.card_out = KPICard(ft.Icons.ELECTRIC_BOLT, "POTENCIA", "--", "%", AppTheme.color_mv)

        kpi_row = ft.ResponsiveRow(
            controls=[
                ft.Column([self.card_temp], col={"xs": 6, "md": 4}),
                ft.Column([self.card_sp],   col={"xs": 6, "md": 4}),
                ft.Column([self.card_out],  col={"xs": 12, "md": 4}),
            ],
            run_spacing=5
        )

        # 2. PANEL DE CONTROL (LIMITADO A 80°C)
        self.input_sp = ft.TextField(
            value="0", width=80, text_size=16, content_padding=10,
            suffix_text="°", border_color=AppTheme.color_sp, 
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=self.sync_slider_from_input
        )

        self.slider_sp = ft.Slider(
            min=0, max=80, divisions=80, value=0, # <--- CAMBIO: Max 80
            active_color=AppTheme.color_sp, 
            on_change=self.sync_input_from_slider
        )
        
        self.btn_apply = ft.IconButton(
            icon=ft.Icons.SEND_ROUNDED, 
            icon_color="black",
            style=ft.ButtonStyle(bgcolor=AppTheme.color_sp), 
            tooltip="Enviar Temperatura",
            on_click=self.handle_apply_sp
        )

        control_panel = ft.Container(
            bgcolor=AppTheme.card_bgcolor, 
            border_radius=10, 
            padding=ft.padding.symmetric(horizontal=15, vertical=10),
            border=ft.border.all(1, AppTheme.card_border),
            content=ft.Column([
                ft.Text("Control de Temperatura (Máx 80°C)", size=14, color="grey", weight="bold"),
                ft.Row([
                    ft.Container(content=self.slider_sp, expand=True), 
                    self.input_sp, 
                    self.btn_apply
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            ], spacing=5)
        )

        # 3. GRÁFICA
        self.chart = ft.LineChart(
            data_series=[
                ft.LineChartData(
                    data_points=self.data_store.data_temp, 
                    stroke_width=3, color=AppTheme.color_pv, 
                    curved=True, stroke_cap_round=True,
                    below_line_bgcolor=f"#1A{AppTheme.color_pv.lstrip('#')}" 
                ),
                ft.LineChartData(
                    data_points=self.data_store.data_sp,
                    stroke_width=2, color=AppTheme.color_sp, 
                    curved=False
                )
            ],
            min_y=0, max_y=100, min_x=0, max_x=60,
            expand=True, 
            border=ft.border.all(1, AppTheme.card_border),
            horizontal_grid_lines=ft.ChartGridLines(interval=10, color="#222222"),
            vertical_grid_lines=ft.ChartGridLines(interval=10, color="#222222"),
            tooltip_bgcolor="#111111", 
            interactive=False 
        )

        self.btn_export = ft.IconButton(
            icon=ft.Icons.DOWNLOAD, 
            icon_color="green", 
            tooltip="Exportar CSV",
            on_click=self.trigger_export
        )
        
        self.btn_clear_chart = ft.IconButton(
            icon=ft.Icons.DELETE_SWEEP, 
            icon_color="red", 
            tooltip="Borrar Historial",
            on_click=self.handle_clear_chart
        )

        chart_header = ft.Row(
            [
                ft.Text("Historial Térmico", size=16, weight="bold", color="white"), 
                ft.Row([self.btn_export, self.btn_clear_chart])
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )

        chart_container = ft.Container(
            content=ft.Column([chart_header, ft.Container(content=self.chart, expand=True)]),
            expand=True, 
            padding=10, 
            bgcolor=AppTheme.card_bgcolor,
            border_radius=10, 
            border=ft.border.all(1, AppTheme.card_border)
        )

        self.content = ft.Column(
            controls=[
                ft.Text("Dashboard", size=20, weight="bold", color="white"),
                kpi_row, 
                ft.Container(height=5), 
                control_panel, 
                ft.Container(height=5), 
                chart_container
            ], 
            spacing=5, 
            expand=True
        )

    # --- LÓGICA ---

    def sync_input_from_slider(self, e):
        self.input_sp.value = str(int(e.control.value))
        self.input_sp.update()

    def sync_slider_from_input(self, e):
        try:
            val = float(e.control.value)
            if 0 <= val <= 80: # <--- CAMBIO: Max 80
                self.slider_sp.value = val
                self.slider_sp.update()
        except: pass

    def handle_apply_sp(self, e):
        # <--- CAMBIO: Validación segura hasta 80
        val = InputValidator.validate_float(self.input_sp, 0, 80)
        if val is not None:
            success = self.esp.send_setpoint_only(val)
            if success:
                self.page.snack_bar = ft.SnackBar(ft.Text(f"Setpoint: {val}°C"), bgcolor="green")
            else:
                self.page.snack_bar = ft.SnackBar(ft.Text("Error comunicación"), bgcolor="red")
            self.page.snack_bar.open = True
            self.page.update()

    def handle_clear_chart(self, e):
        self.data_store.clear_data()
        self.data_store.start_time = time.time()
        self.chart.update()
        self.page.snack_bar = ft.SnackBar(ft.Text("Gráfica reiniciada"), bgcolor="orange")
        self.page.snack_bar.open = True
        self.page.update()

    def trigger_export(self, e):
        filename = f"horno_pid_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        self.file_picker.save_file(file_name=filename, allowed_extensions=["csv"])

    def handle_save_csv(self, e: ft.FilePickerResultEvent):
        if e.path:
            try:
                full_temps, full_sps = self.data_store.get_export_data()
                with open(e.path, mode='w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(["Tiempo (s)", "Temperatura (°C)", "Setpoint (°C)"])
                    for i in range(len(full_temps)):
                        t_val = full_temps[i][0]
                        temp_val = full_temps[i][1]
                        sp_val = 0
                        if i < len(full_sps): sp_val = full_sps[i][1]
                        writer.writerow([f"{t_val:.2f}", f"{temp_val:.2f}", f"{sp_val:.2f}"])
                self.page.snack_bar = ft.SnackBar(ft.Text(f"Guardado: {e.path}"), bgcolor="green")
            except Exception as ex:
                self.page.snack_bar = ft.SnackBar(ft.Text(f"Error: {str(ex)}"), bgcolor="red")
            self.page.snack_bar.open = True
            self.page.update()

    # --- BUCLE VISUAL PASIVO ---
    async def update_loop(self):
        """
        Lee de DataStore (llenado por main.py) para no crear conflicto de sockets.
        """
        while self.running:
            # Verificamos si hay datos en la lista visual
            if self.data_store.data_temp:
                # Obtenemos los últimos valores registrados
                latest_temp_point = self.data_store.data_temp[-1]
                latest_sp_point = self.data_store.data_sp[-1]
                
                temp = latest_temp_point.y
                sp = latest_sp_point.y
                elapsed = latest_temp_point.x

                if self.chart.page:
                    self.card_temp.set_value(temp)
                    self.card_sp.set_value(sp)
                    
                    # --- ACTUALIZACIÓN DE POTENCIA ---
                    # Leemos la última potencia guardada en DataStore
                    self.card_out.set_value(self.data_store.last_power)
                    
                    # Scroll de Gráfica
                    if elapsed > 60:
                        self.chart.min_x = elapsed - 60
                        self.chart.max_x = elapsed
                    else:
                        self.chart.max_x = 60
                    
                    # Autoescala Y
                    current_max = max(temp, sp)
                    if current_max > self.chart.max_y - 5: 
                        self.chart.max_y = current_max + 20
                    
                    self.chart.update()
                    self.card_temp.update()
                    self.card_out.update() # Asegurar actualización visual
            
            await asyncio.sleep(0.5)