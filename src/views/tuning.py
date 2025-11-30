# src/views/tuning.py
import flet as ft
import asyncio
import time
from src.utils.theme import AppTheme
from src.utils.validators import InputValidator

class TuningView(ft.Container):
    def __init__(self, esp_interface, page: ft.Page, global_tuner_instance):
        super().__init__()
        self.esp = esp_interface
        self.page = page
        self.tuner = global_tuner_instance 
        
        self.expand = True
        self.padding = 20
        self.running = True

        # Modelo por defecto para la simulación
        self.plant_model = {"Kp": 1.5, "tau": 30.0, "theta": 5.0}

        # Si ya había un modelo detectado en el tuner global, lo recuperamos
        if self.tuner.last_identified_model:
            self.plant_model = self.tuner.last_identified_model
            
        # --- CARGAR MEMORIA PERSISTENTE ---
        self.saved_kp = self.page.client_storage.get("pid_kp") or "2.0"
        self.saved_ki = self.page.client_storage.get("pid_ki") or "0.5"
        self.saved_kd = self.page.client_storage.get("pid_kd") or "1.0"
        self.saved_sp = self.page.client_storage.get("pid_sp") or "50.0"

        # --- CONSTRUCCIÓN DE UI ---
        self.build_ui()

        # --- NUEVO: RESTAURAR ESTADO VISUAL ---
        # Esto recupera las gráficas si vienes de otra pestaña
        self.restore_existing_data()

        # Iniciar bucle visual
        self.page.run_task(self.update_visuals_loop)

        # Sincronización inicial
        if self.esp.connected:
            self.handle_read_current_sp(update_ui=False)

    def restore_existing_data(self):
        """
        Reconstruye la escena al volver a la pestaña.
        Garantiza que no se pierdan las gráficas ni el estado de los botones.
        """
        # 1. RECUPERAR GRÁFICA ROJA (La Realidad)
        if self.tuner.time_data:
            points = [
                ft.LineChartDataPoint(x=self.tuner.time_data[i], y=self.tuner.temp_data[i])
                for i in range(len(self.tuner.time_data))
            ]
            self.line_real.data_points = points
            
            # Restaurar el ancho correcto (Auto-Escala)
            max_t = self.tuner.time_data[-1]
            self.chart.min_x = 0
            self.chart.max_x = max(60, max_t * 1.05)

        # 2. RECUPERAR ESTADO DE CONTROLES
        if self.tuner.recording:
            # Seguimos grabando
            self.btn_autotune.text = "DETENER"
            self.btn_autotune.style.bgcolor = "red"
            self.lbl_status_info.value = "Grabando..."
            self.container_imc.visible = False
        else:
            # Ya terminamos (Modo Análisis)
            self.btn_autotune.text = "Auto-Calibrar"
            self.btn_autotune.style.bgcolor = AppTheme.color_tuning
            
            if self.tuner.last_identified_model:
                self.plant_model = self.tuner.last_identified_model
                self.container_imc.visible = True
                
                # Restaurar slider lambda visualmente
                tau = self.plant_model['tau']
                self.slider_lambda.min = max(0.1, tau * 0.2)
                self.slider_lambda.max = tau * 3.0
                self.slider_lambda.value = tau 
                self.lbl_status_info.value = "Modelo cargado. Ajusta PID o reinicia."
                self.lbl_status_info.color = "green"

        # 3. RECUPERAR GRÁFICA AZUL (La Ideal)
        # Esto asegura que la curva comparativa reaparezca
        self.update_simulation_curve()

        
    def did_unmount(self):
        self.running = False

    def build_ui(self):
        # 1. INPUTS PID (Usamos los valores cargados de memoria)
        self.tf_sp = self._make_input("Setpoint", self.saved_sp, width=100) # <--- Usar self.saved_sp
        self.tf_kp = self._make_input("Kp", self.saved_kp)
        self.tf_ki = self._make_input("Ki", self.saved_ki)
        self.tf_kd = self._make_input("Kd", self.saved_kd)

        pid_row = ft.Row(
            controls=[self.tf_kp, self.tf_ki, self.tf_kd, self.tf_sp],
            spacing=10,
            alignment=ft.MainAxisAlignment.CENTER
        )

        # 2. BOTONES
        # Estado inicial depende de si el Tuner Global ya está grabando
        btn_text = "DETENER" if self.tuner.recording else "Auto-Calibrar"
        btn_bgcolor = "red" if self.tuner.recording else AppTheme.color_tuning

        self.btn_autotune = ft.ElevatedButton(
            text=btn_text,
            icon=ft.Icons.AUTO_FIX_HIGH,
            style=ft.ButtonStyle(bgcolor=btn_bgcolor, color="white"),
            on_click=self.handle_autotune_click
        )

        self.btn_upload = ft.ElevatedButton(
            "Subir al ESP32",
            icon=ft.Icons.UPLOAD,
            style=ft.ButtonStyle(bgcolor=AppTheme.color_mv, color="black"),
            on_click=self.handle_upload
        )

        # 3. SLIDER LAMBDA (IMC)
        self.slider_lambda = ft.Slider(
            min=0.1, max=10.0, divisions=100, value=1.0,
            label="Lambda: {value}s",
            active_color=AppTheme.color_tuning,
            on_change=self.on_lambda_change
        )

        self.container_imc = ft.Column(
            visible=(self.tuner.last_identified_model is not None),
            controls=[
                ft.Divider(color="grey"),
                ft.Row([
                    ft.Text("Rápido", size=10, color="red"),
                    ft.Container(content=self.slider_lambda, expand=True),
                    ft.Text("Suave", size=10, color="green")
                ]),
                ft.Text("Ajusta Lambda para recalcular PID.", size=10, color="grey", italic=True)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )

        # 4. ETIQUETA MATEMÁTICA FLOTANTE
        g_text = ft.Text("G(s) =", size=14, italic=True, font_family="Times New Roman", color="white")
        numerator = ft.Text("K", size=12, weight="bold", color="white")
        divider = ft.Container(width=30, height=1, bgcolor="white") 
        denominator = ft.Text("τs + 1", size=12, weight="bold", color="white")
        
        fraction = ft.Column([numerator, divider, denominator], spacing=1, alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        
        term_exponent = ft.Row([
            ft.Text("e", size=14, italic=True, font_family="Times New Roman", color="white"),
            ft.Text("-θs", size=10, weight="bold", color="white", offset=ft.Offset(0, -0.5))
        ], spacing=0, vertical_alignment=ft.CrossAxisAlignment.START)

        math_row = ft.Row([g_text, fraction, term_exponent], alignment=ft.MainAxisAlignment.CENTER, spacing=3)
        
        self.lbl_sim_params = ft.Text("K=1.5 | τ=30s | θ=5s", color=ft.Colors.CYAN_200, weight="bold", size=11, font_family=AppTheme.font_mono)

        floating_label = ft.Container(
            content=ft.Column([math_row, ft.Container(height=2), self.lbl_sim_params], spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=10, bgcolor="#CC111111", border_radius=8
        )

        # 5. PANEL LIVE (Recuperado: Temperatura + Dimmer Potencia)
        self.lbl_live_temp = ft.Text("-- °C", size=24, weight="bold", color=AppTheme.color_pv, font_family=AppTheme.font_mono)
        self.lbl_live_out = ft.Text("-- %", size=24, weight="bold", color=AppTheme.color_mv, font_family=AppTheme.font_mono)
        
        self.live_panel = ft.Container(
            bgcolor="#161616", border_radius=12, padding=10, border=ft.border.all(1, "#333"),
            content=ft.Row(
                controls=[
                    ft.Row([ft.Icon(ft.Icons.THERMOSTAT, color=AppTheme.color_pv, size=20), self.lbl_live_temp]),
                    ft.Container(width=1, height=25, bgcolor="#333"),
                    ft.Row([ft.Icon(ft.Icons.ELECTRIC_BOLT, color=AppTheme.color_mv, size=20), self.lbl_live_out]),
                ], alignment=ft.MainAxisAlignment.SPACE_EVENLY
            )
        )

        # 6. GRÁFICA + STACK
        self.line_real = ft.LineChartData(data_points=[], stroke_width=3, color=AppTheme.color_pv, curved=True, stroke_cap_round=True)
        self.line_ideal = ft.LineChartData(data_points=[], stroke_width=2, color=ft.Colors.CYAN_400, curved=True, stroke_cap_round=True)

        self.line_sp_ref = ft.LineChartData(
            data_points=[], 
            stroke_width=2, 
             color="#C5D20B", # color
            curved=False,             # Recta perfecta
        )

        self.chart = ft.LineChart(
            data_series=[self.line_sp_ref,self.line_ideal, self.line_real],
            min_y=0, max_y=100, min_x=0, max_x=60, expand=True,
            border=ft.border.all(1, AppTheme.card_border),
            horizontal_grid_lines=ft.ChartGridLines(interval=10, color="#222"),
            tooltip_bgcolor="#111111"
        )

        chart_stack = ft.Stack(
            controls=[
                ft.Container(content=self.chart, padding=10, bgcolor=AppTheme.card_bgcolor, border_radius=10, border=ft.border.all(1, AppTheme.card_border)),
                ft.Container(content=floating_label, top=20, right=20)
            ],
            height=300
        )

        legend = ft.Row([
            ft.Row([ft.Container(width=10, height=10, bgcolor=AppTheme.color_pv), ft.Text("Real", size=12)]),
            ft.Row([ft.Container(width=10, height=10, bgcolor=ft.Colors.CYAN_400), ft.Text("Ideal", size=12)]),
            ft.Row([ft.Container(width=10, height=10, bgcolor=ft.Colors.BLUE_700), ft.Text("Setpoint", size=12)]),
        ], alignment=ft.MainAxisAlignment.CENTER)

        self.lbl_status_info = ft.Text("Listo.", color="grey", size=12)

        # ENSAMBLAJE FINAL
        self.content = ft.Column(
            controls=[
                ft.Text("Sintonización Avanzada", size=20, weight="bold", color="white"),
                ft.Container(height=5),
                pid_row,
                ft.Container(height=5),
                ft.Row([self.btn_autotune, self.btn_upload], alignment=ft.MainAxisAlignment.CENTER),
                self.container_imc,
                ft.Divider(color="grey"),
                self.live_panel,
                ft.Container(height=10),
                chart_stack,
                legend,
                self.lbl_status_info
            ],
            scroll=ft.ScrollMode.AUTO
        )

    def _make_input(self, label, val, width=80):
        return ft.TextField(
            label=label, value=val, width=width, text_size=14,
            border_color="grey", keyboard_type=ft.KeyboardType.NUMBER, color="white",
            on_change=self.update_simulation_curve
        )

# --- SIMULACIÓN IDEAL + SETPOINT + GUARDADO SEGURO ---
    def update_simulation_curve(self, e=None):
        # 1. VISIBILIDAD: Si estamos grabando, ocultamos Ideal y SP, y salimos.
        if self.tuner.recording:
            self.line_ideal.data_points = []
            self.line_sp_ref.data_points = [] # <--- NUEVO: Ocultar también la referencia
            if self.chart.page: self.chart.update()
            return

        # 2. VALIDACIÓN VISUAL DEL SETPOINT
        sp_val = 0.0
        try:
            if self.tf_sp.value:
                sp_val = float(self.tf_sp.value)
                if 0 <= sp_val <= 80:
                    self.tf_sp.border_color = "grey"
                else:
                    self.tf_sp.border_color = "red"
            else:
                self.tf_sp.border_color = "grey"
        except ValueError:
            self.tf_sp.border_color = "red"
        
        if self.tf_sp.page:
            self.tf_sp.update()

        # 3. GUARDADO DE PREFERENCIAS (BLINDADO)
        try:
            if self.tf_sp.border_color == "grey":
                 self.page.client_storage.set("pid_sp", self.tf_sp.value)
            
            if self.tf_kp.value: self.page.client_storage.set("pid_kp", self.tf_kp.value)
            if self.tf_ki.value: self.page.client_storage.set("pid_ki", self.tf_ki.value)
            if self.tf_kd.value: self.page.client_storage.set("pid_kd", self.tf_kd.value)
        except Exception as ex:
            print(f"Warning: Storage busy ({ex})")

        # 4. PREPARACIÓN DE DATOS MATEMÁTICOS
        try:
            kp = float(self.tf_kp.value) if self.tf_kp.value else 0
            ki = float(self.tf_ki.value) if self.tf_ki.value else 0
            kd = float(self.tf_kd.value) if self.tf_kd.value else 0
            sp = sp_val # Usamos el valor validado arriba
        except: return

        # Obtener modelo FOPDT (Planta)
        K_proc = self.plant_model.get('Kp', 1.5)
        Tau = self.plant_model.get('tau', 30.0)
        Theta = self.plant_model.get('theta', 5.0)

        self.lbl_sim_params.value = f"K={K_proc:.2f} | τ={Tau:.1f}s | θ={Theta:.1f}s"
        if self.lbl_sim_params.page: self.lbl_sim_params.update()

        # 5. SINCRONIZACIÓN DE CONTEXTO
        if self.tuner.time_data:
            # Usamos los datos de la grabación real
            start_temp = self.tuner.base_temp
            max_t = self.tuner.time_data[-1]
            final_time = max(60, max_t * 1.05)
        else:
            # Modo reposo
            start_temp = self.tuner.latest_temp 
            final_time = 60

        # --- NUEVO: DIBUJAR LÍNEA DE SETPOINT (REFERENCIA) ---
        # Creamos dos puntos: Inicio (t=0) y Fin (t=final_time) a la altura de 'sp'
        self.line_sp_ref.data_points = [
            ft.LineChartDataPoint(x=0, y=sp),
            ft.LineChartDataPoint(x=final_time, y=sp)
        ]

        # 6. SIMULACIÓN MATEMÁTICA (Curva Ideal)
        sim_points = []
        temp = start_temp 
        integral = 0.0
        prev_err = 0.0
        
        dt = 0.2
        steps = int(final_time / dt)
        delay_steps = max(1, int(Theta / dt))
        out_buffer = [0.0] * (delay_steps + 2)

        for i in range(steps):
            t = i * dt
            err = sp - temp
            integral += err * dt
            deriv = (err - prev_err) / dt
            prev_err = err
            
            # PID Output (0-100%)
            out = max(0.0, min(100.0, (kp * err) + (ki * integral) + (kd * deriv)))
            
            # Planta
            out_buffer.append(out)
            delayed_out = out_buffer.pop(0)
            
            change = ((K_proc * delayed_out) - (temp - start_temp)) / Tau
            temp += change * dt
            
            sim_points.append(ft.LineChartDataPoint(x=t, y=temp))

        # 7. ACTUALIZAR GRÁFICA
        self.line_ideal.data_points = sim_points
        self.chart.min_x = 0
        self.chart.max_x = final_time
        
        if self.chart.page: self.chart.update()

    # --- AUTO-TUNE ---
    async def handle_autotune_click(self, e):
        # --- 1. BLOQUEO DE SEGURIDAD: VERIFICAR CONEXIÓN ---
        # Si no hay conexión real con el ESP32, no permitimos iniciar.
        # Esto evita errores de división por cero o datos vacíos.
        if not self.esp.connected:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text("⚠️ Error: Conecta el horno antes de iniciar el Auto-Tune"),
                bgcolor="red",
                duration=3000
            )
            self.page.snack_bar.open = True
            self.page.update()
            return # <--- IMPORTANTE: Detiene la ejecución aquí mismo.

        # --- 2. FLUJO NORMAL (Solo si está conectado) ---
        if self.tuner.recording:
            self.stop_autotune()
        else:
            await self.start_autotune()
            
    async def start_autotune(self):
        # 1. Enviar comando HW
        if hasattr(self.esp, 'send_auto_tune_cmd'):
            self.esp.send_auto_tune_cmd(True)
        
        # 2. Configurar Tuner Global
        start_temp = self.tuner.latest_temp # Usamos el dato live más reciente
        self.tuner.start_recording(start_temp)
        
        # 3. UI: Cambio a modo grabación
        self.btn_autotune.text = "DETENER"
        self.btn_autotune.style.bgcolor = "red"
        self.btn_autotune.update()
        
        # Ocultar controles de análisis mientras se graba
        self.container_imc.visible = False
        self.container_imc.update()
        
        self.lbl_status_info.value = "Grabando respuesta al escalón..."
        self.lbl_status_info.update()
        
        # Ocultar curva ideal para limpiar la vista
        self.update_simulation_curve()

    def stop_autotune(self):
        # 1. Enviar comando HW
        if hasattr(self.esp, 'send_auto_tune_cmd'):
            self.esp.send_auto_tune_cmd(False)
        
        # 2. Procesar Datos y detener
        model = self.tuner.stop_recording()
        
        # 3. UI: Regreso a modo reposo
        self.btn_autotune.text = "Auto-Calibrar"
        self.btn_autotune.style.bgcolor = AppTheme.color_tuning
        self.btn_autotune.update()

        if model:
            self.plant_model = model
            tau = model['tau']
            
            # Ajustar slider según el modelo detectado
            self.slider_lambda.min = max(0.1, tau * 0.2)
            self.slider_lambda.max = tau * 3.0
            self.slider_lambda.value = tau
            self.container_imc.visible = True
            self.container_imc.update()
            
            # Recalcular PID sugerido automáticamente
            self.on_lambda_change(None)
            
            self.lbl_status_info.value = "¡Modelo Identificado!"
            self.lbl_status_info.color = "green"
        else:
            self.lbl_status_info.value = "Fallo: Movimiento insuficiente o cancelación."
            self.lbl_status_info.color = "red"
        
        self.lbl_status_info.update()

        # 4. RE-DIBUJAR CURVA IDEAL (COMPARACIÓN)
        # Esto hace que la línea cian regrese sincronizada encima de la roja
        self.update_simulation_curve()

    def on_lambda_change(self, e):
        if not self.plant_model: return
        lam = self.slider_lambda.value
        kp, ki, kd = self.tuner.calculate_imc_pid(self.plant_model, lam)
        self.tf_kp.value, self.tf_ki.value, self.tf_kd.value = str(kp), str(ki), str(kd)
        if self.tf_kp.page: self.tf_kp.update(), self.tf_ki.update(), self.tf_kd.update()
        self.update_simulation_curve()

    def handle_upload(self, e):
        kp = InputValidator.validate_float(self.tf_kp)
        ki = InputValidator.validate_float(self.tf_ki)
        kd = InputValidator.validate_float(self.tf_kd)
        sp = InputValidator.validate_float(self.tf_sp, 0, 80) # Validar SP también
        
        if None not in [kp, ki, kd, sp]:
            # Enviar PID
            if self.esp.send_pid_config(kp, ki, kd):
                # Pausa breve para no saturar y Enviar SP
                time.sleep(0.1)
                self.esp.send_setpoint_only(sp)
                
                self.page.snack_bar = ft.SnackBar(ft.Text("Configuración completa enviada"), bgcolor="green")
            else:
                self.page.snack_bar = ft.SnackBar(ft.Text("Error comunicación"), bgcolor="red")
        else:
             self.page.snack_bar = ft.SnackBar(ft.Text("Revisa los números (SP máx 80)"), bgcolor="red")
        self.page.snack_bar.open = True
        self.page.update()
    
    def handle_read_current_sp(self, update_ui=True):
        pass

# --- BUCLE VISUAL PASIVO (MODIFICADO AUTO-ESCALA) ---
    async def update_visuals_loop(self):
        last_data_count = 0
        
        while self.running:
            try:
                # 1. VALIDACIÓN DE EXISTENCIA
                # Si la gráfica no está en la página (cambio de pestaña), esperamos.
                if not self.chart.page:
                    await asyncio.sleep(0.5)
                    continue

                # 2. ACTUALIZAR PANEL LIVE (Temp y Potencia)
                self.lbl_live_temp.value = f"{self.tuner.latest_temp:.1f} °C"
                self.lbl_live_out.value = f"{self.tuner.latest_out} %"
                self.lbl_live_temp.update()
                self.lbl_live_out.update()

                # 3. ACTUALIZAR GRÁFICA REAL (Solo si estamos grabando)
                if self.tuner.recording:
                    current_count = len(self.tuner.time_data)
                    
                    if current_count > last_data_count:
                        # Reconstrucción rápida de puntos
                        # (En Flet es mejor reasignar la lista completa)
                        points = [
                            ft.LineChartDataPoint(x=self.tuner.time_data[i], y=self.tuner.temp_data[i])
                            for i in range(current_count)
                        ]
                        self.line_real.data_points = points
                        
                        # LÓGICA DE AUTO-ESCALA (ESTIRAMIENTO)
                        if self.tuner.time_data:
                            max_t = self.tuner.time_data[-1]
                            
                            # Mantenemos el inicio fijo en 0
                            self.chart.min_x = 0
                            
                            # El final crece si superamos los 60s
                            # (1.05 es un margen del 5% a la derecha para estética)
                            self.chart.max_x = max(60, max_t * 1.05)
                        
                        self.chart.update()
                        last_data_count = current_count

                # 4. SINCRONIZACIÓN DE ESTADO (Por si hubo parada externa)
                # Si el tuner ya no graba, pero el botón sigue en rojo "DETENER"
                if not self.tuner.recording and self.btn_autotune.text == "DETENER":
                     # Resetear visualmente el botón
                     self.btn_autotune.text = "Auto-Calibrar"
                     self.btn_autotune.style.bgcolor = AppTheme.color_tuning
                     self.lbl_status_info.value = "Detenido."
                     
                     # Actualizar UI con seguridad
                     if self.btn_autotune.page: self.btn_autotune.update()
                     if self.lbl_status_info.page: self.lbl_status_info.update()
                     
                     # IMPORTANTE: Forzar reaparición de la línea azul comparativa
                     self.update_simulation_curve()

            except AssertionError:
                # Error normal al cambiar de vista muy rápido, lo ignoramos.
                pass
            except Exception as e:
                # Log de errores no críticos
                print(f"Log visual tuning: {e}")

            await asyncio.sleep(0.5)