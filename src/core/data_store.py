# src/core/data_store.py
import flet as ft

class DataStore:
    def __init__(self):
        # --- CAPA VISUAL (Flet Objects) ---
        # Mantenemos esta lista corta para que la gráfica no se trabe
        self.data_temp = [] 
        self.data_sp = []
        
        # --- NUEVO: Variable para guardar la última potencia recibida ---
        self.last_power = 0
        
        # --- CAPA HISTÓRICA (Raw Data) ---
        # Guardamos todo aquí para exportar a Excel/CSV.
        # Usamos tuplas simples (x, y) que consumen menos RAM que objetos Flet
        self.full_temp_history = [] 
        self.full_sp_history = []
        
        # Referencia de tiempo
        self.start_time = None

    def add_data(self, elapsed_time, temp, sp, power=0): # <--- Añadido argumento power
        """
        Agrega datos dividiéndolos en capa visual y capa histórica.
        """
        # Actualizamos la potencia actual para que el Dashboard la lea
        self.last_power = power

        # 1. Guardar en Historial Completo (Sin límite, o límite muy alto)
        self.full_temp_history.append((elapsed_time, temp))
        self.full_sp_history.append((elapsed_time, sp))

        # 2. Guardar en Capa Visual (Sliding Window / Ventana Deslizante)
        # Límite de puntos visibles simultáneamente. 
        # 300 puntos a 0.5s/sample = 2.5 minutos de alta resolución en pantalla.
        # Si la gráfica es de 60s, esto sobra y basta, manteniendo la UI fluida.
        MAX_UI_POINTS = 300 

        self.data_temp.append(ft.LineChartDataPoint(x=elapsed_time, y=temp))
        self.data_sp.append(ft.LineChartDataPoint(x=elapsed_time, y=sp))
        
        # Algoritmo Anti-Lag: Si excedemos el límite visual, borramos los más viejos
        # de la lista visual (pero quedan guardados en full_history).
        if len(self.data_temp) > MAX_UI_POINTS:
            self.data_temp.pop(0)
            self.data_sp.pop(0)

    def get_export_data(self):
        """
        Retorna las listas completas para generar el CSV.
        """
        return self.full_temp_history, self.full_sp_history

    def clear_data(self):
        """Borra todo y reinicia el contador de tiempo"""
        self.data_temp.clear()
        self.data_sp.clear()
        
        self.full_temp_history.clear()
        self.full_sp_history.clear()
        
        self.start_time = None # Resetear tiempo
        self.last_power = 0    # Resetear potencia