import paho.mqtt.client as mqtt
import numpy as np
from collections import deque
import pyqtgraph as pg 
from pyqtgraph.Qt import QtWidgets, QtCore 
import sys 
import time 
# Asegúrate de que esta línea de importación sea correcta para tu estructura de carpetas
from configBD.mongo_manager import save_data 

# --- Broker Configuration (CLOUD) ---
# BROKER = "j72b9212.ala.us-east-1.emqxsl.com"
# PORT = 1883
BROKER = "localhost"
PORT = 1883

# TOPICOS DE DATOS (LECTURA DESDE ESP32)
TOPICS = [("ic/sensor/temp", 0), ("ic/sensor/humedad", 0)] 
# TOPICOS DE COMANDO (ESCRITURA HACIA ESP32)
TOPIC_UMBRAL_TEMP = "ic/umbral/temp"
TOPIC_UMBRAL_HUM = "ic/umbral/hum"


USERNAME = "user"
PASSWORD = "user"
# CA_CERT_PATH = "emqxsl-ca.crt"

# --- ALERT CONFIGURATION (VARIABLES GLOBALES MODIFICABLES) ---
HIGH_TEMP_THRESHOLD = 30.0 # Upper temperature limit (Red Alert)
LOW_TEMP_THRESHOLD = 15.0  # Lower temperature limit (Blue Alert)
HIGH_HUM_THRESHOLD = 90.0  # Humedad muy alta
LOW_HUM_THRESHOLD = 30.0   # Humedad muy baja

# --- CONFIGURACIÓN DE GUARDADO EN BD ---
DB_SAVE_INTERVAL_S = 300 # 300 segundos = 5 minutos
last_db_save_time = time.time()

# Circular buffers to store latest values
MAX_POINTS = 50
temps = deque(maxlen=MAX_POINTS)
hums = deque(maxlen=MAX_POINTS)
times = deque(maxlen=MAX_POINTS)
counter = 0
# Global variable for the last received value of each topic
last_temp = None
last_hum = None

# --- UI elements (Global access for update_plot and control function) ---
threshold_inputs = {} # Contiene los QLineEdit


# Callback when connected
def on_connect(client, userdata, flags, reason_code, properties=None):
    global last_db_save_time
    if reason_code == 0:
        print("Conectado exitosamente al broker MQTT en la nube.")
        for t in TOPICS:
            client.subscribe(t)
            print(f"Suscripto a {t[0]}")
        
        # Al conectar, enviamos los umbrales iniciales al ESP32 para sincronizar
        update_thresholds(initial_sync=True) 
        last_db_save_time = time.time() 
    else:
        print(f"Error de conexión. Código: {reason_code}")
        if reason_code == 5:
            print("Error: Autenticación fallida (Username/Password incorrectos).")

# Callback when a message arrives
def on_message(client, userdata, msg):
    global counter, last_temp, last_hum
    try:
        valor = float(msg.payload.decode())
        
        # Temporarily store the value in the last received variable
        if msg.topic == "ic/sensor/temp":
            last_temp = valor
        elif msg.topic == "ic/sensor/humedad":
            last_hum = valor
            
        # Synchronization Logic: Only add to the buffer if we have both data points
        if last_temp is not None and last_hum is not None:
            
            temps.append(last_temp)
            hums.append(last_hum)
            times.append(counter)
            counter += 1

            # --- GUARDAR EN MONGODB (Solo se llama a save_data, la frecuencia se controla en update_plot) ---
            # save_data(last_temp, last_hum) # COMENTADO AQUI, SE LLAMA EN update_plot()
            
            # Clear temporary variables to wait for the next pair of data
            last_temp = None
            last_hum = None
            
    except ValueError:
        print(f"Error: Mensaje recibido no es un número: {msg.payload.decode()}")

