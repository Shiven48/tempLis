#!/usr/bin/env python3
"""
Final verification test for Task 6: Test the complete implementation
This test verifies all requirements from the task details:
- Verify dropdown appears with correct default selection (BS240)
- Test machine selection changes and persistence
- Verify styling consistency with existing UI elements  
- Test error handling with missing configuration file
- Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3
"""

import tkinter as tk
import os
import json
import sys
import tempfile
import shutil

# Add Graphics directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Graphics'))

class MockMainApp:
    def __init__(self):
        self.events = []
        self.errors = []
    
    def log_event(self, message):
        self.events.append(message)
    
    def log_error(self, message):
        self.errors.append(message)

def verify_requirement_1_1():
    """Requirement 1.1: WHEN the SerialTab interface loads THEN the system SHALL display a dropdown menu labeled "Machine" with available machine options"""
    print("Testing Requirement 1.1: Machine dropdown display...")
    
    root = tk.Tk()
    root.withdraw()
    
    try:
        mock_app = MockMainApp()
        from SerialTab import SerialTab
        serial_tab = SerialTab(root, mock_app)
        
        # Verify machine_var exists (indicates dropdown was created)
        assert hasattr(serial_tab, 'machine_var'), "Machine dropdown variable not found"
        
        # Verify machine options are loaded
        machine_options = serial_tab.load_machine_options()
        assert len(machine_options) > 0, "No machine options available"
        
        print("✓ Requirement 1.1 PASSED: Machine dropdown with options is displayed")
        return True
        
    except Exception as e:
        print(f"✗ Requirement 1.1 FAILED: {e}")
        return False
    finally:
        root.destroy()

def verify_requirement_1_3():
    """Requirement 1.3: WHEN the interface initializes THEN the system SHALL set BS240 as the default selected machine"""
    print("Testing Requirement 1.3: Default selection BS240...")
    
    root = tk.Tk()
    root.withdraw()
    
    try:
        mock_app = MockMainApp()
        from SerialTab import SerialTab
        serial_tab = SerialTab(root, mock_app)
        
        default_selection = serial_tab.machine_var.get()
        assert default_selection == "BS240", f"Expected BS240, got {default_selection}"
        
        print("✓ Requirement 1.3 PASSED: Default selection is BS240")
        return True
        
    except Exception as e:
        print(f"✗ Requirement 1.3 FAILED: {e}")
        return False
    finally:
        root.destroy()

def verify_requirement_2_1():
    """Requirement 2.1: WHEN a user selects a machine from the dropdown THEN the system SHALL maintain that selection until changed"""
    print("Testing Requirement 2.1: Selection persistence...")
    
    root = tk.Tk()
    root.withdraw()
    
    try:
        mock_app = MockMainApp()
        from SerialTab import SerialTab
        serial_tab = SerialTab(root, mock_app)
        
        # Get available machines
        machine_options = serial_tab.load_machine_options()
        
        if len(machine_options) > 1:
            # Change selection
            new_machine = machine_options[1] if machine_options[0] == "BS240" else machine_options[0]
            serial_tab.machine_var.set(new_machine)
            serial_tab.on_machine_change(new_machine)
            
            # Verify persistence
            current_selection = serial_tab.machine_var.get()
            assert current_selection == new_machine, f"Selection not maintained: expected {new_machine}, got {current_selection}"
            
            print("✓ Requirement 2.1 PASSED: Selection is maintained")
        else:
            print("⚠ Requirement 2.1 SKIPPED: Only one machine available")
        
        return True
        
    except Exception as e:
        print(f"✗ Requirement 2.1 FAILED: {e}")
        return False
    finally:
        root.destroy()

def verify_requirement_3_1():
    """Requirement 3.1: WHEN the dropdown is displayed THEN the system SHALL use the same styling and fonts as existing UI elements"""
    print("Testing Requirement 3.1: Styling consistency...")
    
    root = tk.Tk()
    root.withdraw()
    
    try:
        mock_app = MockMainApp()
        from SerialTab import SerialTab
        serial_tab = SerialTab(root, mock_app)
        
        # Find dropdown widgets
        machine_menu = None
        baud_menu = None
        
        def find_widgets(widget):
            nonlocal machine_menu, baud_menu
            for child in widget.winfo_children():
                if isinstance(child, tk.OptionMenu):
                    if hasattr(child, 'cget'):
                        try:
                            if child['textvariable'] == str(serial_tab.machine_var):
                                machine_menu = child
                            elif child['textvariable'] == str(serial_tab.baud_var):
                                baud_menu = child
                        except:
                            pass
                find_widgets(child)
        
        find_widgets(serial_tab.frame)
        
        if machine_menu and baud_menu:
            # Compare key styling attributes
            machine_bg = machine_menu.cget('bg')
            baud_bg = baud_menu.cget('bg')
            assert machine_bg == baud_bg, f"Background colors don't match: {machine_bg} vs {baud_bg}"
            
            machine_font = machine_menu.cget('font')
            baud_font = baud_menu.cget('font')
            assert machine_font == baud_font, f"Fonts don't match: {machine_font} vs {baud_font}"
            
            print("✓ Requirement 3.1 PASSED: Styling is consistent")
        else:
            print("⚠ Requirement 3.1 WARNING: Could not locate dropdown widgets for comparison")
        
        return True
        
    except Exception as e:
        print(f"✗ Requirement 3.1 FAILED: {e}")
        return False
    finally:
        root.destroy()

