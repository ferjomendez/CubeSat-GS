import serial

SER_PORT = '/dev/ttyUSB0'  # Adjust to your ground station port
BAUD = 115200
FREQ_BEACON = 437.250

ser = serial.Serial(SER_PORT, BAUD, timeout=0.1)

# Force the ESP32 modem to the beacon frequency immediately
ser.write(f"FREQ:{FREQ_BEACON}\n".encode())
print(f"Listening exclusively for beacons on {FREQ_BEACON} MHz...")

while True:
    if ser.in_waiting > 0:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        
        if line.startswith("RX:"):
            packet = bytes.fromhex(line[3:])
            
            # Parse CCSDS Header
            apid = ((packet[0] & 0x07) << 8) | packet[1]
            seq = ((packet[2] & 0x3F) << 8) | packet[3]
            payload = packet[6:] # Excludes header and 2-byte CRC
            
            print(f"[BEACON] APID: {apid} | Seq: {seq} | Data: {payload.decode('utf-8', errors='ignore')}")
