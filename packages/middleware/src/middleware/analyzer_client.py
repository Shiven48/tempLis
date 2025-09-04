"""
Mock Erba Analyzer Test Script

This script simulates an Erba analyzer sending HL7 messages to test the middleware.
Run this independently to test your middleware without the GUI.
"""

from pathlib import Path
import socket
import time
import sys

from middleware.logger import logger
from packages.middleware.src.constants import (
    START_BLOCK,
    END_BLOCK,
    CARRIAGE_RETURN,
)

class MockErbaAnalyzer:
    def __init__(self, host="127.0.0.1", port=15200):
        self.host = host
        self.port = port
        self.socket = None
        print("Mock ananlyzer created!!")
    
    def connect(self):
        """Connect to middleware server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            print(f"✓ Connected to middleware at {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from server"""
        if self.socket:
            self.socket.close()
            self.socket = None
            print("✓ Disconnected from middleware")
    
    def generate_hl7_messages(self):
        """Generate sample HL7 messages"""     
        working_dir = str(Path.cwd()) + '\\packages\\middleware\\src\\configuration\\erba.txt'
        with open(working_dir, 'r') as file:
            lines = file.readlines()

        messages = []
        for i, line in enumerate(lines, 1):
            cleaned_line = line.strip()
    
            # Use actual control characters, not escaped strings
            cleaned_line = cleaned_line.replace('[VT]', chr(11))   # \x0B
            cleaned_line = cleaned_line.replace('[CR]', chr(13))   # \r  
            cleaned_line = cleaned_line.replace('[FS]', chr(28))   # \x1C
            cleaned_line = cleaned_line.replace('[LF]', chr(10))   # \n
        
            if not cleaned_line:
                continue

            logger.info(repr(cleaned_line))
        
            message_dict = {
                'name': f'HL7_Message_{i}',
                'data': cleaned_line
            }
            messages.append(message_dict)

        return messages
    
    def send_message(self, message_data, message_name, i):
        """Send a single HL7 message wrapped in an MLLP frame"""
        try:
            print(f"\n📤 Sending: {message_name}")
            print(f"   Data length: {len(message_data)} bytes")
            print(f"   Preview: {message_data[:60]}...")
            
            # 1. Encode the HL7 string to bytes
            hl7_bytes = message_data.encode('utf-8')
            
            # 2. Wrap the bytes in the MLLP frame
            framed_message = START_BLOCK + hl7_bytes + END_BLOCK + CARRIAGE_RETURN
            
            # 3. Send the complete framed message using sendall
            self.socket.sendall(framed_message)
            print(f"Message {i} sent successfully")
            
            # Wait for acknowledgment
            self.socket.settimeout(5.0)
            ack = self.socket.recv(1024)
            
            print(f"📥 ACK received: {len(ack)} bytes")
            if ack:
                # The ACK will also be MLLP-framed, so you might see the special characters
                ack_str = ack.decode('utf-8', errors='ignore')
                print(f"   ACK Preview: {repr(ack_str)}") # Use repr() to see special chars
                if 'MSA|AA' in ack_str:
                    print("   ✓ Success ACK (AA) detected")
            
            return True
            
        except socket.timeout:
            print("   ⚠ Timeout waiting for ACK")
            return False
        except Exception as e:
            print(f"   ✗ Send error: {e}")
            return False

    def run_test_sequence(self, delay_between_messages=3):
        """Run complete test sequence with fresh connection per message"""
        print("=" * 60)
        print("MOCK ERBA ANALYZER - TEST SEQUENCE")
        print("=" * 60)
        print(f"Target: {self.host}:{self.port}")
        print(f"Delay between messages: {delay_between_messages} seconds")
        print()
    
        messages = self.generate_hl7_messages()   

        try:
            for i, message in enumerate(messages, 1):
                print(f"[{i}/{len(messages)}] Processing {message['name']}...")
            
                # Fresh connection for each message
                if not self.connect():
                    print(f"   ✗ Failed to connect for {message['name']}")
                    continue
                    
                success = self.send_message(message['data'], message['name'], i)
                
                # Close connection after each message
                self.disconnect()
            
                if success:
                    print(f"   ✓ {message['name']} sent successfully")
                else:
                    print(f"   ✗ Failed to send {message['name']}")
                
                if i < len(messages):
                    print(f"   ⏳ Waiting {delay_between_messages} seconds...")
                    time.sleep(delay_between_messages)
            
            print("\n" + "=" * 60)
            print("TEST SEQUENCE COMPLETED")
            print(f"✓ Sent {len(messages)} HL7 messages")
            print("=" * 60)
        
        except Exception as e:
            print(f"\n✗ Test error: {e}")
        
        return True

def main():
    """Main function"""
    print("Mock Erba Analyzer Test Tool")
    print("-" * 40)
    
    # Configuration
    host = "127.0.0.1"
    port = 15200
    delay = 3
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] in ['-h', '--help']:
            print("Usage: python test_mock_erba.py [host] [port] [delay]")
            print(f"Default: {host} {port} {delay}")
            return
        
        try:
            host = sys.argv[1] if len(sys.argv) > 1 else host
            port = int(sys.argv[2]) if len(sys.argv) > 2 else port
            delay = int(sys.argv[3]) if len(sys.argv) > 3 else delay
        except ValueError as e:
            print(f"Error parsing arguments: {e}")
            return
    
    # Create and run mock analyzer
    analyzer = MockErbaAnalyzer(host, port)
    
    try:
        analyzer.run_test_sequence(delay)
    except Exception as e:
        print(f"Fatal error: {e}")

if __name__ == "__main__":
    main()