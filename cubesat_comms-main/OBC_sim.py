import serial
import time
import math

SER_PORT = '/dev/ttyUSB0'  # Adjust to the ESP32 serial port
BAUD = 115200

# ITU Compliant Frequencies 
FREQ_TCTM = 435.500
FREQ_BEACON = 437.250
BEACON_INTERVAL = 10  # Transmit beacon every 60 seconds
ser = serial.Serial(SER_PORT, BAUD, timeout=0.1)

# Ensure modem initializes on the listening frequency
ser.write(f"FREQ:{FREQ_TCTM}\n".encode())
last_beacon_time = time.time()
seq_count = 0

def build_ccsds_packet(apid, payload_bytes):
    """Constructs the 6-byte big-endian CCSDS primary header."""
    global seq_count
    
    # Calculate length: Payload size + 2 bytes for the ESP32 CRC, minus 1 per CCSDS standard
    ccsds_data_len = len(payload_bytes) + 2 - 1  
    
    header = bytearray(6)
    header[0] = (apid >> 8) & 0x07
    header[1] = apid & 0xFF
    header[2] = 0xC0 | ((seq_count >> 8) & 0x3F)
    header[3] = seq_count & 0xFF
    header[4] = (ccsds_data_len >> 8) & 0xFF
    header[5] = ccsds_data_len & 0xFF
    
    seq_count = (seq_count + 1) & 0x3FFF
    return header + payload_bytes

print("Satellite OBC Running. Listening for Telecommands...")

while True:
    # --- 1. Process Incoming Ground Telecommands ---
    if ser.in_waiting > 0:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        
        if line.startswith("RX:"):
            hex_data = line[3:]
            packet = bytes.fromhex(hex_data)
            
            apid = ((packet[0] & 0x07) << 8) | packet[1]
            payload = packet[6:]
            
            print(f"[Ground Command] APID: {apid} | Data: {payload}")
            
            # Example logic: Respond to a ping command
            if b"PING" in payload:
                # Execution of internal calculations 
                telemetry_val = math.pi * 2.0 
                
                response_data = f"PONG_DATA_{telemetry_val:.2f}".encode()
                tx_hex = build_ccsds_packet(101, response_data).hex()
                
                ser.write(f"TX:{tx_hex}\n".encode())
                print("[Telemetry] Sent response.")

    # --- 2. Broadcast Periodic Beacon ---
    current_time = time.time()
    if (current_time - last_beacon_time) >= BEACON_INTERVAL:
        print(f"[Beacon] Shifting frequency to {FREQ_BEACON} MHz...")
        
        # Shift hardware to beacon frequency
        ser.write(f"FREQ:{FREQ_BEACON}\n".encode())
        time.sleep(0.1) 
        
        beacon_data = b"VLEO_BEACON_SYS_NOMINAL"
        beacon_hex = build_ccsds_packet(10, beacon_data).hex()

        print(f"beacon data {beacon_data}, hex {beacon_hex}")
        
        # Transmit
        ser.write(f"TX:{beacon_hex}\n".encode())
        
        # Wait for transmission time before shifting back to avoid cutting off the RF output
        time.sleep(1.0) 
        
        # Shift back to main listening frequency
        ser.write(f"FREQ:{FREQ_TCTM}\n".encode())
        print(f"[Beacon] Returned to {FREQ_TCTM} MHz.")
        
        last_beacon_time = current_time
