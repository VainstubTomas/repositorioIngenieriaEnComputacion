import paho.mqtt.client as mqtt
import numpy as np # Necessary for pyqtgraph and efficient data handling
from collections import deque
import pyqtgraph as pg # Library for fast, real-time plotting
from pyqtgraph.Qt import QtWidgets, QtCore # For the desktop application

# --- Broker Configuration (CLOUD) ---
BROKER = "j72b9212.ala.us-east-1.emqxsl.com" # Cloud broker URL
PORT = 8883 # Secure port (SSL/TLS)

# CORRECTED TOPICS to match ESP32 publication
TOPICS = [("ic/sensor/temp", 0), ("ic/sensor/humedad", 0)] 

USERNAME = "user"
PASSWORD = "FinalPCI123"
CA_CERT_PATH = "emqxsl-ca.crt" # Name of the certificate file in the same folder

# --- ALERT CONFIGURATION ---
HIGH_TEMP_THRESHOLD = 30.0 # Upper temperature limit (Red Alert)
LOW_TEMP_THRESHOLD = 26.7  # Lower temperature limit (Blue Alert)


# Circular buffers to store latest values
MAX_POINTS = 50
temps = deque(maxlen=MAX_POINTS)
hums = deque(maxlen=MAX_POINTS)
times = deque(maxlen=MAX_POINTS)
counter = 0
# Global variable for the last received value of each topic
last_temp = None
last_hum = None

# Callback when connected
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Conectado exitosamente al broker MQTT en la nube.")
        for t in TOPICS:
            client.subscribe(t)
            print(f"Suscripto a {t[0]}")
    else:
        print(f"Error de conexión. Código: {rc}")
        if rc == 5:
            print("Error: Autenticación fallida (Username/Password incorrectos).")

# Callback when a message arrives
def on_message(client, userdata, msg):
    global counter, last_temp, last_hum
    try:
        valor = float(msg.payload.decode())
        
        # 1. Temporarily store the value in the last received variable
        if msg.topic == "ic/sensor/temp":
            last_temp = valor
        elif msg.topic == "ic/sensor/humedad":
            last_hum = valor
            
        # 2. Synchronization Logic: Only add to the buffer if we have both data points
        if last_temp is not None and last_hum is not None:
            
            temps.append(last_temp)
            hums.append(last_hum)
            times.append(counter)
            counter += 1
            
            print(f"[{msg.topic}] -> {valor} (Sincronizado)")
            
            # Clear temporary variables to wait for the next pair of data
            last_temp = None
            last_hum = None
            
        else:
             print(f"[{msg.topic}] -> {valor} (Esperando par)")

    except ValueError:
        print(f"Error: Mensaje recibido no es un número: {msg.payload.decode()}")

# Create MQTT client
client = mqtt.Client()

# TLS/SSL Security Configuration
try:
    client.tls_set(ca_certs=CA_CERT_PATH)
    client.username_pw_set(USERNAME, PASSWORD)
except FileNotFoundError:
    print(f"ERROR: No se encontró el archivo de certificado CA en la ruta: {CA_CERT_PATH}")
    exit()

client.on_connect = on_connect
client.on_message = on_message

# Attempt connection
try:
    client.connect(BROKER, PORT, 60)
except Exception as e:
    print(f"Error al intentar la conexión: {e}")
    exit()

# --- INTERFACE AND PLOT CONFIGURATION (pyqtgraph) ---

app = QtWidgets.QApplication([])
win = pg.GraphicsLayoutWidget(title="Monitor de Sensores MQTT (pyqtgraph)")
win.resize(800, 600)
win.setWindowTitle('Visualizador MQTT en Tiempo Real')

# Plot 1: Temperatura
plot_temp = win.addPlot(title="Temperatura (°C)", row=0, col=0)
plot_temp.setLabel('left', "Temperatura", units='C')
plot_temp.setXRange(0, MAX_POINTS)
plot_temp.setYRange(0, 50) 
curve_temp = plot_temp.plot(pen='r')

# --- ALERT ELEMENTS ---
# TextItem used to display the alert in the center of the plot
alert_center_text = pg.TextItem(
    html="<div style='background-color: rgba(255, 0, 0, 0.8); border: 2px solid red; padding: 10px; border-radius: 5px; color: white;'></div>",
    anchor=(0.5, 0.5) # Center the text
)
plot_temp.addItem(alert_center_text)
alert_center_text.setVisible(False)


