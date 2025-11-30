#include <WiFi.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <DHT.h>
#include <WiFiClientSecure.h>

WiFiClientSecure espClient;

// def y config DHT11
#define DHTPIN 23
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

// def LEDs
#define LED_ROJO 22
#define LED_VERDE 21
#define LED_ALERTA_ROJA_TEMP 12 
#define LED_ALERTA_AZUL_TEMP 14
#define LED_ALERTA_ROJA_HUM 27 
#define LED_ALERTA_AZUL_HUM 26

// UMBRALES DE TEMPERATURA Y HUEMDAD PARA ALERTAS
volatile float UMBRAL_ALTO = 30.0;
volatile float UMBRAL_BAJO = 15.0;
volatile float UMBRAL_ALTO_HUM = 90.0;
volatile float UMBRAL_BAJO_HUM = 30.0;

// TOPICOS DE COMANDO (Debe coincidir con Python)
const char* TOPIC_UMBRAL_TEMP = "ic/umbral/temp";
const char* TOPIC_UMBRAL_HUM = "ic/umbral/hum";

PubSubClient client(espClient);
long lastMsg = 0;
char msg[50];
int value = 0;

float Temperatura = 0;
float Humedad = 0;

// config internet
const char* ssid = "TP-Link_6D76";
const char* password = "55500722";

// config mqtt
// dir mqtt broker ip adreess
const char* mqtt_server = "j72b9212.ala.us-east-1.emqxsl.com";
const char* mqtt_user = "user";        // Tu Username
const char* mqtt_password = "FinalPCI123"; // Tu Password

// certificado broker
const char* EMQX_CA_CERT = R"EOF(
-----BEGIN CERTIFICATE-----
MIIDjjCCAnagAwIBAgIQAzrx5qcRqaC7KGSxHQn65TANBgkqhkiG9w0BAQsFADBh
MQswCQYDVQQGEwJVUzEVMBMGA1UEChMMRGlnaUNlcnQgSW5jMRkwFwYDVQQLExB3
d3cuZGlnaWNlcnQuY29tMSAwHgYDVQQDExdEaWdpQ2VydCBHbG9iYWwgUm9vdCBH
MjAeFw0xMzA4MDExMjAwMDBaFw0zODAxMTUxMjAwMDBaMGExCzAJBgNVBAYTAlVT
MRUwEwYDVQQKEwxEaWdpQ2VydCBJbmMxGTAXBgNVBAsTEHd3dy5kaWdpY2VydC5j
b20xIDAeBgNVBAMTF0RpZ2lDZXJ0IEdsb2JhbCBSb290IEcyMIIBIjANBgkqhkiG
9w0BAQEFAAOCAQ8AMIIBCgKCAQEAuzfNNNx7a8myaJCtSnX/RrohCgiN9RlUyfuI
2/Ou8jqJkTx65qsGGmvPrC3oXgkkRLpimn7Wo6h+4FR1IAWsULecYxpsMNzaHxmx
1x7e/dfgy5SDN67sH0NO3Xss0r0upS/kqbitOtSZpLYl6ZtrAGCSYP9PIUkY92eQ
q2EGnI/yuum06ZIya7XzV+hdG82MHauVBJVJ8zUtluNJbd134/tJS7SsVQepj5Wz
tCO7TG1F8PapspUwtP1MVYwnSlcUfIKdzXOS0xZKBgyMUNGPHgm+F6HmIcr9g+UQ
vIOlCsRnKPZzFBQ9RnbDhxSJITRNrw9FDKZJobq7nMWxM4MphQIDAQABo0IwQDAP
BgNVHRMBAf8EBTADAQH/MA4GA1UdDwEB/wQEAwIBhjAdBgNVHQ4EFgQUTiJUIBiV
5uNu5g/6+rkS7QYXjzkwDQYJKoZIhvcNAQELBQADggEBAGBnKJRvDkhj6zHd6mcY
1Yl9PMWLSn/pvtsrF9+wX3N3KjITOYFnQoQj8kVnNeyIv/iPsGEMNKSuIEyExtv4
NeF22d+mQrvHRAiGfzZ0JFrabA0UWTW98kndth/Jsw1HKj2ZL7tcu7XUIOGZX1NG
Fdtom/DzMNU+MeKNhJ7jitralj41E6Vf8PlwUHBHQRFXGU7Aj64GxJUTFy8bJZ91
8rGOmaFvE7FBcf6IKshPECBV1/MUReXgRPTqh5Uykw7+U0b6LJ3/iyK5S9kJRaTe
pLiaWN0bfVKfjllDiIGknibVb63dDcY3fe0Dkhvld1927jyNxF1WW6LZZm6zNTfl
MrY=
-----END CERTIFICATE-----
)EOF";