# --- NEW FUNCTION: CONTROL LOGIC (PUBLICAR UMBRALES) ---
def update_thresholds(initial_sync=False):
    global HIGH_TEMP_THRESHOLD, LOW_TEMP_THRESHOLD, HIGH_HUM_THRESHOLD, LOW_HUM_THRESHOLD

    if not initial_sync:
        try:
            # TRIES TO READ AND UPDATE TEMPERATURE THRESHOLDS FROM INPUTS
            new_high_temp = float(threshold_inputs['temp_high'].text())
            new_low_temp = float(threshold_inputs['temp_low'].text())
            
            if new_high_temp > new_low_temp and new_high_temp <= 100:
                 HIGH_TEMP_THRESHOLD = new_high_temp
                 LOW_TEMP_THRESHOLD = new_low_temp
            else:
                 print("ERROR: Umbral Alto Temp debe ser mayor que Bajo Temp (y <= 100). No publicado.")
                 return
    
            # TRIES TO READ AND UPDATE HUMIDITY THRESHOLDS FROM INPUTS
            new_high_hum = float(threshold_inputs['hum_high'].text())
            new_low_hum = float(threshold_inputs['hum_low'].text())
    
            if new_high_hum > new_low_hum and new_high_hum <= 100:
                 HIGH_HUM_THRESHOLD = new_high_hum
                 LOW_HUM_THRESHOLD = new_low_hum
            else:
                 print("ERROR: Umbral Alto Hum debe ser mayor que Bajo Hum (y <= 100). No publicado.")
                 return
                 
        except ValueError:
            print("ERROR: Ingrese valores numéricos válidos en los campos de umbral. No publicado.")
            return

    # PUBLICAR A MQTT
    temp_payload = f"{HIGH_TEMP_THRESHOLD:.1f},{LOW_TEMP_THRESHOLD:.1f}"
    hum_payload = f"{HIGH_HUM_THRESHOLD:.1f},{LOW_HUM_THRESHOLD:.1f}"
    
    client.publish(TOPIC_UMBRAL_TEMP, temp_payload)
    client.publish(TOPIC_UMBRAL_HUM, hum_payload)
    
    if not initial_sync:
        print(f"✅ Umbrales enviados al ESP32: Temp={temp_payload}, Hum={hum_payload}")


# Create MQTT client
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.username_pw_set(USERNAME, PASSWORD)

# TLS/SSL Security Configuration
# try:
#     client.tls_set(ca_certs=CA_CERT_PATH)
#     client.username_pw_set(USERNAME, PASSWORD)
# except FileNotFoundError:
#     print(f"ERROR: No se encontró el archivo de certificado CA en la ruta: {CA_CERT_PATH}")
#     sys.exit()

client.on_connect = on_connect
client.on_message = on_message

# Attempt connection
try:
    client.connect(BROKER, PORT, 60)
except Exception as e:
    print(f"Error al intentar la conexión: {e}")
    sys.exit()

# --- INTERFACE AND PLOT CONFIGURATION (pyqtgraph) ---

app = QtWidgets.QApplication([])
win = pg.GraphicsLayoutWidget(title="Monitor de Sensores MQTT (pyqtgraph)")
win.resize(800, 600)
win.setWindowTitle('Visualizador MQTT en Tiempo Real')

# =========================================================================
# Plot 1: TEMPERATURA
# =========================================================================
plot_temp = win.addPlot(title="Temperatura (°C)", row=0, col=0)
plot_temp.setLabel('left', "Temperatura", units='C')
plot_temp.setXRange(0, MAX_POINTS)
plot_temp.setYRange(0, 50) 
curve_temp = plot_temp.plot(pen='r')

# ALERTA FLOTANTE (TEMPERATURA) - OBJETO CENTRAL FIJO
alert_center_text_temp = pg.TextItem(
    html="<div style='background-color: rgba(255, 0, 0, 0.8); border: 2px solid red; padding: 10px; border-radius: 5px; color: white;'></div>",
    anchor=(0.5, 0.5)
)
plot_temp.addItem(alert_center_text_temp)
alert_center_text_temp.setVisible(False) 


# =========================================================================
# Plot 2: HUMEDAD
# =========================================================================
win.nextRow()
plot_hum = win.addPlot(title="Humedad (%)", row=1, col=0)
plot_hum.setLabel('left', "Humedad", units='%')
plot_hum.setXRange(0, MAX_POINTS)
plot_hum.setYRange(0, 100)
curve_hum = plot_hum.plot(pen='b')

# ALERTA FLOTANTE (HUMEDAD) - OBJETO CENTRAL FIJO
alert_center_text_hum = pg.TextItem(
    html="<div style='background-color: rgba(0, 0, 139, 0.8); border: 2px solid blue; padding: 10px; border-radius: 5px; color: white;'></div>",
    anchor=(0.5, 0.5)
)
plot_hum.addItem(alert_center_text_hum)
alert_center_text_hum.setVisible(False) 

