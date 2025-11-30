import flet as ft

class PlaceholderView(ft.Container):
    def __init__(self, title, icon, bgcolor="surfaceVariant"):
        super().__init__()
        self.expand = True
        self.alignment = ft.alignment.center
        
        # Usamos el color de fondo pasado o uno por defecto del tema
        self.bgcolor = bgcolor 
        
        self.content = ft.Column(
            controls=[
                # CORRECCIÓN: En lugar de ft.colors.with_opacity, 
                # usamos el color "grey" y la propiedad opacity=0.5 del icono.
                ft.Icon(icon, size=80, color="grey", opacity=0.5),
                
                ft.Container(height=20),
                
                # Título de la sección
                ft.Text(title, size=30, weight="bold"),
                
                ft.Container(height=10),
                
                # Subtítulo descriptivo
                ft.Text(
                    "Esta funcionalidad está en desarrollo.\nPronto podrás configurar parámetros aquí.", 
                    color="grey", 
                    size=16,
                    text_align=ft.TextAlign.CENTER
                ),
                
                ft.Container(height=30),
                
                # Botón simulado
                ft.OutlinedButton(
                    "Volver al Inicio",
                    icon=ft.Icons.HOME,
                    on_click=lambda e: print("Navegación manual requerida") 
                )
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER
        )