// --- NUEVA FUNCIÓN: PARSING DE MENSAJES (ALTO, BAJO) ---
void parseThresholds(String payload, volatile float &high_ref, volatile float &low_ref, const char* label) {
    int commaIndex = payload.indexOf(',');
    
    if (commaIndex > 0) {
        String highString = payload.substring(0, commaIndex);
        String lowString = payload.substring(commaIndex + 1);
        
        float new_high = highString.toFloat();
        float new_low = lowString.toFloat();
        
        // Validación básica
        if (new_high > new_low) { // Eliminamos <= 100.0 ya que la humedad puede ser 100%
            high_ref = new_high;
            low_ref = new_low;
            Serial.print("Umbrales ");
            Serial.print(label);
            Serial.print(" actualizados: ALTO=");
            Serial.print(high_ref);
            Serial.print(", BAJO=");
            Serial.println(low_ref);
        } else {
            Serial.print("ERROR: Valores de umbral inválidos (Alto <= Bajo) para ");
            Serial.println(label);
        }
    } else {
        Serial.print("ERROR: Formato de mensaje de umbral incorrecto (Falta coma) para ");
        Serial.println(label);
    }
}

void setup() {
  Serial.begin(115200);
  setup_wifi();
  espClient.setCACert(EMQX_CA_CERT);
  client.setServer(mqtt_server, 8883);
  client.setCallback(callback);
  //dht11
  dht.begin();
  
  //leds (Pines digitales para Rojo y Verde)
  pinMode(LED_ROJO, OUTPUT);
  pinMode(LED_VERDE, OUTPUT);
  pinMode(LED_ALERTA_ROJA_TEMP, OUTPUT);
  pinMode(LED_ALERTA_AZUL_TEMP, OUTPUT);
  pinMode(LED_ALERTA_ROJA_HUM, OUTPUT);
  pinMode(LED_ALERTA_AZUL_HUM, OUTPUT);
  
  // Estado inicial leds
  digitalWrite(LED_ROJO, HIGH);// Rojo encendido por default (indicando no conectado)
  digitalWrite(LED_VERDE, LOW);// Verde apagado
  digitalWrite(LED_ALERTA_AZUL_TEMP, LOW);
  digitalWrite(LED_ALERTA_ROJA_TEMP, LOW);
  digitalWrite(LED_ALERTA_AZUL_HUM, LOW);
  digitalWrite(LED_ALERTA_ROJA_HUM, LOW);
}

void setup_wifi(){
  delay(10);
  Serial.println();
  Serial.print("conectado a");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  while(WiFi.status() != WL_CONNECTED){
    delay(500);
    Serial.print(".");
    }
    Serial.println("");
    Serial.println("WiFi conectado");
    Serial.println("IP ADRESS:");
    Serial.println(WiFi.localIP());
}

//realiza conexiòn mqtt (suscriptor empieza a recibir datos)
void callback(char* topic, byte* message, unsigned int length){
    
  // Impresión de mensaje recibido
  Serial.print("Mensaje recibido en topic: ");
  Serial.print(topic);
  Serial.print(", message: ");
  
  String messageTemp;
  for (int i = 0; i < length; i++ ){
    Serial.print((char)message[i]);
    messageTemp += (char)message[i];
   }
  Serial.println();

  // ------------------------------------------
  // LÓGICA DE ACTUALIZACIÓN DE UMBRALES
  // ------------------------------------------
  
  // Si el tópico es de Temperatura
  if (strcmp(topic, TOPIC_UMBRAL_TEMP) == 0) {
      parseThresholds(messageTemp, UMBRAL_ALTO, UMBRAL_BAJO, "TEMP");
  }
  // Si el tópico es de Humedad
  else if (strcmp(topic, TOPIC_UMBRAL_HUM) == 0) {
      parseThresholds(messageTemp, UMBRAL_ALTO_HUM, UMBRAL_BAJO_HUM, "HUM");
  }
}

