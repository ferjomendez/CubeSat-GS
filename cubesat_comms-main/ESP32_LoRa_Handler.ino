#include <RadioLib.h>

#define NSS_PIN   5
#define DIO0_PIN  2
#define RESET_PIN 14
#define DIO1_PIN  33

SX1278 radio = new Module(NSS_PIN, DIO0_PIN, RESET_PIN, DIO1_PIN);
volatile bool receivedFlag = false;

#if defined(ESP8266) || defined(ESP32)
  ICACHE_RAM_ATTR
#endif
void setFlag(void) {
  receivedFlag = true;
}

// Standard CCSDS CRC-16-CCITT calculation
uint16_t calculateCRC(uint8_t *data, uint16_t len) {
  uint16_t crc = 0xFFFF;
  for (uint16_t i = 0; i < len; i++) {
    crc ^= (uint16_t)data[i] << 8;
    for (uint8_t j = 0; j < 8; j++) {
      if (crc & 0x8000) crc = (crc << 1) ^ 0x1021;
      else crc <<= 1;
    }
  }
  return crc;
}

void setup() {
  Serial.begin(115200);
  
  int state = radio.begin(435.500, 125.0, 9, 7, 0x12, 17, 8);
  if (state != RADIOLIB_ERR_NONE) {
    while (true);
  }
  
  radio.setPacketReceivedAction(setFlag);
  radio.startReceive();
}

void loop() {
  if (receivedFlag) {
    receivedFlag = false;
    uint8_t packet[255];
    int state = radio.readData(packet, 255);
    
    if (state == RADIOLIB_ERR_NONE) {
      size_t len = radio.getPacketLength();
      if (len >= 8) {
        // Isolate trailing 2-byte CRC and verify
        uint16_t receivedCrc = ((uint16_t)packet[len - 2] << 8) | packet[len - 1];
        uint16_t calculatedCrc = calculateCRC(packet, len - 2);
        
        if (receivedCrc == calculatedCrc) {
          Serial.print("RX:");
          for (size_t i = 0; i < len - 2; i++) {
            if (packet[i] < 0x10) Serial.print("0");
            Serial.print(packet[i], HEX);
          }
          Serial.println();
        }
      }
    }
    radio.startReceive();
  }

  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    
    if (input.startsWith("TX:")) {
      String hexData = input.substring(3);
      size_t len = hexData.length() / 2;
      uint8_t txBuffer[255];
      
      for (size_t i = 0; i < len; i++) {
        String byteStr = hexData.substring(i*2, i*2 + 2);
        txBuffer[i] = (uint8_t) strtol(byteStr.c_str(), NULL, 16);
      }
      
      // Calculate and append CRC internally before transmission
      uint16_t crc = calculateCRC(txBuffer, len);
      txBuffer[len] = (crc >> 8) & 0xFF;
      txBuffer[len + 1] = crc & 0xFF;
      
      radio.transmit(txBuffer, len + 2);
      Serial.println("OK:TX_DONE");
      radio.startReceive(); 
    } 
    
    else if (input.startsWith("FREQ:")) {
      float newFreq = input.substring(5).toFloat();
      radio.standby();
      if (radio.setFrequency(newFreq) == RADIOLIB_ERR_NONE) {
        Serial.println("OK:FREQ_SET");
      }
      radio.startReceive(); 
    }
  }
}
