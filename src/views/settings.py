# src/views/settings.py
import flet as ft
import socket
from src.utils.theme import AppTheme

class SettingsView(ft.Container):
    def __init__(self, esp_interface, page: ft.Page):
        super().__init__()
        self.esp = esp_interface 
        self.page_ref = page 
        self.expand = True
        self.padding = 20
        
        # --- GUI ELEMENTOS ---
        self.build_ui()
        
        # Sincronización inicial (Sin actualizar gráfico para evitar error)
        self.scan_ports(None, update_ui=False)
        self.refresh_state_visuals(update_ui=False)
        
        # Chequeo silencioso de AP
        self.check_ap_availability(update_ui=False)

    def build_ui(self):
        # --- 1. TARJETA DE ESTADO PRINCIPAL ---
        self.status_text = ft.Text("Estado: DESCONECTADO", color=AppTheme.color_alarm, size=18, weight="bold")
        self.btn_disconnect = ft.OutlinedButton("Desconectar", icon=ft.Icons.LINK_OFF, style=ft.ButtonStyle(color="red"), on_click=self.handle_disconnect)

        status_card = ft.Container(
            content=ft.Row([self.status_text, ft.Container(expand=True), self.btn_disconnect]),
            padding=15, bgcolor="#1a1a1a", border_radius=10, border=ft.border.all(1, "#333")
        )

        # --- 2. ASISTENTE DE VINCULACIÓN ---
        self.ap_status_icon = ft.Icon(ft.Icons.WIFI_TETHERING_OFF, color="grey")
        self.ap_status_text = ft.Text("Buscando señal del Horno...", size=12, color="grey")
        
        self.btn_connect_ap_direct = ft.ElevatedButton(
            "Vincular con Horno (AP)",
            icon=ft.Icons.ROCKET_LAUNCH,
            style=ft.ButtonStyle(bgcolor=AppTheme.color_sp, color="white"),
            disabled=True, 
            on_click=lambda e: self.handle_wifi_connect(None, ip_override="192.168.4.1")
        )

        self.btn_open_wifi_settings = ft.OutlinedButton(
            "Abrir Ajustes WiFi del Sistema",
            icon=ft.Icons.SETTINGS_SYSTEM_DAYDREAM,
            on_click=self.open_system_wifi_settings
        )

        link_card = ft.Container(
            bgcolor=AppTheme.card_bgcolor, border=ft.border.all(1, AppTheme.color_sp), border_radius=15, padding=20,
            content=ft.Column([
                ft.Row([ft.Icon(ft.Icons.LINK, color="white"), ft.Text(" Asistente de Vinculación", size=16, weight="bold")]),
                ft.Text("1. Conecta tu celular/PC a la red WiFi 'HornoPID_Control'.", color="white"),
                ft.Text("2. Si aparece el botón azul abajo, dale click para conectar.", color="white"),
                ft.Container(height=5),
                self.btn_open_wifi_settings, 
                ft.Divider(color="grey"),
                ft.Row([self.ap_status_icon, self.ap_status_text], alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(content=self.btn_connect_ap_direct, alignment=ft.alignment.center)
            ])
        )

        # --- 3. CONFIGURACIÓN DE CREDENCIALES (NUEVO) ---
        self.tf_ssid = ft.TextField(label="Tu Red WiFi (Casa)", hint_text="Ej: MiCasa_2.4G", border_color=AppTheme.color_mv, expand=True, color="white")
        self.tf_pass = ft.TextField(label="Contraseña", password=True, can_reveal_password=True, border_color=AppTheme.color_mv, expand=True, color="white")
        
        self.btn_save_creds = ft.ElevatedButton(
            "Guardar en Horno",
            icon=ft.Icons.SAVE_AS,
            style=ft.ButtonStyle(bgcolor=AppTheme.color_mv, color="black"),
            on_click=self.handle_save_wifi_creds
        )
        
        self.btn_reset_wifi = ft.TextButton("Borrar datos y volver a AP", icon=ft.Icons.DELETE_FOREVER, icon_color="red", on_click=self.handle_reset_wifi)

        config_card = ft.Container(
            bgcolor=AppTheme.card_bgcolor, border=ft.border.all(1, AppTheme.card_border), border_radius=15, padding=20,
            content=ft.Column([
                ft.Text("Configurar Internet en el Horno", size=16, weight="bold"),
                ft.Text("Úsalo cuando ya estés vinculado (Estado: CONECTADO WiFi)", size=10, italic=True),
                ft.Container(height=10),
                ft.Row([self.tf_ssid, self.tf_pass]),
                ft.Row([self.btn_save_creds, self.btn_reset_wifi], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            ])
        )

        # --- 4. CONEXIÓN MANUAL (IP/USB) ---
        self.ip_input = ft.TextField(
            label="IP Manual", 
            value=self.esp.wifi_ip, 
            border_color="grey", 
            expand=True
        )
        self.btn_wifi_connect = ft.IconButton(icon=ft.Icons.LOGIN, on_click=self.handle_wifi_connect)
        
        self.port_dropdown = ft.Dropdown(
            label="Puerto USB", 
            expand=True, 
            border_color="grey"
        )
        self.btn_refresh = ft.IconButton(icon=ft.Icons.REFRESH, on_click=self.scan_ports)
        self.btn_serial_connect = ft.IconButton(icon=ft.Icons.USB, on_click=self.handle_serial_connect)

        manual_card = ft.ExpansionTile(
            title=ft.Text("Conexión Manual Avanzada", size=14),
            controls=[
                ft.Container(padding=10, content=ft.Column([
                    ft.Row([self.ip_input, self.btn_wifi_connect]),
                    ft.Row([self.port_dropdown, self.btn_refresh, self.btn_serial_connect])
                ]))
            ]
        )

        # ENSAMBLAJE
        self.content = ft.Column(
            controls=[
                ft.Text("Centro de Conexión", size=24, weight="bold"),
                status_card,
                ft.Container(height=10),
                link_card,   
                ft.Container(height=10),
                config_card, 
                ft.Container(height=10),
                manual_card 
            ], scroll=ft.ScrollMode.AUTO
        )
        
        # Escaneo inicial
        self.scan_ports(None, update_ui=False)

    # --- LÓGICA DE ASISTENCIA ---

    def open_system_wifi_settings(self, e):
        # Intenta abrir configuración nativa
        try:
            self.page_ref.launch_url("ms-settings:network-wifi")
        except:
            self.show_snack("Abre tu configuración WiFi y busca 'HornoPID_Control'", "blue")

    def check_ap_availability(self, update_ui=True):
        """Verifica silenciosamente si 192.168.4.1 responde"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.2) 
            result = sock.connect_ex(('192.168.4.1', 80))
            sock.close()
            
            if result == 0:
                self.ap_status_icon.icon = ft.Icons.WIFI_TETHERING
                self.ap_status_icon.color = "green"
                self.ap_status_text.value = "¡Horno Detectado en Modo AP!"
                self.ap_status_text.color = "green"
                self.btn_connect_ap_direct.disabled = False
                self.btn_connect_ap_direct.text = "¡Conectar Ahora!"
            else:
                self.ap_status_icon.icon = ft.Icons.WIFI_TETHERING_OFF
                self.ap_status_icon.color = "red"
                self.ap_status_text.value = "No se detecta el Horno (Conecta al WiFi 'HornoPID_Control')"
                self.btn_connect_ap_direct.disabled = True
                
        except:
            pass
        
        if update_ui and self.page_ref: 
            self.update()

    # --- LÓGICA DE GESTIÓN WIFI (UPDATED) ---

    def handle_save_wifi_creds(self, e):
        ssid = self.tf_ssid.value
        password = self.tf_pass.value
        if not ssid or not password:
            self.show_snack("Faltan datos", "red")
            return
        if not self.esp.connected:
            self.show_snack("No hay conexión con el horno", "orange")
            return

        # Usamos el método dedicado del interface
        if self.esp.send_wifi_config(ssid, password):
             self.show_snack("Datos enviados. El horno se reiniciará.", "green")
        else:
             self.show_snack("Error de envío", "red")

    def handle_reset_wifi(self, e):
        if not self.esp.connected:
            self.show_snack("No conectado", "red")
            return
        
        # Usamos el método dedicado
        self.esp.send_wifi_reset()
        self.show_snack("Reset enviado. Espera la red 'HornoPID_Control'", "orange")

    # --- LÓGICA DE CONEXIÓN ESTÁNDAR ---

    def handle_wifi_connect(self, e, ip_override=None):
        ip = ip_override if ip_override else self.ip_input.value
        
        if not ip: return
        
        if self.btn_connect_ap_direct.disabled == False:
            self.btn_connect_ap_direct.text = "Conectando..."
            self.update()

        success, msg = self.esp.connect_wifi(ip)
        
        if success:
            self.show_snack(f"Conectado a {ip}", "green")
        else:
            self.show_snack("No se pudo conectar", "red")
            self.check_ap_availability(update_ui=True)
        
        self.refresh_state_visuals(update_ui=True)

    def refresh_state_visuals(self, update_ui=True):
        if self.esp.connected:
            txt = f"CONECTADO: {self.esp.mode}"
            if self.esp.mode == "WIFI": txt += f" ({self.esp.wifi_ip})"
            self.status_text.value = txt
            self.status_text.color = AppTheme.color_stable
            self.btn_wifi_connect.disabled = True
            self.btn_serial_connect.disabled = True
            self.btn_save_creds.disabled = False
        else:
            self.status_text.value = "Estado: DESCONECTADO"
            self.status_text.color = AppTheme.color_alarm
            self.btn_wifi_connect.disabled = False
            self.btn_serial_connect.disabled = False
            self.btn_save_creds.disabled = True
            
        if update_ui and self.page_ref: self.update()

    def scan_ports(self, e, update_ui=True):
        ports = self.esp.scan_serial_ports()
        self.port_dropdown.options = [ft.dropdown.Option(p) for p in ports]
        if update_ui and self.port_dropdown.page: self.port_dropdown.update()

    def handle_serial_connect(self, e):
        if self.esp.connect_serial(self.port_dropdown.value)[0]:
            self.refresh_state_visuals(update_ui=True)
        else: self.show_snack("Error Serial", "red")

    def handle_disconnect(self, e):
        self.esp.disconnect()
        self.refresh_state_visuals(update_ui=True)
        self.check_ap_availability(update_ui=True)

    def show_snack(self, msg, color):
        if self.page_ref:
            self.page_ref.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=color)
            self.page_ref.snack_bar.open = True
            self.page_ref.update()