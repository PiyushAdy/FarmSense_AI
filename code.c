
#include <SoftwareSerial.h>
#include <DHT.h>


#define MOISTURE_SENSOR_PIN A0    
#define LDR_SENSOR_PIN A1         
#define MOISTURE_SENSOR_POWER 7   
#define DHTPIN 8                  
#define DHTTYPE DHT11             
#define BT_RX 10                  
#define BT_TX 11                  
#define LDR_SENSOR_GND 4    


SoftwareSerial BTSerial(BT_RX, BT_TX); 
DHT dht(DHTPIN, DHTTYPE);

int moistureValue = 0;      
int ldrValue = 0;           
float temperature = 0;      
float humidity = 0;         
unsigned long previousMillis = 0;
const long interval = 5000; 

void setup() {
  Serial.begin(9600);
  BTSerial.begin(9600);
  dht.begin();
  pinMode(MOISTURE_SENSOR_POWER, OUTPUT);
  pinMode(LDR_SENSOR_GND, OUTPUT);
  digitalWrite(LDR_SENSOR_GND, LOW); 
  digitalWrite(MOISTURE_SENSOR_POWER,LOW); //keeping low to save power and to avoid uncertain behaviours
  // Waiting to initialize all the sensors
  delay(2000);
  Serial.println("ALL Sensors have been successfully initialized");
}

void loop() {
  unsigned long currentMillis = millis();
  
  // Check if it's time to take readings
  if (currentMillis - previousMillis >= interval) {
    previousMillis = currentMillis;
    
    digitalWrite(MOISTURE_SENSOR_POWER,HIGH);
    delay(1000);
    moistureValue = analogRead(MOISTURE_SENSOR_PIN);
    digitalWrite(MOISTURE_SENSOR_POWER,LOW);
    int moisturePercent = map(moistureValue, 1023, 0, 0, 100);
    // int moisturePercent = (int)moistureValue;

    ldrValue = analogRead(LDR_SENSOR_PIN);
    int lightPercent = map(ldrValue, 1023, 0, 0, 100);
    
    humidity = dht.readHumidity();
    temperature = dht.readTemperature(); // temp is in Celsius
    if (isnan(humidity) || isnan(temperature)) {
      Serial.println("Failed to read from DHT sensor!");
      humidity = 0;
      temperature = 0;
    }
    
    Serial.println("Sensor Readings:");
    Serial.print("Soil Moisture: ");
    Serial.print(moisturePercent);
    Serial.println("%");
    
    Serial.print("Light Level: ");
    Serial.print(lightPercent);
    Serial.println("%");
    
    Serial.print("Temperature: ");
    Serial.print(temperature);
    Serial.println(" C");
    
    Serial.print("Humidity: ");
    Serial.print(humidity);
    Serial.println("%");
    Serial.println("-------------------");
    
    // Send data over Bluetooth in JSON format
    BTSerial.print("{");
    BTSerial.print("\"moisture\":");
    BTSerial.print(moisturePercent);
    BTSerial.print(",\"light\":");
    BTSerial.print(lightPercent);
    BTSerial.print(",\"temp\":");
    BTSerial.print(temperature);
    BTSerial.print(",\"humidity\":");
    BTSerial.print(humidity);
    BTSerial.println("}");
  }
}