// realiza la reconexiòn en caso de fallo
void reconnect (){
  while (!client.connected()){
    Serial.print("intentando conexiòn MQTT");
    
    if (client.connect ("ESP32 client", mqtt_user, mqtt_password)){
      Serial.println("conectado");

      // Cambiar LEDs
      digitalWrite(LED_ROJO, LOW);  
      digitalWrite(LED_VERDE, HIGH);  
      //sub a topicos
      client.subscribe(TOPIC_UMBRAL_TEMP);
      client.subscribe(TOPIC_UMBRAL_HUM);
      } else {
        Serial.print ("fallo, rc=");
        Serial.print (client.state());
        Serial.println ("intente en 5s");

        //mantenemos estado o retornamos a los leds
        digitalWrite(LED_ROJO, HIGH);  
        digitalWrite(LED_VERDE, LOW);    
        
        delay (5000);
        }
    }
  }

//reliza conexiòn MQTT (publicador envìa datos)
void loop() {
  // put your main code here, to run repeatedly:
  if (!client.connected()){
    reconnect();
    }
  client.loop();
  long now = millis ();
  if (now-lastMsg>1000){ //tiempo de muestreo 1000 ms (1 segundo)
    lastMsg=now;
    
      // Leer temperatura y humedad desde el DHT11
    float Temperatura = dht.readTemperature();
    float Humedad = dht.readHumidity();
    
      // Verificar si la lectura es válida
    if (isnan(Temperatura)|| isnan(Humedad)) {
      Serial.println("Error al leer del DHT11!");
      return;
    }

     // ------------------------------------------
    // LÓGICA DE CONTROL DE LEDS DE ALERTA TEMPERATURA
    // ------------------------------------------
      if (Temperatura >= UMBRAL_ALTO) {
          // Alerta ROJA (Temperatura Alta)
          digitalWrite(LED_ALERTA_ROJA_TEMP, HIGH);
          digitalWrite(LED_ALERTA_AZUL_TEMP, LOW);
          Serial.println(">>> ALERTA ROJA: TEMPERATURA ALTA");
      } else if (Temperatura <= UMBRAL_BAJO) {
          // Alerta AZUL (Temperatura Baja)
          digitalWrite(LED_ALERTA_ROJA_TEMP, LOW);
          digitalWrite(LED_ALERTA_AZUL_TEMP, HIGH);
          Serial.println(">>> ALERTA AZUL: TEMPERATURA BAJA");
      } else {
          // Rango normal: ambos apagados
          digitalWrite(LED_ALERTA_ROJA_TEMP, LOW);
          digitalWrite(LED_ALERTA_AZUL_TEMP, LOW);
      }

       // ------------------------------------------
    // 2. LÓGICA DE CONTROL DE LEDS DE HUMEDAD
    // ------------------------------------------
      if (Humedad >= UMBRAL_ALTO_HUM) {
          // Alerta ROJA (Humedad Alta)
          digitalWrite(LED_ALERTA_ROJA_HUM, HIGH);
          digitalWrite(LED_ALERTA_AZUL_HUM, LOW);
          Serial.println(">>> ALERTA ROJA: HUMEDAD ALTA");
      } else if (Humedad <= UMBRAL_BAJO_HUM) {
          // Alerta AZUL (Humedad Baja)
          digitalWrite(LED_ALERTA_ROJA_HUM, LOW);
          digitalWrite(LED_ALERTA_AZUL_HUM, HIGH);
          Serial.println(">>> ALERTA AZUL: HUMEDAD BAJA");
      } else {
          // Rango normal: ambos apagados
          digitalWrite(LED_ALERTA_ROJA_HUM, LOW);
          digitalWrite(LED_ALERTA_AZUL_HUM, LOW);
      }

      // Mostrar en el monitor serial
    Serial.print("Temperatura: ");
    Serial.print(Temperatura);
    Serial.print(" °C  |  Humedad: ");
    Serial.print(Humedad);
    Serial.println(" %");

    //publicamos temperatura
    char tempString[8];
    dtostrf(Temperatura, 1, 2, tempString);
    client.publish("ic/sensor/temp", tempString);
    
    //Publicar humedad
    char humString[8];
    dtostrf(Humedad, 1, 2, humString);
    client.publish("ic/sensor/humedad", humString);
  }
}
