"""
Test script to demonstrate the profile-based ASTM system
"""
import datetime
from profile_factory import ProfileFactory
from message_processor import MessageProcessor

def test_bs240_profile():
    """Test BS240 profile functionality"""
    print("=== Testing BS240 Profile ===")
    
    # Create BS240 profile
    profile = ProfileFactory.create_profile("BS_240")
    
    print(f"Machine Type: {profile.get_machine_type()}")
    print(f"Protocol: {profile.get_protocol_type()}")
    print(f"Connection Config: {profile.get_connection_config()}")
    
    # Test record class creation
    header_class = profile.get_record_class('header')
    if header_class:
        print("\n--- Testing Header Record ---")
        try:
            header = header_class(
                record_type_id="H",
                delimeter="\\^&",
                Processing_Id="PR",
                protocol_version="1.0",
                timestamp=datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            )
            print("Header created successfully:", header)
            print("Header data:", dict(header._data))
        except Exception as e:
            print("Header creation error:", e)
    
    # Test patient record
    patient_class = profile.get_record_class('patient')
    if patient_class:
        print("\n--- Testing Patient Record ---")
        try:
            patient = patient_class(
                record_type_id="P",
                sequence_number=1,
                patient_id="PAT001",
                patient_sex="M"
            )
            print("Patient created successfully:", patient)
        except Exception as e:
            print("Patient creation error:", e)

def test_erba_profile():
    """Test ERBA Elite 580 profile functionality"""
    print("\n=== Testing ERBA Elite 580 Profile ===")
    
    # Create ERBA profile
    profile = ProfileFactory.create_profile("ERBA_ELITE_580")
    
    print(f"Machine Type: {profile.get_machine_type()}")
    print(f"Protocol: {profile.get_protocol_type()}")
    print(f"Specific Settings: {profile.get_specific_settings()}")

def test_message_processing():
    """Test message processing"""
    print("\n=== Testing Message Processing ===")
    
    processor = MessageProcessor("BS_240")
    
    # Sample ASTM message
    sample_message = """H|\\^&|||BS240^1.0^1|||||||P|1|20240716120000
        P|1||PAT001||Doe^John^||19900101|M|||123 Main St||||||||||||
        O|1|SAM001||GLU^Glucose|||20240716120000|||||||||Serum||Doctor^Jane||O
        R|1|GLU^Glucose^|120|mg/dL|70-110|H||F|||20240716120500|BS240
        L|1|N"""
    
    try:
        results = processor.process_message(sample_message)
        print(f"Processed {len(results)} results:")
        for result in results:
            print("Result:", result)
    except Exception as e:
        print("Message processing error:", e)

def test_dynamic_record_creation():
    """Test dynamic record creation from config"""
    print("\n=== Testing Dynamic Record Creation ===")
    
    # Test the libtest.py functionality
    from libtest import build_record_class_from_config
    
    # Sample config for testing
    fields_config = [
        {"name": "record_type_id", "index": 0, "type": "constantField", "value": "H"},
        {"name": "Processing_Id", "index": 1, "type": "setField", "values": ["PR", "QR", "CR"]},
        {"name": "protocol_version", "index": 2, "type": "textField"},
        {"name": "timestamp", "index": 3, "type": "dateTimeField"},
    ]
    
    # Build the record class
    TestHeaderRecord = build_record_class_from_config("TestHeaderRecord", fields_config)
    
    print("--- Testing with valid data ---")
    try:
        record = TestHeaderRecord(
            record_type_id="H",
            Processing_Id="PR", 
            protocol_version="1.0",
            timestamp=datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
        )
        print("Record created successfully:", dict(record._data))
    except Exception as e:
        print("Validation error:", e)

def main():
    """Run all tests"""
    test_bs240_profile()
    test_erba_profile()
    test_message_processing()
    test_dynamic_record_creation()
    
    print("\n=== Supported Machines ===")
    print("Supported machines:", ProfileFactory.get_supported_machines())

if __name__ == "__main__":
    main()