# Plot 2: Humedad
plot_hum = win.addPlot(title="Humedad (%)", row=1, col=0)
plot_hum.setLabel('left', "Humedad", units='%')
plot_hum.setXRange(0, MAX_POINTS)
plot_hum.setYRange(0, 100)
curve_hum = plot_hum.plot(pen='b')

# CORRECTION: Hide the 'A' axis label in the second plot (Humedad)
# The correct method is setLabel(None) or setLabel('')
plot_hum.getAxis('left').setLabel(None)


# Update function for the animation (Called by QTimer)
def update_plot():
    # Only draw if the buffers have the same length (guaranteed by on_message)
    if len(temps) > 0 and len(temps) == len(hums): 
        # Convert from deque to numpy array for set_data
        y_temp = np.array(temps)
        y_hum = np.array(hums)
        # X axis is created with the current buffer length
        x = np.arange(len(y_temp)) 
        
        # GET VALUES
        current_temp = y_temp[-1]
        current_hum = y_hum[-1]
        current_x = x[-1]
        
        # Get current view range to center the alert
        view_range = plot_temp.getViewBox().viewRange()
        center_x = (view_range[0][0] + view_range[0][1]) / 2
        center_y = (view_range[1][0] + view_range[1][1]) / 2
        
        # ---------------------------------------------
        # TEMPERATURE ALERT LOGIC
        # ---------------------------------------------
        alert_text = ""
        alert_style = ""
        
        # 1. RED Alert (High Temperature)
        if current_temp >= HIGH_TEMP_THRESHOLD:
            alert_text = "ALERTA: TEMPERATURA ALTA!"
            alert_style = "background-color: rgba(255, 0, 0, 0.8); border: 2px solid red;"
            alert_center_text.setVisible(True)
        
        # 2. BLUE Alert (Low Temperature)
        elif current_temp <= LOW_TEMP_THRESHOLD:
            alert_text = "AVISO: TEMPERATURA BAJA!"
            alert_style = "background-color: rgba(30, 144, 255, 0.8); border: 2px solid blue;"
            alert_center_text.setVisible(True)

        # 3. Normal
        else:
            alert_text = ""
            alert_center_text.setVisible(False)
        
        # ---------------------------------------------
        # TITLE AND CENTRAL ALERT UPDATE
        # ---------------------------------------------

        # Update the central TextItem
        if alert_text:
            alert_html_content = f"<div style='{alert_style} padding: 10px; border-radius: 5px; color: white; font-size: 16pt; font-weight: bold;'>{alert_text}</div>"
            alert_center_text.setHtml(alert_html_content)
            alert_center_text.setPos(center_x, center_y) # Center in the current view

        # GET AND FORMAT CURRENT VALUE FOR TITLE (WITHOUT FULL ALERT TEXT)
        temp_value_html = f"<span style='color: yellow; font-size: 14pt;'>{current_temp:.1f} °C</span>"
        
        # If there is an alert, the indicator in the title should be subtle (e.g., a red dot)
        title_alert_indicator = ""
        if alert_text:
             title_alert_indicator = f"<span style='color: red; font-size: 20pt; margin-left: 10px;'>•</span>"

        temp_title = f"Temperatura (°C) {temp_value_html} {title_alert_indicator}"
        hum_title = f"Humedad (%) <span style='color: yellow; font-size: 14pt;'>{current_hum:.1f} %</span>"

        # UPDATE TITLES WITH VALUES
        plot_temp.setTitle(temp_title)
        plot_hum.setTitle(hum_title)

        # Update curve data
        curve_temp.setData(x, y_temp)
        curve_hum.setData(x, y_hum)
        
        # Auto-range the X axis to follow the most recent point
        plot_temp.setXRange(x[-1] - MAX_POINTS + 1, x[-1] + 1, padding=0)
        plot_hum.setXRange(x[-1] - MAX_POINTS + 1, x[-1] + 1, padding=0)


# Use QTimer to update the interface periodically (every 500ms)
timer = QtCore.QTimer()
timer.timeout.connect(update_plot)
timer.start(500) 

# Start MQTT in the background
client.loop_start()

print("Esperando mensajes... Cierra la ventana para terminar.")
win.show()
QtWidgets.QApplication.instance().exec() 

# Stop MQTT loop when graph is closed
client.loop_stop()
client.disconnect()