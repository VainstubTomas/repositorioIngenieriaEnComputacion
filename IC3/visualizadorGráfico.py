import paho.mqtt.client as mqtt
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque

# Configuración del broker
BROKER = "192.168.0.109"  # IP de tu Raspberry Pi con Mosquitto
PORT = 1883
TOPICS = [("esp32/temperatura", 0), ("esp32/humedad", 0)]

# Buffers circulares para almacenar últimos valores
MAX_POINTS = 50
temps = deque(maxlen=MAX_POINTS)
hums = deque(maxlen=MAX_POINTS)
times = deque(maxlen=MAX_POINTS)
counter = 0

# Callback cuando se conecta
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Conectado al broker MQTT")
        for t in TOPICS:
            client.subscribe(t)
            print(f"Suscripto a {t[0]}")
    else:
        print("Error de conexión. Código:", rc)

# Callback cuando llega un mensaje
def on_message(client, userdata, msg):
    global counter
    valor = float(msg.payload.decode())
    if msg.topic == "esp32/temperatura":
        temps.append(valor)
        times.append(counter)
    elif msg.topic == "esp32/humedad":
        hums.append(valor)
    counter += 1
    print(f"[{msg.topic}] -> {valor}")

# Crear cliente MQTT
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT, 60)

# --- Configuración del gráfico ---
fig, ax = plt.subplots(2, 1, figsize=(8,6))
ax[0].set_title("Temperatura (°C)")
ax[1].set_title("Humedad (%)")

line_temp, = ax[0].plot([], [], "r-o", label="Temperatura")
line_hum, = ax[1].plot([], [], "b-o", label="Humedad")

for a in ax:
    a.set_xlim(0, MAX_POINTS)
    a.set_ylim(0, 100)
    a.legend()
    a.grid(True)

# Función de actualización para la animación
def update(frame):
    if len(times) > 0:
        line_temp.set_data(range(len(temps)), list(temps))
        line_hum.set_data(range(len(hums)), list(hums))
        ax[0].set_xlim(0, len(temps))
        ax[1].set_xlim(0, len(hums))
    return line_temp, line_hum

ani = animation.FuncAnimation(fig, update, interval=1000)

# Iniciar MQTT en segundo plano
client.loop_start()

print("Esperando mensajes... Cierra la ventana del gráfico para terminar.")
plt.tight_layout()
plt.show()

# Al cerrar el gráfico, detener MQTT
client.loop_stop()
client.disconnect()
