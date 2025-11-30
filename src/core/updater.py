import requests
import flet as ft
from src.core.version import APP_VERSION, GITHUB_REPO, LANDING_PAGE_URL

def check_for_updates(page: ft.Page):
    """
    Consulta GitHub para ver si hay un release más nuevo.
    Si lo hay, muestra un diálogo bloqueante o un banner.
    """
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
    
    try:
        # Timeout de 3 seg para no congelar el arranque si no hay internet
        response = requests.get(api_url, timeout=3)
        
        if response.status_code == 200:
            data = response.json()
            latest_version = data.get("tag_name", "") # Ej: "v1.0.1"
            
            # Lógica simple de comparación de strings 
            # (Para algo pro, usar la librería 'packaging.version')
            if latest_version and latest_version != APP_VERSION:
                show_update_dialog(page, latest_version, data.get("body", ""))
                
    except Exception as e:
        print(f"Update check failed: {e}")

def show_update_dialog(page, new_version, release_notes):
    def go_download(e):
        page.launch_url(LANDING_PAGE_URL)
        
    def close_dlg(e):
        dlg.open = False
        page.update()

    dlg = ft.AlertDialog(
        title=ft.Text("¡Nueva Versión Disponible!"),
        content=ft.Column([
            ft.Text(f"Actual: {APP_VERSION} -> Nueva: {new_version}", weight="bold"),
            ft.Text("Novedades:", size=12, weight="bold"),
            ft.Container(
                content=ft.Text(release_notes, size=12),
                height=100,
                scroll=ft.ScrollMode.AUTO
            )
        ], tight=True, width=400),
        actions=[
            ft.TextButton("Más tarde", on_click=close_dlg),
            ft.ElevatedButton("Descargar", on_click=go_download, bgcolor="green", color="white"),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    
    page.dialog = dlg
    dlg.open = True
    page.update()