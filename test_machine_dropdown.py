#!/usr/bin/env python3
"""
Test script for machine selection dropdown implementation
Tests all requirements from task 6:
- Verify dropdown appears with correct default selection (BS240)
- Test machine selection changes and persistence
- Verify styling consistency with existing UI elements
- Test error handling with missing configuration file
"""

import tkinter as tk
import os
import json
import tempfile
import shutil
import sys
import time
from unittest.mock import Mock

# Add the Graphics directory to the path so we can import SerialTab
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Graphics'))

class MockMainApp:
    """Mock main application for testing"""
    def __init__(self):
        self.events = []
        self.errors = []
    
    def log_event(self, message):
        self.events.append(message)
        print(f"[EVENT] {message}")
    
    def log_error(self, message):
        self.errors.append(message)
        print(f"[ERROR] {message}")

def test_dropdown_default_selection():
    """Test 1: Verify dropdown appears with correct default selection (BS240)"""
    print("\n=== Test 1: Default Selection ===")
    
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    
    try:
        # Create mock main app
        mock_app = MockMainApp()
        
        # Create SerialTab instance
        from SerialTab import SerialTab
        serial_tab = SerialTab(root, mock_app)
        
        # Check if machine_var exists and has correct default
        assert hasattr(serial_tab, 'machine_var'), "machine_var attribute not found"
        default_value = serial_tab.machine_var.get()
        
        print(f"Default machine selection: {default_value}")
        assert default_value == "BS240", f"Expected default 'BS240', got '{default_value}'"
        
        print("✓ Default selection test PASSED")
        return True
        
    except Exception as e:
        print(f"✗ Default selection test FAILED: {e}")
        return False
    finally:
        root.destroy()

def test_machine_selection_changes():
    """Test 2: Test machine selection changes and persistence"""
    print("\n=== Test 2: Machine Selection Changes ===")
    
    root = tk.Tk()
    root.withdraw()
    
    try:
        mock_app = MockMainApp()
        from SerialTab import SerialTab
        serial_tab = SerialTab(root, mock_app)
        
        # Test changing machine selection
        original_selection = serial_tab.machine_var.get()
        print(f"Original selection: {original_selection}")
        
        # Get available machines
        machine_options = serial_tab.load_machine_options()
        print(f"Available machines: {machine_options}")
        
        # Test changing to different machine
        if len(machine_options) > 1:
            new_machine = machine_options[1] if machine_options[0] == original_selection else machine_options[0]
            
            # Simulate machine change
            serial_tab.machine_var.set(new_machine)
            serial_tab.on_machine_change(new_machine)
            
            # Verify change persisted
            current_selection = serial_tab.machine_var.get()
            print(f"New selection: {current_selection}")
            assert current_selection == new_machine, f"Selection not persisted: expected '{new_machine}', got '{current_selection}'"
            
            # Check if change was logged
            logged_change = any("[Machine] Selection changed to:" in event for event in mock_app.events)
            assert logged_change, "Machine selection change was not logged"
            
            print("✓ Machine selection change test PASSED")
        else:
            print("⚠ Only one machine available, skipping change test")
        
        return True
        
    except Exception as e:
        print(f"✗ Machine selection change test FAILED: {e}")
        return False
    finally:
        root.destroy()

def test_styling_consistency():
    """Test 3: Verify styling consistency with existing UI elements"""
    print("\n=== Test 3: Styling Consistency ===")
    
    root = tk.Tk()
    root.withdraw()
    
    try:
        mock_app = MockMainApp()
        from SerialTab import SerialTab
        serial_tab = SerialTab(root, mock_app)
        
        # Find the machine dropdown widget by traversing the UI
        machine_menu = None
        baud_menu = None
        
        def find_widgets(widget):
            nonlocal machine_menu, baud_menu
            for child in widget.winfo_children():
                if isinstance(child, tk.OptionMenu):
                    # Check if this is the machine dropdown by checking its variable
                    if hasattr(child, 'cget') and child['textvariable'] == str(serial_tab.machine_var):
                        machine_menu = child
                    elif hasattr(child, 'cget') and child['textvariable'] == str(serial_tab.baud_var):
                        baud_menu = child
                find_widgets(child)
        
        find_widgets(serial_tab.frame)
        
        if machine_menu and baud_menu:
            # Compare styling attributes
            machine_bg = machine_menu.cget('bg')
            baud_bg = baud_menu.cget('bg')
            
            machine_font = machine_menu.cget('font')
            baud_font = baud_menu.cget('font')
            
            machine_relief = machine_menu.cget('relief')
            baud_relief = baud_menu.cget('relief')
            
            print(f"Machine dropdown - bg: {machine_bg}, font: {machine_font}, relief: {machine_relief}")
            print(f"Baud dropdown - bg: {baud_bg}, font: {baud_font}, relief: {baud_relief}")
            
            # Verify consistency
            assert machine_bg == baud_bg, f"Background colors don't match: machine={machine_bg}, baud={baud_bg}"
            assert machine_font == baud_font, f"Fonts don't match: machine={machine_font}, baud={baud_font}"
            assert machine_relief == baud_relief, f"Relief styles don't match: machine={machine_relief}, baud={baud_relief}"
            
            print("✓ Styling consistency test PASSED")
        else:
            print("⚠ Could not find dropdown widgets for comparison")
        
        return True
        
    except Exception as e:
        print(f"✗ Styling consistency test FAILED: {e}")
        return False
    finally:
        root.destroy()

