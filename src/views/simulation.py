# src/views/simulation.py
import flet as ft
import asyncio
import time
import random
from src.utils.theme import AppTheme
from src.core.pid_logic import PIDController, ThermalSimulator

class SimulationView(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.page = page
        self.expand = True
        self.padding = 20
        
        # --- MOTOR DE SIMULACIÓN ---
        self.pid = PIDController(kp=2.0, ki=0.1, kd=1.0)
        self.sim = ThermalSimulator()
        
        self.running = True
        self.start_time = time.time()
        
        self.setpoint = 50.0
        self.disturbance = 0.0 
        
        # --- UI ELEMENTS ---
        self.build_ui()
        
        self.page.run_task(self.sim_loop)

    def did_unmount(self):
        self.running = False

    def build_ui(self):
        # 1. GRÁFICA DE RESPUESTA
        self.data_temp = []
        self.data_sp = []

        self.chart = ft.LineChart(
            data_series=[
                # Serie 1: Temperatura (Rojo)
                ft.LineChartData(
                    data_points=self.data_temp,
                    stroke_width=3,
                    color=AppTheme.color_pv,
                    curved=True,
                    stroke_cap_round=True,
                ),
                # Serie 2: Setpoint (Azul)
                ft.LineChartData(
                    data_points=self.data_sp,
                    stroke_width=2,
                    color=AppTheme.color_sp,
                    # stroke_dash_pattern=[5, 5], <--- ELIMINADO: Causa error en tu versión de Flet
                    curved=False
                )
            ],
            min_y=0,
            max_y=100,
            min_x=0,
            max_x=30,
            expand=True,
            border=ft.border.all(1, AppTheme.card_border),
            horizontal_grid_lines=ft.ChartGridLines(interval=10, color="#222222"),
            tooltip_bgcolor="#111111"
        )

        chart_container = ft.Container(
            content=self.chart,
            height=250,
            padding=10,
            bgcolor=AppTheme.card_bgcolor,
            border_radius=15,
            border=ft.border.all(1, AppTheme.card_border)
        )

        # 2. CONTROLES (Sliders)
        self.slider_kp = self._make_slider("Kp (Fuerza)", 0, 20, 2.0, "red")
        self.slider_ki = self._make_slider("Ki (Memoria)", 0, 2.0, 0.1, "green")
        self.slider_kd = self._make_slider("Kd (Freno)", 0, 10, 1.0, "orange")
        self.slider_sp = self._make_slider("Setpoint", 0, 90, 50.0, "blue")

        # 3. BOTONES DE ACCIÓN
        self.btn_disturbance = ft.ElevatedButton(
            "Abrir Puerta (Perturbación)",
            icon=ft.Icons.WIND_POWER,
            style=ft.ButtonStyle(bgcolor="#444444", color="white"),
            on_click=self.trigger_disturbance
        )
        
        self.btn_reset = ft.TextButton(
            "Reiniciar Simulación",
            icon=ft.Icons.REFRESH,
            on_click=self.reset_sim
        )

        # 4. INFO TEXT
        self.lbl_info = ft.Text(
            "Modo Aprendizaje: Ajusta los valores y observa cómo cambia la curva.", 
            size=12, color="grey"
        )

        # ENSAMBLAJE
        self.content = ft.Column(
            controls=[
                ft.Text("Simulador Térmico PID", size=24, weight="bold", color="white"),
                self.lbl_info,
                ft.Container(height=10),
                chart_container,
                ft.Container(height=10),
                # Panel de control
                ft.Container(
                    bgcolor=AppTheme.card_bgcolor,
                    padding=15,
                    border_radius=10,
                    content=ft.Column([
                        self.slider_sp,
                        ft.Divider(color="#333333"),
                        self.slider_kp,
                        self.slider_ki,
                        self.slider_kd
                    ])
                ),
                ft.Container(height=10),
                ft.Row([self.btn_disturbance, self.btn_reset], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            ],
            scroll=ft.ScrollMode.AUTO
        )

    def _make_slider(self, label, min_v, max_v, start_v, color):
        return ft.Column([
            ft.Row([
                ft.Text(label, size=14, weight="bold"),
                ft.Container(expand=True),
                ft.Text(f"{start_v:.1f}", size=14, font_family=AppTheme.font_mono)
            ]),
            ft.Slider(
                min=min_v, max=max_v, divisions=100, 
                value=start_v, 
                active_color=color,
                on_change=self.on_slider_change
            )
        ], spacing=0)

    # --- LÓGICA ---

    def on_slider_change(self, e):
        self.pid.kp = self.slider_kp.controls[1].value
        self.pid.ki = self.slider_ki.controls[1].value
        self.pid.kd = self.slider_kd.controls[1].value
        self.setpoint = self.slider_sp.controls[1].value
        
        self.slider_kp.controls[0].controls[2].value = f"{self.pid.kp:.1f}"
        self.slider_ki.controls[0].controls[2].value = f"{self.pid.ki:.2f}"
        self.slider_kd.controls[0].controls[2].value = f"{self.pid.kd:.1f}"
        self.slider_sp.controls[0].controls[2].value = f"{self.setpoint:.1f}°C"
        
        self.page.update()

    def trigger_disturbance(self, e):
        self.sim.temperature -= 15.0 
        self.page.snack_bar = ft.SnackBar(ft.Text("¡Aire frío detectado!"), bgcolor="blue")
        self.page.snack_bar.open = True
        self.page.update()

    def reset_sim(self, e):
        self.sim.temperature = 25.0
        self.pid.reset()
        self.data_temp.clear()
        self.data_sp.clear()
        self.start_time = time.time()
        self.page.update()

    async def sim_loop(self):
        """Bucle de física acelerada"""
        while self.running:
            now = time.time()
            elapsed = now - self.start_time
            
            self.pid.setpoint = self.setpoint
            output_pwm = self.pid.compute(self.sim.temperature)
            
            # Física
            current_temp = self.sim.update(output_pwm, dt=0.1)
            
            # Graficar
            self.data_temp.append(ft.LineChartDataPoint(x=elapsed, y=current_temp))
            self.data_sp.append(ft.LineChartDataPoint(x=elapsed, y=self.setpoint))
            
            if elapsed > 30:
                self.chart.min_x = elapsed - 30
                self.chart.max_x = elapsed
                if len(self.data_temp) > 300:
                    self.data_temp.pop(0)
                    self.data_sp.pop(0)
            else:
                self.chart.max_x = 30
                
            if self.chart.page:
                self.chart.update()
            else:
                # Si no hay página, es seguro asumir que debemos detener el loop
                self.running = False
                break 
            
            await asyncio.sleep(0.1)