# CORRECTION: Hide the 'A' axis label in the second plot (Humedad)
plot_hum.getAxis('left').setLabel(None)


# --- WIDGET DE CONTROL DE UMBRALES (INPUTS) ---
control_widget = QtWidgets.QWidget()
control_layout = QtWidgets.QHBoxLayout()

# Helper para crear etiquetas y campos de entrada
def create_threshold_input(label_text, default_value, key):
    label = QtWidgets.QLabel(label_text)
    line_edit = QtWidgets.QLineEdit(str(default_value))
    line_edit.setFixedWidth(60)
    control_layout.addWidget(label)
    control_layout.addWidget(line_edit)
    threshold_inputs[key] = line_edit

# Entradas para TEMPERATURA
control_layout.addWidget(QtWidgets.QLabel("--- UMBRALES DE ALARMA ---"))
create_threshold_input("Temp Alta (°C):", HIGH_TEMP_THRESHOLD, 'temp_high')
create_threshold_input("Temp Baja (°C):", LOW_TEMP_THRESHOLD, 'temp_low')
control_layout.addSpacing(20)

# Entradas para HUMEDAD
create_threshold_input("Hum Alta (%):", HIGH_HUM_THRESHOLD, 'hum_high')
create_threshold_input("Hum Baja (%):", LOW_HUM_THRESHOLD, 'hum_low')
control_layout.addSpacing(20)

# Botón de Aplicar
btn_apply = QtWidgets.QPushButton("Aplicar Umbrales")
btn_apply.clicked.connect(update_thresholds)
btn_apply.setStyleSheet("background-color: #3090FF; color: white; padding: 5px; border-radius: 5px;")

control_layout.addWidget(btn_apply)
control_widget.setLayout(control_layout)
# -----------------------------------------------

# Layout principal: Gráficos + Control
main_layout = QtWidgets.QVBoxLayout()
main_layout.addWidget(win)
main_layout.addWidget(control_widget)

main_container = QtWidgets.QWidget()
main_container.setLayout(main_layout)


