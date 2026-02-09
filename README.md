# 🌡️ Proyecto IC III: Sistema de Monitoreo y Control IoT

> **Control inteligente para Freezers e Incubadoras Universitarias**

Este repositorio aloja el código fuente y la documentación del proyecto final para la materia **Ingeniería en Computación III**. El sistema fue diseñado para optimizar la supervisión de equipos críticos en el laboratorio, garantizando la integridad de las muestras mediante un monitoreo constante y alertas en tiempo real.

## 🚀 Características Principales

El proyecto representa una evolución en la arquitectura de control, destacando las siguientes mejoras:

* **Conectividad en la Nube:** Migración completa del Broker MQTT local a una instancia en la nube, permitiendo monitoreo remoto.
* **Persistencia NoSQL:** Almacenamiento histórico de datos en **MongoDB**, ideal para el manejo de grandes volúmenes de datos no estructurados provenientes de sensores.
* **Interfaz de Gestión (GUI):** Aplicación de escritorio desarrollada en Python que permite a los usuarios:
    * 📉 Visualizar datos en tiempo real.
    * 🔔 Recibir y gestionar alertas críticas.
    * ⚙️ Modificar umbrales de temperatura/humedad dinámicamente.
    * 📊 Analizar el historial de mediciones.

## 🛠️ Tecnologías y Arquitectura

### Hardware
* **Microcontrolador:** ESP32.
* **Sensores:** DHT11.

### Comunicación y Backend
* **Protocolo:** MQTT (Message Queuing Telemetry Transport).
* **Broker:** EMQX.
* **Base de Datos:** MongoDB.

### Software de Control (Cliente)
* **Lenguaje:** Python.
* **GUI:** PyQtGraph.

## 🛠️ Guía de Instalación y Ejecución

Sigue estos pasos para levantar el entorno completo (Base de datos + Broker MQTT) y ejecutar la interfaz gráfica de usuario.

### 📋 Requisitos Previos
Asegúrate de tener instalado lo siguiente:
* [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Debe estar abierto y corriendo).
* [Python 3.x](https://www.python.org/downloads/).
* [Git](https://git-scm.com/downloads).

### 1. Clonar el Repositorio
Abre tu terminal y descarga el proyecto:

```bash
git clone [https://github.com/VainstubTomas/repositorioIngenieriaEnComputacion.git](https://github.com/VainstubTomas/repositorioIngenieriaEnComputacion.git)
cd repositorioIngenieriaEnComputacion
```

### 2. 🐳 Levantar servicios de Docker

Dirigirse a la dirección (path) "IC3/dockerConfig/" y ejecutar en la terminal el siguiente comando:

   ```bash
    docker-compose up -d
   ```

### 3. 🐍 Correr el script de Python

3.1. Ingresar a la carpeta IC3 donde se encuentra el archivo .py

3.2. Instalar dependencias:
Instala las librerías necesarias para la interfaz gráfica (PyQtGraph) y la conexión de datos abriendo la terminal y pegando el siguiente comando:

```bash
pip install paho-mqtt numpy pyqtgraph PyQt5 pymongo
```

3.3 Correr el script con el siguiente comando desde la terminal: 

```bash
python visualizadorGrafico.py
```
