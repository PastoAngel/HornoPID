# src/utils/validators.py
import flet as ft
from src.utils.theme import AppTheme

class InputValidator:
    @staticmethod
    def validate_float(control: ft.TextField, min_val=0.0, max_val=1000.0):
        """
        Valida que el input sea un número float seguro.
        
        Retorno:
        - float: Si es válido.
        - None: Si es inválido (texto, vacío o fuera de rango).
        
        Efectos visuales:
        - Borde Azul: Correcto.
        - Borde Rojo + Texto (!): Error.
        """
        try:
            if not control.value:
                raise ValueError("Vacío")
                
            val = float(control.value)
            
            if min_val <= val <= max_val:
                # ÉXITO: Limpiamos errores visuales
                control.border_color = AppTheme.color_sp # Azul semántico
                control.error_text = None
                control.update()
                return val
            else:
                raise ValueError("Fuera de rango")
                
        except ValueError:
            # ERROR: Marcamos visualmente y retornamos None
            control.border_color = AppTheme.color_alarm # Rojo semántico
            control.error_text = "!" # Indicador discreto
            control.update()
            return None