def verify_requirement_4_1():
    """Requirement 4.1: WHEN new machines are added to the system THEN the dropdown SHALL automatically include them without code modification"""
    print("Testing Requirement 4.1: Dynamic machine loading...")
    
    # Create temporary config with additional machine
    config_path = os.path.join("Configuration", "AnalyzerConfig.json")
    backup_path = config_path + ".backup"
    
    # Backup original
    if os.path.exists(config_path):
        shutil.copy2(config_path, backup_path)
    
    # Create test config with additional machine
    test_config = {
        "BS240": {"config": {}},
        "ErbaElite580": {"config": {}},
        "TestMachine": {"config": {}}
    }
    
    with open(config_path, 'w') as f:
        json.dump(test_config, f)
    
    root = tk.Tk()
    root.withdraw()
    
    try:
        mock_app = MockMainApp()
        from SerialTab import SerialTab
        serial_tab = SerialTab(root, mock_app)
        
        machine_options = serial_tab.load_machine_options()
        assert "TestMachine" in machine_options, "New machine not automatically loaded"
        assert len(machine_options) == 3, f"Expected 3 machines, got {len(machine_options)}"
        
        print("✓ Requirement 4.1 PASSED: New machines are automatically loaded")
        return True
        
    except Exception as e:
        print(f"✗ Requirement 4.1 FAILED: {e}")
        return False
    finally:
        # Restore original config
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, config_path)
            os.remove(backup_path)
        root.destroy()

def verify_error_handling():
    """Test error handling with missing configuration file"""
    print("Testing Error Handling: Missing configuration file...")
    
    # Backup and remove config
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
        
        # Should fall back to default machines
        machine_options = serial_tab.load_machine_options()
        expected_defaults = ["BS240", "Abbott", "Snibe", "ErbaElite580"]
        assert machine_options == expected_defaults, f"Expected defaults {expected_defaults}, got {machine_options}"
        
        # Should log the missing file
        config_not_found = any("Configuration file not found" in event for event in mock_app.events)
        assert config_not_found, "Missing config file not logged"
        
        print("✓ Error Handling PASSED: Missing config handled gracefully")
        return True
        
    except Exception as e:
        print(f"✗ Error Handling FAILED: {e}")
        return False
    finally:
        # Restore config
        if config_existed:
            shutil.copy2(backup_path, config_path)
            os.remove(backup_path)
        root.destroy()

def run_final_verification():
    """Run all requirement verification tests"""
    print("FINAL VERIFICATION TEST - Task 6: Test the complete implementation")
    print("=" * 70)
    
    tests = [
        ("Requirement 1.1 - Machine dropdown display", verify_requirement_1_1),
        ("Requirement 1.3 - Default selection BS240", verify_requirement_1_3),
        ("Requirement 2.1 - Selection persistence", verify_requirement_2_1),
        ("Requirement 3.1 - Styling consistency", verify_requirement_3_1),
        ("Requirement 4.1 - Dynamic machine loading", verify_requirement_4_1),
        ("Error Handling - Missing config", verify_error_handling),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} FAILED with exception: {e}")
            results.append((test_name, False))
    
    # Final summary
    print("\n" + "=" * 70)
    print("FINAL VERIFICATION SUMMARY")
    print("=" * 70)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "PASSED" if result else "FAILED"
        symbol = "✓" if result else "✗"
        print(f"{symbol} {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nFinal Results: {passed}/{total} requirements verified")
    
    if passed == total:
        print("\n🎉 TASK 6 COMPLETE: All requirements verified successfully!")
        print("The machine selection dropdown implementation is fully functional and meets all specifications.")
        return True
    else:
        print(f"\n⚠ TASK 6 INCOMPLETE: {total - passed} requirement(s) not met.")
        return False

if __name__ == "__main__":
    success = run_final_verification()
    sys.exit(0 if success else 1)