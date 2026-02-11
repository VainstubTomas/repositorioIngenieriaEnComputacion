import paho.mqtt.client as mqtt
import time
import random

BROKER = "emqx" 
PORT = 1883

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.username_pw_set("user", "user")

# --- LÓGICA DE REINTENTO ROBUSTA ---
connected = False
while not connected:
    try:
        print(f"Intentando conectar al broker en {BROKER}:{PORT}...")
        client.connect(BROKER, PORT, 60)
        connected = True
        print("✅ Conectado al broker desde el simulador")
    except Exception as e:
        print(f"❌ Error de conexión: {e}. Reintentando en 5 segundos...")
        time.sleep(5)

# Iniciar el loop en segundo plano
client.loop_start()

try:
    while True:
        temp = round(random.uniform(20.0, 30.0), 2)
        hum = round(random.uniform(40.0, 70.0), 2)
        
        client.publish("unraf/48E729B45E88/temp", str(temp))
        client.publish("unraf/48E729B45E88/hum", str(hum))
        
        print(f"Publicando -> Temp: {temp}, Hum: {hum}")
        time.sleep(2)
except KeyboardInterrupt:
    client.disconnect()