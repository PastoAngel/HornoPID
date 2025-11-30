# src/components/kpi_card.py
import flet as ft
from src.utils.theme import AppTheme

class KPICard(ft.Container):
    def __init__(self, icon, title, initial_value, unit, value_color):
        super().__init__()
        
        self.unit = unit
        
        # Texto del valor (Guardamos referencia para actualizar rápido)
        self.display_text = ft.Text(
            f"{initial_value}{unit}", 
            size=26, 
            weight="bold", 
            color=value_color,
            font_family=AppTheme.font_mono 
        )
        
        # --- Estructura Interna ---
        self.content = ft.Column(
            controls=[
                # Cabecera: Icono + Título pequeño
                ft.Row(
                    controls=[
                        ft.Icon(icon, size=16, color=AppTheme.text_secondary),
                        ft.Text(title, size=12, color=AppTheme.text_secondary, weight="w600")
                    ],
                    spacing=5,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER
                ),
                
                ft.Container(height=5),
                
                # Valor Grande
                self.display_text
            ],
            spacing=0,
            alignment=ft.MainAxisAlignment.CENTER
        )
        
        # --- Estilo Visual (Dark Glass) ---
        self.bgcolor = AppTheme.card_bgcolor
        self.border = ft.border.all(1, AppTheme.card_border)
        self.border_radius = 12
        self.padding = 15
        
        # Expansión: Permite que la tarjeta crezca en grillas responsivas
        self.expand = True 

    def set_value(self, new_val):
        """
        Actualiza el valor numérico en la interfaz.
        Acepta float, int o str.
        """
        if isinstance(new_val, float):
            text_val = f"{new_val:.1f}"
        else:
            text_val = str(new_val)
            
        self.display_text.value = f"{text_val}{self.unit}"
        
        # --- CORRECCIÓN DE SEGURIDAD ---
        # Solo actualizamos si el control está efectivamente en la página
        if self.display_text.page:
            self.display_text.update()