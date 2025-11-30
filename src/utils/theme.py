# src/utils/theme.py
import flet as ft

class AppTheme:
    # --- PALETA BASE ---
    dark_bg = "#000000" # Negro Absoluto (OLED)
    
    # --- COLORES SEMÁNTICOS PID (Los que causaban el error) ---
    color_pv = "#FF1744"   # Rojo Neón -> Temperatura Actual
    color_sp = "#2979FF"   # Azul Eléctrico -> Setpoint
    color_mv = "#00E676"   # Verde Matriz -> Salida del Dimmer
    
    # --- COLORES DE ESTADO ---
    color_alarm = "#D50000"  # Rojo Alarma
    color_stable = "#00C853" # Verde Estable
    color_tuning = "#AA00FF" # Morado (Modo Auto-Sintonía)
    
    # --- ESTILO DE TARJETAS (Glassmorphism) ---
    card_bgcolor = "#151515" # Gris muy oscuro transparente
    card_border = "#333333"  # Borde gris sutil
    
    # --- TIPOGRAFÍA ---
    text_primary = "#FFFFFF"
    text_secondary = "#B0BEC5" # Gris azulado
    font_mono = "Roboto Mono"  # Importante para que los números no bailen

    # --- MÉTODOS DE COMPATIBILIDAD ---
    # Mantenemos estos métodos por si algún componente viejo (sidebar) los llama
    @staticmethod
    def get_sidebar_color(mode: ft.ThemeMode):
        return AppTheme.dark_bg

    @staticmethod
    def get_highlight_color(mode: ft.ThemeMode):
        return "#333333"