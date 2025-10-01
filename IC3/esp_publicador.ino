#include<WiFi.h>
#include<PubSubClient.h>
#include<Wire.h>
#include <DHT.h>

//def y config DHT11
#define DHTPIN 23       
#define DHTTYPE DHT11   
DHT dht(DHTPIN, DHTTYPE);
//def LEDs
#define LED_ROJO 22
#define LED_VERDE 21

WiFiClient espClient;
PubSubClient client(espClient);
long lastMsg=0;
char msg[50];
int value=0;

float Temperatura=0;
float Humedad=0;

//config internet
const char* ssid="TP-Link_6D76";
const char*password="55500722";
//config mqtt
//dir mqtt broker ip adreess
const char* mqtt_server="192.168.0.109";

void setup() {
  Serial.begin(115200);
  setup_wifi();
  client.setServer(mqtt_server,1883);
  client.setCallback(callback);
  //dht11
  dht.begin();
  //leds
  pinMode(LED_ROJO, OUTPUT);
  pinMode(LED_VERDE, OUTPUT);
    // Estado inicial leds
  digitalWrite(LED_ROJO, HIGH);   
  digitalWrite(LED_VERDE, LOW);   
}

void setup_wifi(){
  delay(10);
  Serial.println();
  Serial.print("conectado a");
  Serial.println(ssid);
  WiFi.begin(ssid,password);
  while(WiFi.status()!=WL_CONNECTED){
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
  Serial.print ("Mensaje recibido en topic: ");
  Serial.print (topic); 
  Serial.print (", message: "); 
  String messageTemp;
  for (int i = 0; i<length; i++ ){
    Serial.print ((char)message[i]);
    messageTemp+=(char)message[i];
   }
  Serial.println(); 
  //si necesitamos que nuestro publicador (ESP) tambien reciba datos
  //Primer output temperatura - topic: esp32/output/temperatura
  //Segundo output temperatura - topic: esp32/output/humedad
  }

 // realiza la reconexiòn en caso de fallo
void reconnect (){
  while (!client.connected()){
    Serial.print("intentando conexiòn MQTT");
    
    if (client.connect ("ESP32 client")){
      Serial.println("conectado");

      // Cambiar LEDs
      digitalWrite(LED_ROJO, LOW); 
      digitalWrite(LED_VERDE, HIGH); 
      
      client.subscribe ("esp32/output/temperatura");
      client.subscribe ("esp32/output/humedad");
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
  if (now-lastMsg>1000){ //tiempo de muestreo 100 ms 
    lastMsg=now;
    
     // Leer temperatura y humedad desde el DHT11
    float Temperatura = dht.readTemperature();
    float Humedad = dht.readHumidity();
    
     // Verificar si la lectura es válida
    if (isnan(Temperatura)|| isnan(Humedad)) {
      Serial.println("Error al leer del DHT11!");
      return;
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
    client.publish("esp32/temperatura", tempString);
    
    // Publicar humedad
    char humString[8];
    dtostrf(Humedad, 1, 2, humString);
    client.publish("esp32/humedad", humString);
  }
}
