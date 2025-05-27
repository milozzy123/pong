#include <WiFi.h>
#include <esp_now.h>
#include <PubSubClient.h>

// --------------- Wi-Fi Configuration ---------------
const char* ssid = "E109-E110";
const char* password = "DBHaacht24"; 

// --------------- MQTT Broker Configuration ---------------
const char* mqttServerIp = "192.168.0.157";
const int mqttPort = 1883; // Default MQTT port
const char* mqttTopic = "GAME/milo";
const char* mqttClientIdBase = "esp32-pong-receiver-"; // Base for unique client ID

// --------------- Global Objects ---------------
WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

// --------------- ESP-NOW Callback ---------------
// Function to be executed when ESP-NOW data is received
void OnDataRecv(const esp_now_recv_info_t *esp_now_info, const uint8_t *incomingData, int len) {
  Serial.print("ESP-NOW Packet from: ");
  char macStr[18];
  snprintf(macStr, sizeof(macStr), "%02x:%02x:%02x:%02x:%02x:%02x",
           esp_now_info->src_addr[0], esp_now_info->src_addr[1], esp_now_info->src_addr[2],
           esp_now_info->src_addr[3], esp_now_info->src_addr[4], esp_now_info->src_addr[5]);
  Serial.print(macStr);

  // Create a buffer to hold the incoming data as a C-string
  char dataBuffer[len + 1];
  memcpy(dataBuffer, incomingData, len);
  dataBuffer[len] = '\0'; // Null-terminate the string

  Serial.print(" | Data: ");
  Serial.print(dataBuffer);

  // Publish to MQTT if connected
  if (mqttClient.connected()) {
    if (mqttClient.publish(mqttTopic, dataBuffer)) {
      Serial.println(" | Published to MQTT");
    } else {
      Serial.println(" | MQTT Publish Failed!");
    }
  } else {
    Serial.println(" | MQTT Not Connected - Cannot Publish.");
  }
}

// --------------- MQTT Helper Functions ---------------
void setupMQTT() {
  mqttClient.setServer(mqttServerIp, mqttPort);
  // mqttClient.setCallback(mqttCallback); // We are not subscribing, so callback not strictly needed
                                        // but good practice if you ever add subscriptions.
  String clientId = mqttClientIdBase + String(random(0xffff), HEX);
  Serial.print("Attempting MQTT connection with Client ID: ");
  Serial.println(clientId);
}

void reconnectMQTT() {
  // Loop until we're reconnected
  while (!mqttClient.connected()) {
    Serial.print("Attempting MQTT connection...");
    String clientId = mqttClientIdBase + String(random(0xffff), HEX); // Generate unique client ID
    // Attempt to connect
    if (mqttClient.connect(clientId.c_str())) {
      Serial.println("connected to MQTT Broker!");
      // You could publish a "connected" message if desired
      // mqttClient.publish(mqttTopic, "ReceiverOnline"); 
    } else {
      Serial.print("failed, rc=");
      Serial.print(mqttClient.state());
      Serial.println(" try again in 5 seconds");
      // Wait 5 seconds before retrying
      delay(5000);
    }
  }
}

// void mqttCallback(char* topic, byte* payload, unsigned int length) {
//   // Handle incoming MQTT messages here if you subscribe to topics
//   Serial.print("Message arrived [");
//   Serial.print(topic);
//   Serial.print("] ");
//   for (int i = 0; i < length; i++) {
//     Serial.print((char)payload[i]);
//   }
//   Serial.println();
// }

// --------------- Setup Function ---------------
void setup() {
  Serial.begin(115200);
  Serial.println("\nESP32 ESP-NOW to MQTT Gateway");

  // 1. Connect to Wi-Fi
  Serial.print("Connecting to WiFi: ");
  Serial.println(ssid);
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  int wifi_retry_count = 0;
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    wifi_retry_count++;
    if (wifi_retry_count > 20) { // Timeout after 10 seconds
        Serial.println("\nFailed to connect to WiFi. Please check credentials or network.");
        // You might want to restart or enter a deep sleep here
        ESP.restart(); 
    }
  }
  Serial.println("\nWiFi connected!");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());

  // 2. Setup MQTT
  setupMQTT();
  // Note: reconnectMQTT() will be called in loop() to establish initial connection

  // 3. Initialize ESP-NOW (after WiFi is connected to use the same channel)
  if (esp_now_init() != ESP_OK) {
    Serial.println("Error initializing ESP-NOW");
    return;
  }
  esp_now_register_recv_cb(OnDataRecv);
  Serial.println("ESP-NOW Initialized. Waiting for data...");
  Serial.print("This ESP32's MAC Address (for sender config): ");
  Serial.println(WiFi.macAddress());
}

// --------------- Loop Function ---------------
void loop() {
  if (!mqttClient.connected()) {
    reconnectMQTT();
  }
  mqttClient.loop(); // Allow the MQTT client to process incoming messages and maintain connection

  // Other tasks can go here, but keep them non-blocking or short
  // to allow MQTT and ESP-NOW to function smoothly.
  delay(10); // Small delay
}