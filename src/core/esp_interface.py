# src/core/esp_interface.py
import socket
import time
import re
import threading

# Importación segura de Serial
try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

class ESP32Interface:
    def __init__(self):
        self.mode = "NONE" # "SERIAL" o "WIFI"
        
        # Conexiones
        self.serial_conn = None
        self.socket_conn = None
        
        self.wifi_ip = "192.168.4.1"
        self.connected = False
        self.lock = threading.Lock()
        
        # --- NUEVO: RESILIENCIA ---
        self.auto_reconnect = True
        self.last_known_ip = None
        self.last_known_port = 80
        
        # REGEX: temp=25.00,setpoint=50.0,dimmer=128,...
        self.regex_status = re.compile(
            r"temp=([\d\.]+).*?setpoint=([\d\.]+).*?dimmer=(\d+)"
        )

    # --- 1. GESTIÓN SERIAL (USB) ---
    def scan_serial_ports(self):
        if not SERIAL_AVAILABLE: return []
        return [p.device for p in serial.tools.list_ports.comports()]

    def connect_serial(self, port, baudrate=115200):
        if not SERIAL_AVAILABLE: return False, "Librería Serial no encontrada"
        self.disconnect()
        
        try:
            self.serial_conn = serial.Serial(port, baudrate, timeout=1, write_timeout=1)
            time.sleep(2) # Esperar reset
            
            self.serial_conn.write(b"CONNECT_USB\n")
            time.sleep(0.5)
            self.serial_conn.reset_input_buffer()
            
            self.mode = "SERIAL"
            self.connected = True
            self.auto_reconnect = False # En Serial no auto-reconectamos igual
            return True, f"Conectado a {port}"
        except Exception as e:
            self.connected = False
            return False, str(e)

    # --- 2. GESTIÓN WIFI (TCP SOCKET) ---
    def connect_wifi(self, ip, port=80):
        self.disconnect()
        self.wifi_ip = ip
        
        try:
            self.socket_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket_conn.settimeout(3.0) 
            self.socket_conn.connect((ip, port))
            
            self.mode = "WIFI"
            self.connected = True
            
            # Guardamos datos para reconexión futura
            self.last_known_ip = ip
            self.last_known_port = port
            self.auto_reconnect = True
            
            return True, f"Conectado a {ip}"
        except Exception as e:
            self.connected = False
            return False, f"Error WiFi: {str(e)}"

    def attempt_reconnect(self):
        """Intenta reconectar silenciosamente si se perdió la conexión WiFi"""
        if self.mode == "NONE" and self.auto_reconnect and self.last_known_ip:
            # Intentamos conectar sin bloquear la UI principal mucho tiempo
            try:
                # Usamos un timeout muy corto para el chequeo
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1.0)
                result = sock.connect_ex((self.last_known_ip, self.last_known_port))
                sock.close()
                
                if result == 0:
                    print(f"[Auto-Reconnect] Recuperando conexión a {self.last_known_ip}...")
                    return self.connect_wifi(self.last_known_ip, self.last_known_port)
            except:
                pass
        return False, "No reconnect"

    def disconnect(self):
        with self.lock:
            self.connected = False
            self.mode = "NONE"
            
            if self.serial_conn:
                try: self.serial_conn.close()
                except: pass
                self.serial_conn = None
            
            if self.socket_conn:
                try: self.socket_conn.close()
                except: pass
                self.socket_conn = None

    # --- 3. ENVÍO DE COMANDOS ---
    def _send_raw(self, cmd_str):
        if not self.connected: return False
        
        payload = (cmd_str + "\n").encode('utf-8')
        
        try:
            with self.lock:
                if self.mode == "SERIAL" and self.serial_conn:
                    self.serial_conn.write(payload)
                    return True
                elif self.mode == "WIFI" and self.socket_conn:
                    self.socket_conn.sendall(payload)
                    return True
        except Exception as e:
            print(f"Error enviando: {e}")
            self.disconnect() 
            return False
        return False

    # --- NUEVO: ENVÍO SEGURO SEPARADO ---
    
    def send_setpoint_only(self, setpoint):
        """Envía SOLO el Setpoint (Comando T). Ligero y seguro."""
        return self._send_raw(f"T{setpoint}")

    def send_pid_config(self, kp, ki, kd):
        """Envía SOLO la configuración PID secuencialmente."""
        # Enviamos con pequeñas pausas para asegurar que el ESP procese
        if not self._send_raw(f"P{kp}"): return False
        time.sleep(0.05)
        if not self._send_raw(f"I{ki}"): return False
        time.sleep(0.05)
        if not self._send_raw(f"D{kd}"): return False
        return True

    def send_wifi_config(self, ssid, password):
        """
        Envía las credenciales WiFi al ESP32.
        El ESP32 se reiniciará automáticamente y tratará de conectar.
        """
        # Formato esperado por tu firmware: "SET_WIFI:SSID;PASSWORD"
        cmd = f"SET_WIFI:{ssid};{password}"
        return self._send_raw(cmd)

    def send_wifi_reset(self):
        """
        Borra las credenciales en el ESP32.
        El ESP32 se reiniciará y volverá a modo AP (Punto de Acceso).
        """
        return self._send_raw("RESET_WIFI")
    
    
    def send_buzzer(self, state: bool):
        cmd = "B1" if state else "B0"
        return self._send_raw(cmd)

    def send_auto_tune_cmd(self, start: bool):
        """Inicia (E) o Detiene (N) el modo Auto-Tune/Manual"""
        cmd = "E" if start else "N"
        return self._send_raw(cmd)

    def send_manual_power(self, power_percent):
        """Para pruebas manuales si fuera necesario (no usado en PID normal)"""
        # Tu firmware actual usa el PID, pero si implementas modo manual:
        # return self._send_raw(f"M{power_percent}")
        pass

    # --- 4. TELEMETRÍA (LECTURA) ---
    def read_telemetry(self):
        """
        Retorna: {'temp': 25.0, 'sp': 50.0, 'out': 50} (Out en %)
        """
        if not self.connected: return None
        
        response_line = ""
        
        try:
            # Petición
            if not self._send_raw("GET_ESTADO"): return None
            
            # Lectura
            if self.mode == "SERIAL" and self.serial_conn:
                if self.serial_conn.in_waiting > 0:
                    response_line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
            
            elif self.mode == "WIFI" and self.socket_conn:
                data = self.socket_conn.recv(1024)
                response_line = data.decode('utf-8', errors='ignore').strip()

            # Parseo
            if "ESTADO:" in response_line:
                match = self.regex_status.search(response_line)
                if match:
                    temp = float(match.group(1))
                    sp = float(match.group(2))
                    raw_dimmer = int(match.group(3)) # 0-255
                    
                    # Convertir a % para la UI
                    out_percent = (raw_dimmer / 255.0) * 100.0
                    
                    return {
                        'temp': temp,
                        'sp': sp,
                        'out': int(out_percent)
                    }
                    
        except Exception:
            # Fallo silencioso de lectura, el watchdog o el loop principal
            # manejarán la desconexión si es persistente.
            pass
            
        return None