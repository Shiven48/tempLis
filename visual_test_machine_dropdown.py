#!/usr/bin/env python3
"""
Visual test for machine selection dropdown
This script opens the SerialTab interface so you can manually verify:
- Dropdown appears in the correct location
- Default selection is BS240
- Machine options are populated correctly
- Styling matches other UI elements
- Selection changes work properly
"""

import tkinter as tk
import sys
import os

# Add the Graphics directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Graphics'))

class MockMainApp:
    """Mock main application for visual testing"""
    def __init__(self):
        self.events = []
        self.errors = []
    
    def log_event(self, message):
        self.events.append(message)
        print(f"[EVENT] {message}")
    
    def log_error(self, message):
        self.errors.append(message)
        print(f"[ERROR] {message}")
    
    def parse_input_with_control_chars(self, input_str):
        """Mock method for parsing input"""
        return input_str.encode('utf-8')
    
    def pretty_logger(self, data):
        """Mock method for pretty logging"""
        return repr(data)
    
    def send_api_request(self, endpoint, payload):
        """Mock method for API requests"""
        return True, {"processed": len(payload.get('data', []))}, None

def main():
    print("Starting Visual Test for Machine Selection Dropdown")
    print("=" * 50)
    print("This will open the SerialTab interface.")
    print("Please verify the following:")
    print("1. Machine dropdown appears between Baud and Connect button")
    print("2. Default selection is 'BS240'")
    print("3. Dropdown contains available machines")
    print("4. Styling matches the Baud dropdown")
    print("5. Selection changes work and are logged")
    print("=" * 50)
    
    # Create main window
    root = tk.Tk()
    root.title("Machine Dropdown Visual Test")
    root.geometry("1000x800")
    
    # Create mock main app
    mock_app = MockMainApp()
    
    # Import and create SerialTab
    try:
        from SerialTab import SerialTab
        serial_tab = SerialTab(root, mock_app)
        serial_tab.frame.pack(fill=tk.BOTH, expand=True)
        
        # Add instructions label
        instructions = tk.Label(root, 
                              text="Visual Test Instructions:\n" +
                                   "1. Check machine dropdown location and styling\n" +
                                   "2. Verify default selection is 'BS240'\n" +
                                   "3. Test changing machine selection\n" +
                                   "4. Check console for logged events\n" +
                                   "5. Close window when done testing",
                              bg='lightyellow',
                              font=('Arial', 10),
                              justify=tk.LEFT,
                              padx=10,
                              pady=5)
        instructions.pack(side=tk.BOTTOM, fill=tk.X)
        
        print("\n✓ SerialTab interface loaded successfully")
        print("✓ Machine dropdown should be visible in the connection frame")
        print("✓ Watch console for machine selection change events")
        
        # Start the GUI
        root.mainloop()
        
    except Exception as e:
        print(f"✗ Error loading SerialTab: {e}")
        root.destroy()

if __name__ == "__main__":
    main()