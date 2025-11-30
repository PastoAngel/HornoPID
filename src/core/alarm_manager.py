# src/core/alarm_manager.py
import time

class AlarmManager:
    def __init__(self, page, esp_interface, on_trigger_callback):
        self.page = page
        self.esp = esp_interface
        self.on_trigger = on_trigger_callback
        
        # Variables de estado
        self.is_running = False
        self.end_time = 0.0  # Marca de tiempo UNIX cuando debe sonar
        self.buzzer_sent = False
        
        # Valores por defecto (cargamos de la memoria persistente si existen)
        saved_min = self.page.client_storage.get("timer_minutes")
        saved_sp = self.page.client_storage.get("timer_sp")
        
        self.initial_minutes = saved_min if saved_min is not None else 5.0
        self.target_sp = saved_sp if saved_sp is not None else 0.0

    def start_process(self, setpoint, minutes):
        """
        Inicia el proceso: 
        1. Guarda configuración.
        2. Envía SOLO el Setpoint al ESP32 (Seguro).
        3. Calcula la hora exacta de finalización.
        """
        self.target_sp = float(setpoint)
        self.initial_minutes = float(minutes)
        
        # Persistencia: Guardar para la próxima vez que se abra la app
        self.page.client_storage.set("timer_minutes", self.initial_minutes)
        self.page.client_storage.set("timer_sp", self.target_sp)
        
        # --- CORRECCIÓN DE SEGURIDAD ---
        # Antes enviábamos (0,0,0, sp) arriesgando el PID.
        # Ahora usamos el método dedicado que solo toca la temperatura 'T'.
        self.esp.send_setpoint_only(self.target_sp)
        
        # 2. Calcular HORA DE FIN EXACTA (Timestamp Actual + Segundos)
        # Usar Timestamp es mejor que restar 1 segundo, porque es inmune a bloqueos de la app.
        self.end_time = time.time() + (self.initial_minutes * 60)
        
        self.is_running = True
        self.buzzer_sent = False
        print(f"Iniciado. Termina en timestamp: {self.end_time}")

    def stop_process(self):
        """Detiene el contador y apaga el buzzer manualmente."""
        self.is_running = False
        self.esp.send_buzzer(False)
        self.buzzer_sent = False
        print("Proceso detenido manualmente.")

    def get_remaining_seconds(self):
        """Calcula cuánto falta comparando la hora actual con la hora fin."""
        if not self.is_running:
            return 0
        
        remaining = self.end_time - time.time()
        
        if remaining <= 0:
            return 0
        
        return int(remaining)

    def check_status(self):
        """
        Llamar a esto constantemente desde el bucle global en main.py.
        Verifica si ya pasamos la hora de finalización.
        """
        if self.is_running:
            # Si el tiempo actual es mayor o igual al tiempo fin
            if time.time() >= self.end_time:
                if not self.buzzer_sent:
                    # ¡TIEMPO CUMPLIDO!
                    print("Timer finalizado. Enviando señal Buzzer...")
                    self.esp.send_buzzer(True)
                    
                    # Notificar a la interfaz (TopBar)
                    if self.on_trigger:
                        self.on_trigger()
                    
                    self.buzzer_sent = True