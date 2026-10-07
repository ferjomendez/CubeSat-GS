// Fake LoRa modem: speaks the same serial protocol as ESP32_LoRa_Handler.ino, with no radio.
// Flash it on any bare ESP32 to test USB/COM port + ground station software without antennas.
//  - Every BEACON_MS it "receives" a CCSDS beacon (APID 10) with random values.
//  - Answers FREQ:<mhz> with OK:FREQ_SET and TX:<hex> with OK:TX_DONE.
//  - A TX containing "PING" gets a PONG (APID 101) back, like OBC_sim.py.
// MATCH_FREQ = true mimics real RF: beacons are only heard on FREQ_BEACON and PONGs on FREQ_TCTM.
// The GS boots on TC/TM, so switch it to beacon_listen to see beacons (or set MATCH_FREQ = false).

const float FREQ_TCTM = 435.500;
const float FREQ_BEACON = 437.250;
const unsigned long BEACON_MS = 10000;
const bool MATCH_FREQ = true;

float freq = FREQ_TCTM;
uint16_t seq = 0;  // one counter for all APIDs, like OBC_sim.py
unsigned long lastBeacon = 0;

bool tunedTo(float f) { return !MATCH_FREQ || fabs(freq - f) < 0.001; }

// Prints "RX:<header+payload hex>|RSSI:..|SNR:..", i.e. what the real modem prints after stripping the CRC.
void sendRx(uint16_t apid, const String &payload) {
  uint8_t pkt[255];
  size_t n = min((size_t)payload.length(), (size_t)249);
  uint16_t dataLen = n + 2 - 1;  // OBC_sim convention: length field counts the 2-byte CRC
  pkt[0] = (apid >> 8) & 0x07;
  pkt[1] = apid & 0xFF;
  pkt[2] = 0xC0 | ((seq >> 8) & 0x3F);
  pkt[3] = seq & 0xFF;
  pkt[4] = dataLen >> 8;
  pkt[5] = dataLen & 0xFF;
  memcpy(pkt + 6, payload.c_str(), n);
  seq = (seq + 1) & 0x3FFF;

  Serial.print("RX:");
  for (size_t i = 0; i < 6 + n; i++) {
    if (pkt[i] < 0x10) Serial.print('0');
    Serial.print(pkt[i], HEX);
  }
  Serial.printf("|RSSI:%.1f|SNR:%.2f\n", random(-120, -60) + 0.5, random(-500, 1000) / 100.0);
}

void setup() {
  Serial.begin(115200);
  Serial.setTimeout(100);  // don't block loop() for 1 s on partial lines
  randomSeed(esp_random());
}

void loop() {
  if (millis() - lastBeacon >= BEACON_MS) {
    lastBeacon = millis();
    if (tunedTo(FREQ_BEACON)) {
      sendRx(10, String("VLEO_BEACON_T=") + String(random(-100, 400) / 10.0, 1) +
                 "_V=" + String(random(330, 420) / 100.0, 2));
    }
  }

  if (Serial.available()) {
    String in = Serial.readStringUntil('\n');
    in.trim();
    if (in.startsWith("FREQ:")) {
      freq = in.substring(5).toFloat();
      Serial.println("OK:FREQ_SET");
    } else if (in.startsWith("TX:")) {
      Serial.println("OK:TX_DONE");
      in.toUpperCase();
      if (in.indexOf("50494E47", 3 + 12) >= 0 && tunedTo(FREQ_TCTM)) {  // "PING" in the payload
        delay(200);
        sendRx(101, "PONG_DATA_6.28");
      }
    }
  }
}
