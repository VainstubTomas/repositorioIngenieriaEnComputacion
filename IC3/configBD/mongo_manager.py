import datetime
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure

# --- CONFIGURACIÓN DE MONGODB ---
# user:user es el usuario:contraseña
MONGO_URI = "mongodb+srv://user:user@valoressensados.yuszhtm.mongodb.net/sensados_ic_3?appName=ValoresSensados"
#DESCOMENTAR PARA USAR DOCKER
#MONGO_URI = "mongodb://localhost:27017/"
DATABASE_NAME = "sensados_ic_3"
COLLECTION_NAME = "sensor_data"

# Variables globales para el cliente y la colección
client = None
collection = None

def initialize_mongodb():
    """Intenta inicializar la conexión con MongoDB Atlas."""
    global client, collection
    try:
        if client is None:
            # Conexión con un timeout corto
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            
            # Prueba la conexión obteniendo el nombre de la base de datos
            client.admin.command('ping') 
            
            db = client[DATABASE_NAME]
            collection = db[COLLECTION_NAME]
            print(f"Conexión exitosa a MongoDB: Base de Datos '{DATABASE_NAME}'")
        return True
    
    except ConnectionFailure as e:
        print(f"ERROR de Conexión a MongoDB (Timeout): {e}")
        return False
    except Exception as e:
        print(f"ERROR Inesperado al inicializar MongoDB: {e}")
        return False

def save_data(temp_value, hum_value):
    """
    Recibe los valores de temperatura y humedad, crea un documento 
    con marca de tiempo y lo inserta en la colección.
    """
    global collection
    
    # Asegurar que la colección esté lista
    if collection is None:
        if not initialize_mongodb():
            print("ERROR: No se pudo guardar el dato, la conexión a MongoDB falló.")
            return

    # Crear el documento JSON/BSON
    data_document = {
        "timestamp": datetime.datetime.now(),
        "temperatura_c": temp_value,
        "humedad_porcentaje": hum_value,
        "source_device": "ESP32_DHT11",
        "unidad": "IC3"
    }
    
    # Inserción de datos en la BD
    try:
        result = collection.insert_one(data_document)
        return True
    except OperationFailure as e:
        print(f"ERROR de Operación al insertar dato en MongoDB: {e}")
        return False
    except Exception as e:
        print(f"ERROR desconocido al guardar dato: {e}")
        return False

# Inicializar la conexión al cargar el módulo
initialize_mongodb()