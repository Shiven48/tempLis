import serial
import time

# write to middleware (index.py)
# read from middleware (thread)


# Send data on com1 and it will be directly received on com2 
# as they are connected internally via serial bridge

# ASTM Control characters
ENQ = b'\x05'
ACK = b'\x06'
NAK = b'\x15'
EOT = b'\x04'
STX = b'\x02'
ETX = b'\x03'
CR  = b'\r'
LF  = b'\n'

def astm_frame(sequence_number: int, body: str) -> bytes:
    """Wraps a line with ASTM framing and checksum."""
    line = f"{sequence_number}{body}"
    content = line.encode('ascii')
    cs = sum(content) + ETX[0]
    checksum = f"{cs % 256:02X}".encode()

    return STX + content + ETX + checksum + CR + LF

def wait_for_ack(ser, timeout=10):
    """Wait for ACK or NAK from LIS."""
    start = time.time()
    while time.time() - start < timeout:
        if ser.in_waiting:
            response = ser.read()
            if response == ACK:
                print("[LIS] ACK received")
                return True
            elif response == NAK:
                print("[LIS] NAK received")
                return False
    print("[LIS] No response")
    return False

def send_record(ser, frame):
    ser.write(frame)
    print("[Analyzer] SENT:", frame)
    return wait_for_ack(ser)

def simulate_bs240():
    port = 'COM1'  # Adjust this to your middleware port
    baudrate = 9600

    print("Connecting to middleware...")
    with serial.Serial(port, baudrate, timeout=1) as ser:
        time.sleep(2)

        # Start Session
        ser.write(ENQ)
        print("[Analyzer] SENT: ENQ")
        if not wait_for_ack(ser):
            print("[Analyzer] Session failed to start")
            return

        # Define ASTM records
        header = "H|\\^&|||Mindry^^|||||||PR|1394-97|20250701173106"
        patient = "P|1||||^^||^^|U||||||||||||||||||||||||||"
        order = ("O|1|9^^|25142231|"
                 "MGII^Magnesium^^\\CA^Calcium^^\\SGPT^Alanine Aminotransferase^^\\"
                 "SGOT^Aspartate Aminotransferase^^\\^AST/ALT^^|"
                 "R|20250701145310|20250701145245|||||||20250701145245|serum||||||||||F|||||")
        result = "R|1|MGII^Magnesium^^F|2.199529^^^^|mg/dL|2.2^2.2|N||F|2.199529^^^^|0|20250701154348||Mindry^1234567890"
        terminator = "L|1|N"

        records = [
            astm_frame(1, header),
            astm_frame(2, patient),
            astm_frame(3, order),
            astm_frame(4, result),
            astm_frame(5, terminator)
        ]

        for record in records:
            success = send_record(ser, record)
            if not success:
                print("[Analyzer] Retrying record...")
                send_record(ser, record)  # Retry once

        # End of Transmission
        ser.write(EOT)
        print("[Analyzer] SENT: EOT")
        time.sleep(0.5)

if __name__ == "__main__":
    simulate_bs240()