# Update function for the animation (Called by QTimer)
def update_plot():
    global HIGH_TEMP_THRESHOLD, LOW_TEMP_THRESHOLD, HIGH_HUM_THRESHOLD, LOW_HUM_THRESHOLD, last_db_save_time

    # Solo dibujar si hay al menos un dato
    if len(temps) > 0 and len(temps) == len(hums): 
        # Convert from deque to numpy array for set_data
        y_temp = np.array(temps)
        y_hum = np.array(hums)
        # X axis is created with the current buffer length
        x = np.arange(len(y_temp)) 
        
        # GET VALUES
        current_temp = y_temp[-1]
        current_hum = y_hum[-1]
        
        # Get current view range to center the alert
        view_range_temp = plot_temp.getViewBox().viewRange()
        center_x_temp = (view_range_temp[0][0] + view_range_temp[0][1]) / 2
        center_y_temp = (view_range_temp[1][0] + view_range_temp[1][1]) / 2

        view_range_hum = plot_hum.getViewBox().viewRange()
        center_x_hum = (view_range_hum[0][0] + view_range_hum[0][1]) / 2
        center_y_hum = (view_range_hum[1][0] + view_range_hum[1][1]) / 2
        
        # ---------------------------------------------
        # 1. TEMPERATURE ALERT LOGIC (Central Flotante)
        # ---------------------------------------------
        temp_alert_text = ""
        temp_alert_style = ""
        
        if current_temp >= HIGH_TEMP_THRESHOLD:
            temp_alert_text = "ALERTA: TEMP ALTA"
            temp_alert_style = "background-color: rgba(255, 0, 0, 0.8); border: 2px solid red;"
            alert_center_text_temp.setVisible(True)
        
        elif current_temp <= LOW_TEMP_THRESHOLD:
            temp_alert_text = "AVISO: TEMP BAJA"
            temp_alert_style = "background-color: rgba(30, 144, 255, 0.8); border: 2px solid blue;"
            alert_center_text_temp.setVisible(True)

        else:
            temp_alert_text = ""
            alert_center_text_temp.setVisible(False)
            
        # Update the central TextItem (FLOTANTE TEMPERATURA)
        if temp_alert_text:
            temp_alert_html_content = f"<div style='{temp_alert_style} padding: 10px; border-radius: 5px; color: white; font-size: 16pt; font-weight: bold;'>{temp_alert_text}</div>"
            alert_center_text_temp.setHtml(temp_alert_html_content)
            alert_center_text_temp.setPos(center_x_temp, center_y_temp) # Center in the current view

        # ---------------------------------------------
        # 2. HUMIDITY ALERT LOGIC (Central Flotante)
        # ---------------------------------------------
        hum_alert_text = ""
        hum_alert_style = ""

        if current_hum >= HIGH_HUM_THRESHOLD:
            hum_alert_text = "ALERTA: HUM ALTA"
            hum_alert_style = "background-color: rgba(0, 0, 139, 0.8); border: 2px solid blue;"
            alert_center_text_hum.setVisible(True)

        elif current_hum <= LOW_HUM_THRESHOLD:
            hum_alert_text = "AVISO: HUM BAJA"
            hum_alert_style = "background-color: rgba(255, 165, 0, 0.8); border: 2px solid orange;"
            alert_center_text_hum.setVisible(True)
            
        else:
            hum_alert_text = ""
            alert_center_text_hum.setVisible(False)

        # Update the central TextItem (FLOTANTE HUMEDAD)
        if hum_alert_text:
            hum_alert_html_content = f"<div style='{hum_alert_style} padding: 10px; border-radius: 5px; color: white; font-size: 16pt; font-weight: bold;'>{hum_alert_text}</div>"
            alert_center_text_hum.setHtml(hum_alert_html_content)
            alert_center_text_hum.setPos(center_x_hum, center_y_hum) # Center in the current view
        
        # ---------------------------------------------
        # 3. UMBRALES COMPACTOS Y TÍTULOS
        # ---------------------------------------------

        # GET AND FORMAT CURRENT VALUE FOR TITLE 
        temp_value_html = f"<span style='color: yellow; font-size: 14pt;'>{current_temp:.1f} °C</span>"
        hum_value_html = f"<span style='color: yellow; font-size: 14pt;'>{current_hum:.1f} %</span>"

        # TEMPERATURA: Indicador de alerta en el título
        temp_title_indicator = f"<span style='color: red; font-size: 20pt; margin-left: 10px;'>•</span>" if temp_alert_text else ""
        temp_title = f"Temperatura (°C) {temp_value_html} {temp_title_indicator}"
        
        # HUMEDAD: Indicador de alerta en el título
        hum_title_indicator = f"<span style='color: blue; font-size: 20pt; margin-left: 10px;'>•</span>" if hum_alert_text else ""
        hum_title = f"Humedad (%) {hum_value_html} {hum_title_indicator}" 

        # UPDATE TITLES
        plot_temp.setTitle(temp_title)
        plot_hum.setTitle(hum_title)


        # Update curve data
        curve_temp.setData(x, y_temp)
        curve_hum.setData(x, y_hum)
        
        # Auto-range the X axis to follow the most recent point
        plot_temp.setXRange(x[-1] - MAX_POINTS + 1, x[-1] + 1, padding=0)
        plot_hum.setXRange(x[-1] - MAX_POINTS + 1, x[-1] + 1, padding=0)

        # ---------------------------------------------
        # 4. CONTROL DE FRECUENCIA DE GUARDADO EN BD
        # ---------------------------------------------
        current_time = time.time()
        # CORRECCIÓN CLAVE: La actualización del tiempo DEBE estar dentro del condicional.
        if current_time - last_db_save_time >= DB_SAVE_INTERVAL_S:
            # Solo guardamos el último par de datos sincronizado
            save_data(current_temp, current_hum)
            last_db_save_time = current_time # <--- ACTUALIZAR EL TIEMPO DESPUÉS DEL GUARDADO
            print(f"✅ Dato guardado en MongoDB ({DB_SAVE_INTERVAL_S}s).")
            

# Use QTimer to update the interface periodically (every 500ms)
timer = QtCore.QTimer()
timer.timeout.connect(update_plot)
timer.start(500) 

# Start MQTT in the background
client.loop_start()

print("Esperando mensajes... Cierra la ventana para terminar.")
# Muestra el contenedor principal que incluye gráficos y controles
main_container.show()
QtWidgets.QApplication.instance().exec() 

# Stop MQTT loop when graph is closed
client.loop_stop()
client.disconnect()