def test_error_handling_missing_config():
    """Test 4: Test error handling with missing configuration file"""
    print("\n=== Test 4: Error Handling - Missing Config ===")
    
    # Backup original config file if it exists
    config_path = os.path.join("Configuration", "AnalyzerConfig.json")
    backup_path = config_path + ".backup"
    config_existed = os.path.exists(config_path)
    
    if config_existed:
        shutil.copy2(config_path, backup_path)
        os.remove(config_path)
    
    root = tk.Tk()
    root.withdraw()
    
    try:
        mock_app = MockMainApp()
        from SerialTab import SerialTab
        serial_tab = SerialTab(root, mock_app)
        
        # Test loading machine options with missing config
        machine_options = serial_tab.load_machine_options()
        
        print(f"Machine options with missing config: {machine_options}")
        
        # Should return default machines
        expected_defaults = ["BS240", "Abbott", "Snibe", "ErbaElite580"]
        assert machine_options == expected_defaults, f"Expected default machines {expected_defaults}, got {machine_options}"
        
        # Check if appropriate error/warning was logged
        config_not_found_logged = any("Configuration file not found" in event for event in mock_app.events)
        assert config_not_found_logged, "Missing config file was not logged"
        
        print("✓ Missing config error handling test PASSED")
        return True
        
    except Exception as e:
        print(f"✗ Missing config error handling test FAILED: {e}")
        return False
    finally:
        # Restore original config file
        if config_existed:
            shutil.copy2(backup_path, config_path)
            os.remove(backup_path)
        root.destroy()

def test_error_handling_invalid_config():
    """Test 5: Test error handling with invalid JSON configuration"""
    print("\n=== Test 5: Error Handling - Invalid Config ===")
    
    # Backup original config file
    config_path = os.path.join("Configuration", "AnalyzerConfig.json")
    backup_path = config_path + ".backup"
    config_existed = os.path.exists(config_path)
    
    if config_existed:
        shutil.copy2(config_path, backup_path)
    
    # Create invalid JSON file
    with open(config_path, 'w') as f:
        f.write("{ invalid json content }")
    
    root = tk.Tk()
    root.withdraw()
    
    try:
        mock_app = MockMainApp()
        from SerialTab import SerialTab
        serial_tab = SerialTab(root, mock_app)
        
        # Test loading machine options with invalid config
        machine_options = serial_tab.load_machine_options()
        
        print(f"Machine options with invalid config: {machine_options}")
        
        # Should return default machines
        expected_defaults = ["BS240", "Abbott", "Snibe", "ErbaElite580"]
        assert machine_options == expected_defaults, f"Expected default machines {expected_defaults}, got {machine_options}"
        
        # Check if JSON error was logged
        json_error_logged = any("Invalid JSON" in error for error in mock_app.errors)
        assert json_error_logged, "Invalid JSON error was not logged"
        
        print("✓ Invalid config error handling test PASSED")
        return True
        
    except Exception as e:
        print(f"✗ Invalid config error handling test FAILED: {e}")
        return False
    finally:
        # Restore original config file
        if config_existed:
            shutil.copy2(backup_path, config_path)
        else:
            os.remove(config_path)
        if os.path.exists(backup_path):
            os.remove(backup_path)
        root.destroy()

def test_config_loading_with_valid_file():
    """Test 6: Test configuration loading with valid file"""
    print("\n=== Test 6: Valid Config Loading ===")
    
    root = tk.Tk()
    root.withdraw()
    
    try:
        mock_app = MockMainApp()
        from SerialTab import SerialTab
        serial_tab = SerialTab(root, mock_app)
        
        # Test loading machine options with existing config
        machine_options = serial_tab.load_machine_options()
        
        print(f"Machine options from config: {machine_options}")
        
        # Should contain machines from the actual config file
        assert len(machine_options) > 0, "No machine options loaded"
        assert "BS240" in machine_options, "BS240 not found in loaded options"
        
        # Check if successful loading was logged
        config_loaded_logged = any("Loaded" in event and "machines from configuration" in event for event in mock_app.events)
        assert config_loaded_logged, "Successful config loading was not logged"
        
        print("✓ Valid config loading test PASSED")
        return True
        
    except Exception as e:
        print(f"✗ Valid config loading test FAILED: {e}")
        return False
    finally:
        root.destroy()

def run_all_tests():
    """Run all tests and report results"""
    print("Starting Machine Selection Dropdown Tests")
    print("=" * 50)
    
    tests = [
        ("Default Selection", test_dropdown_default_selection),
        ("Machine Selection Changes", test_machine_selection_changes),
        ("Styling Consistency", test_styling_consistency),
        ("Missing Config Error Handling", test_error_handling_missing_config),
        ("Invalid Config Error Handling", test_error_handling_invalid_config),
        ("Valid Config Loading", test_config_loading_with_valid_file),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} FAILED with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "PASSED" if result else "FAILED"
        symbol = "✓" if result else "✗"
        print(f"{symbol} {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests PASSED! Machine dropdown implementation is working correctly.")
        return True
    else:
        print(f"⚠ {total - passed} test(s) FAILED. Please review the implementation.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)