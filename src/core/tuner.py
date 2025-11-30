# src/core/tuner.py
import math
import time

class StepResponseAnalyzer:
    def __init__(self):
        # --- Datos Históricos (Gráfica) ---
        self.time_data = []
        self.temp_data = []
        
        # --- Estado en Vivo (Para UI sin leer socket) ---
        self.latest_temp = 0.0
        self.latest_out = 0    # Para el "Dimmer Verde"
        
        # --- Control de Proceso ---
        self.recording = False
        self.start_time = 0.0
        self.base_temp = 0.0
        self.step_power = 100.0
        
        # --- Resultado (Persistencia) ---
        self.last_identified_model = None

    def start_recording(self, current_temp, step_power=100.0):
        """Inicia sesión de grabación."""
        self.time_data = []
        self.temp_data = []
        self.base_temp = current_temp
        self.step_power = float(step_power)
        
        self.recording = True
        self.start_time = time.time()
        self.last_identified_model = None
        
        print(f"[Tuner] Rec ON. T0: {current_temp}°C")

    def update_live_data(self, temp, out_percent):
        """
        Actualiza los datos en vivo.
        Llamado desde main.py constantemente (aunque no estemos grabando).
        """
        self.latest_temp = temp
        self.latest_out = out_percent

        # Si estamos grabando, guardamos en el historial también
        if self.recording:
            t_rel = time.time() - self.start_time
            self.time_data.append(t_rel)
            self.temp_data.append(temp)

    def stop_recording(self):
        """Detiene y calcula el modelo."""
        self.recording = False
        self.last_identified_model = self._identify_fopdt_model()
        return self.last_identified_model

    def _identify_fopdt_model(self):
        """Calcula Kp, Tau, Theta (Método 2 puntos)."""
        if len(self.temp_data) < 10: return None

        final_temp = sum(self.temp_data[-5:]) / 5.0
        delta_temp = final_temp - self.base_temp

        if delta_temp <= 2.0: return None

        Kp = delta_temp / self.step_power

        target_t1 = self.base_temp + (delta_temp * 0.283)
        target_t2 = self.base_temp + (delta_temp * 0.632)

        t1 = self._find_time_at_temp(target_t1)
        t2 = self._find_time_at_temp(target_t2)

        if t1 is None or t2 is None: return None

        tau = 1.5 * (t2 - t1)
        theta = t2 - tau

        if theta < 0.1: theta = 0.5
        if tau < 1.0: tau = 1.0

        return {
            "Kp": round(Kp, 4),    
            "tau": round(tau, 2),  
            "theta": round(theta, 2), 
            "delta_temp": round(delta_temp, 1)
        }

    def _find_time_at_temp(self, target_temp):
        for i in range(len(self.temp_data) - 1):
            curr = self.temp_data[i]
            next_t = self.temp_data[i+1]
            if (curr <= target_temp <= next_t):
                denom = next_t - curr
                if denom == 0: continue
                ratio = (target_temp - curr) / denom
                return self.time_data[i] + (self.time_data[i+1] - self.time_data[i]) * ratio
        return None

    def calculate_imc_pid(self, model, lambda_val=None):
        if not model: return (0, 0, 0)
        Kp_proc, tau, theta = model['Kp'], model['tau'], model['theta']
        
        # --- MODIFICACIÓN 1: Lambda más agresivo por defecto ---
        if lambda_val is None: lambda_val = tau * 0.5 
        
        if Kp_proc == 0: return (0, 0, 0)

        # 1. Kc (Ganancia Proporcional)
        num = tau + (0.5 * theta)
        den = lambda_val + (0.5 * theta)
        Kc = (1.0 / Kp_proc) * (num / den)
        
        # 2. Ti (Tiempo Integral)
        Ti = tau + (0.5 * theta)
        
        # 3. Td (Tiempo Derivativo)
        denom_d = (2.0 * tau) + theta
        Td_raw = (tau * theta) / denom_d if denom_d != 0 else 0
        
        # --- MODIFICACIÓN 2: Reducir freno derivativo ---
        # Dividimos por 4 para sistemas térmicos lentos.
        # Esto evita que el Kd sea tan alto que apague el horno prematuramente.
        Td = Td_raw / 4.0

        # Conversión a formato PID Estándar
        # Kp = Kc
        # Ki = Kc / Ti
        # Kd = Kc * Td

        return round(Kc, 2), round(Kc / Ti if Ti > 0 else 0, 3), round(Kc * Td, 2)