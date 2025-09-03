from middleware import logger
from middleware.api import APIService, get_api_service
from middleware.models import ErbaMessage
from pydantic import ValidationError

async def test_with_real_api_service(validated_erba: ErbaMessage):
    """Test using the real API service with ErbaMessage model"""
    logger.info("\n=== Testing with Real API Service ===")
    
    try:
        await _send_to_api(validated_erba)
        logger.info(f"API call completed successfully!")        
    except ValidationError as e:
        logger.info(f"ErbaMessage validation failed:")
        logger.info(f"Errors: {e}")
        return
    except Exception as e:
        logger.info(f"API call failed:")
        logger.info(f"Error: {str(e)}")
        logger.info(f"Error type: {type(e).__name__}")

async def test_with_requests_comparison():
    """Test using direct requests for comparison"""
    logger.info("\n=== Testing with Direct Requests (for comparison) ===")
    
    import requests
    
    url = "http://localhost:8000/lab-results/"
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "test_results": [
            {
                "test_code": "GLU",
                "test_name": "Glucose",
                "result_value": "95.5",
                "units": "mg/dL",  # Add if needed
                "reference_range": "70-100",  # Add if needed
                "flags": ""  # Add if needed
            }
        ],
        "timestamp": "2025-09-01T02:54:00Z",
        "analyzer_id": "ANALYZER_001",
        "raw_segments": ["raw", "data", "here"]  # Note: raw_segments for direct API
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        logger.info(f"Status Code: {response.status_code}")
        
        if response.headers.get('content-type', '').startswith('application/json'):
            logger.info(f"Response: {response.json()}")
        else:
            logger.info(f"Response Text: {response.text}")
            
    except requests.exceptions.RequestException as e:
        logger.info(f"Direct request failed: {e}")

async def _send_to_api(validated_message: ErbaMessage):
    """Send validated data to API endpoint using real API service"""
    try:
        logger.info(f"Getting API service...")
        api_service:APIService = get_api_service()
        
        logger.info(f"Sending data via API service...")
        result = await api_service.send_analyzer_data(validated_message)
        await api_service._close_session()

        
        logger.info(f"API service returned: {result}")
        return result
        
    except Exception as e:
        logger.info(f"Error in _send_to_api: {str(e)}")
        logger.info(f"Error type: {type(e).__name__}")
        raise

