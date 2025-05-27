#include <esp_now.h>
#include <WiFi.h>

// DEFINE THE PINS FOR THE BUTTONS
const int button1Pin = 23; // GPIO23
const int button2Pin = 22; // GPIO22

// MAC Address of the receiver ESP32
uint8_t receiverMacAddress[] = {0x1C, 0x69, 0x20, 0xCD, 0x8B, 0x04}; // Use YOUR receiver's MAC

// Structure to hold data to be sent
char messageToSend[4]; // "X;X" + null terminator ("0;0\0")
char lastMessageSent[4] = ""; // Store the last successfully sent message

// Peer info
esp_now_peer_info_t peerInfo;

// Variables for button debouncing
// Button 1
int button1State = HIGH;
int lastButton1State = HIGH;
unsigned long lastDebounceTime1 = 0;

// Button 2
int button2State = HIGH;
int lastButton2State = HIGH;
unsigned long lastDebounceTime2 = 0;

unsigned long debounceDelay = 50; // 50 milliseconds

// Callback when data is sent
void OnDataSent(const uint8_t *mac_addr, esp_now_send_status_t status) {
  if (status == ESP_NOW_SEND_SUCCESS) {
    // If send was successful, update the lastMessageSent with what was intended to be sent
    // This is crucial for the "send only on change" logic
    // strcpy(lastMessageSent, messageToSend); // We will do this in the main loop after a successful send call
  } else {
    // Serial.print("OnDataSent: Delivery Fail. Last message was: "); Serial.println(lastMessageSent);
    // If it failed, we might want to retry sending the *same* lastMessageSent
    // or just clear lastMessageSent to force a resend on next change.
    // For simplicity now, we won't aggressively retry here, the main loop will try on next change.
  }
}

void setup() {
  Serial.begin(115200);
  Serial.println("ESP32 ESP-NOW Sender (Send on Change)");

  // Initialize Button Pins
  pinMode(button1Pin, INPUT_PULLUP);
  pinMode(button2Pin, INPUT_PULLUP);

  // Set device as a Wi-Fi Station
  WiFi.mode(WIFI_STA);

  // Initialize ESP-NOW
  if (esp_now_init() != ESP_OK) {
    Serial.println("Error initializing ESP-NOW");
    return;
  }

  esp_now_register_send_cb(OnDataSent);

  memcpy(peerInfo.peer_addr, receiverMacAddress, 6);
  peerInfo.channel = 0;
  peerInfo.encrypt = false;

  if (esp_now_add_peer(&peerInfo) != ESP_OK) {
    Serial.println("Failed to add peer");
    return;
  }
  Serial.println("Peer added. Sending on state change...");
  lastMessageSent[0] = '\0'; // Initialize to ensure first message is sent
}

void loop() {
  // --- Read Button 1 with Debouncing ---
  bool currentButton1Pressed = false;
  int reading1 = digitalRead(button1Pin);
  if (reading1 != lastButton1State) {
    lastDebounceTime1 = millis();
  }
  if ((millis() - lastDebounceTime1) > debounceDelay) {
    if (reading1 != button1State) {
      button1State = reading1;
    }
  }
  lastButton1State = reading1;
  if (button1State == LOW) {
    currentButton1Pressed = true;
  }

  // --- Read Button 2 with Debouncing ---
  bool currentButton2Pressed = false;
  int reading2 = digitalRead(button2Pin);
  if (reading2 != lastButton2State) {
    lastDebounceTime2 = millis();
  }
  if ((millis() - lastDebounceTime2) > debounceDelay) {
    if (reading2 != button2State) {
      button2State = reading2;
    }
  }
  lastButton2State = reading2;
  if (button2State == LOW) {
    currentButton2Pressed = true;
  }

  // --- Determine current message based on button states ---
  char currentMessageBuffer[4]; // Temporary buffer for the current state
  if (currentButton1Pressed && currentButton2Pressed) {
    strcpy(currentMessageBuffer, "0;0"); // Both pressed
  } else if (currentButton1Pressed) {
    strcpy(currentMessageBuffer, "0;1"); // Button 1 pressed, Button 2 not -> ESP sends 0;1 -> Python UP
  } else if (currentButton2Pressed) {
    strcpy(currentMessageBuffer, "1;0"); // Button 1 not, Button 2 pressed -> ESP sends 1;0 -> Python DOWN
  } else {
    strcpy(currentMessageBuffer, "1;1"); // Neither pressed -> Python STILL (as per "0;0 or 1;1 means stand still")
  }

  // --- Send the message ONLY if it has changed ---
  if (strcmp(currentMessageBuffer, lastMessageSent) != 0) {
    // The message content has changed, attempt to send it
    strcpy(messageToSend, currentMessageBuffer); // Copy to the global buffer used by OnDataSent (if needed there)

    esp_err_t result = esp_now_send(receiverMacAddress, (uint8_t *)messageToSend, strlen(messageToSend));
    
    Serial.print("Attempting to send: "); Serial.print(messageToSend);
    if (result == ESP_OK) {
      Serial.println(" -> Sent successfully.");
      strcpy(lastMessageSent, messageToSend); // Update lastMessageSent ONLY on successful send attempt
    } else {
      Serial.print(" -> Error sending: ");
      if (result == ESP_ERR_ESPNOW_NOT_INIT) Serial.println("ESP-NOW not Init");
      else if (result == ESP_ERR_ESPNOW_ARG) Serial.println("Invalid Argument");
      else if (result == ESP_ERR_ESPNOW_INTERNAL) Serial.println("Internal Error");
      else if (result == ESP_ERR_ESPNOW_NO_MEM) Serial.println("ESP-NOW No Memory - Retrying next loop");
      else if (result == ESP_ERR_ESPNOW_NOT_FOUND) Serial.println("Peer not found");
      else if (result == ESP_ERR_ESPNOW_IF) Serial.println("WiFi Interface Error");
      else Serial.printf("Other error: %s\n", esp_err_to_name(result));
      // Do NOT update lastMessageSent if send failed, so it will try again with the same message
      // on the next loop iteration where strcmp still shows a difference.
    }
  }

  // The delay can be short now, as we only send on change.
  // This delay determines how responsive the button reading is.
  delay(10); // Poll buttons every 10ms
}