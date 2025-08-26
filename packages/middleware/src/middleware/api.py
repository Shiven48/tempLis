"""
Complete API Service for Middleware Engine
Handles validated data transmission to external APIs
"""

import aiohttp
import asyncio
import json
from typing import Optional, Dict, Any, Union
from dataclasses import asdict, is_dataclass
import logging
from datetime import datetime

class APIService:
    """Handles API communication for validated analyzer data"""
    
    def __init__(self, base_url: str = "http://localhost:8000", timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = None
        self.logger = logging.getLogger(__name__)
        self.retry_attempts = 3
        self.retry_delay = 1.0
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_session()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self._close_session()
    
    async def _ensure_session(self):
        """Ensure session is created"""
        if not self.session or self.session.closed:
            connector = aiohttp.TCPConnector(
                limit=10,
                limit_per_host=5,
                keepalive_timeout=30
            )
            
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'Middleware-Engine/1.0'
                },
                connector=connector
            )
    
    async def _close_session(self):
        """Close session if exists"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
    
    def _serialize_data(self, data: Any) -> Any:
        """Convert complex objects to JSON-serializable format"""
        if is_dataclass(data):
            return asdict(data)
        elif hasattr(data, '__dict__'):
            # Convert object to dict
            result = {}
            for key, value in data.__dict__.items():
                if not key.startswith('_'):  # Skip private attributes
                    result[key] = self._serialize_data(value)
            return result
        elif isinstance(data, (list, tuple)):
            return [self._serialize_data(item) for item in data]
        elif isinstance(data, dict):
            return {key: self._serialize_data(value) for key, value in data.items()}
        elif isinstance(data, datetime):
            return data.isoformat()
        elif hasattr(data, 'isoformat'):  # Other datetime-like objects
            return data.isoformat()
        else:
            return data
    
    def _prepare_payload(self, validated_message, analyzer_name: str) -> Dict[str, Any]:
        """Prepare API payload from validated message"""
        
        # Base payload structure
        payload = {
            'analyzer': analyzer_name,
            'timestamp': datetime.now().isoformat(),
            'source': 'middleware-engine',
            'version': '1.0'
        }
        
        # Handle different message types
        if hasattr(validated_message, '__dict__'):
            # Convert object to serializable format
            message_data = self._serialize_data(validated_message)
            
            # Structure the payload based on available attributes
            if 'patient' in message_data:
                payload['patient_info'] = message_data['patient']
            
            if 'test_results' in message_data:
                payload['test_results'] = message_data['test_results']
                payload['result_count'] = len(message_data['test_results'])
            
            if 'message_id' in message_data:
                payload['message_id'] = message_data['message_id']
            
            if 'timestamp' in message_data:
                payload['original_timestamp'] = message_data['timestamp']
            
            if 'raw_hl7' in message_data:
                payload['raw_data'] = message_data['raw_hl7']
            
            # Include full message data
            payload['validated_data'] = message_data
            
        else:
            # Fallback for simple data types
            payload['data'] = str(validated_message)
            payload['data_type'] = type(validated_message).__name__
        
        return payload
    
    async def send_analyzer_data(self, validated_message, analyzer_name: str) -> Dict[str, Any]:
        """Send validated analyzer data to API with retry logic"""
        
        await self._ensure_session()
        
        payload = self._prepare_payload(validated_message, analyzer_name)
        endpoint = f"{self.base_url}/app/analyzer/parse"
        
        last_error = None
        
        for attempt in range(self.retry_attempts):
            try:
                self.logger.debug(f"API attempt {attempt + 1}/{self.retry_attempts} to {endpoint}")
                
                async with self.session.post(endpoint, json=payload) as response:
                    
                    # Log request details
                    self.logger.debug(f"Request sent: {response.status} - Content-Length: {len(json.dumps(payload))}")
                    
                    # Handle response
                    if response.content_type == 'application/json':
                        try:
                            response_data = await response.json()
                        except json.JSONDecodeError:
                            response_text = await response.text()
                            response_data = {'raw_response': response_text}
                    else:
                        response_data = {'raw_response': await response.text()}
                    
                    # Success cases
                    if response.status in [200, 201, 202]:
                        self.logger.info(f"API success: {response.status}")
                        return {
                            'success': True,
                            'status_code': response.status,
                            'data': response_data,
                            'attempt': attempt + 1
                        }
                    
                    # Client errors (don't retry)
                    elif 400 <= response.status < 500:
                        error_msg = f"Client error {response.status}: {response_data}"
                        self.logger.error(error_msg)
                        return {
                            'success': False,
                            'status_code': response.status,
                            'error': error_msg,
                            'data': response_data,
                            'retry_attempted': False
                        }
                    
                    # Server errors (retry)
                    else:
                        error_msg = f"Server error {response.status}: {response_data}"
                        self.logger.warning(f"Retryable error on attempt {attempt + 1}: {error_msg}")
                        last_error = error_msg
                        
                        if attempt < self.retry_attempts - 1:
                            await asyncio.sleep(self.retry_delay * (attempt + 1))
                            continue
                        
                        return {
                            'success': False,
                            'status_code': response.status,
                            'error': error_msg,
                            'data': response_data,
                            'retry_attempted': True,
                            'final_attempt': attempt + 1
                        }
                        
            except asyncio.TimeoutError:
                error_msg = f"Request timeout after {self.timeout}s (attempt {attempt + 1})"
                self.logger.warning(error_msg)
                last_error = error_msg
                
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                    
            except aiohttp.ClientError as e:
                error_msg = f"Client connection error: {str(e)} (attempt {attempt + 1})"
                self.logger.warning(error_msg)
                last_error = error_msg
                
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                    
            except Exception as e:
                error_msg = f"Unexpected error: {str(e)} (attempt {attempt + 1})"
                self.logger.error(error_msg)
                last_error = error_msg
                break  # Don't retry unexpected errors
        
        # All attempts failed
        self.logger.error(f"All {self.retry_attempts} API attempts failed. Last error: {last_error}")
        return {
            'success': False,
            'error': last_error or 'All retry attempts failed',
            'status_code': 0,
            'retry_attempted': True,
            'final_attempt': self.retry_attempts
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check API health/connectivity"""
        try:
            await self._ensure_session()
            
            health_endpoint = f"{self.base_url}/health"
            
            async with self.session.get(health_endpoint, timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    return {
                        'healthy': True,
                        'status_code': response.status,
                        'response_time_ms': 0  # Could implement timing if needed
                    }
                else:
                    return {
                        'healthy': False,
                        'status_code': response.status,
                        'error': f"Health check returned {response.status}"
                    }
                    
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e),
                'status_code': 0
            }

# Singleton instance for middleware engine
_api_service_instance = None

def get_api_service(base_url: str = "http://localhost:8000", timeout: int = 30) -> APIService:
    """Get singleton API service instance"""
    global _api_service_instance
    
    if _api_service_instance is None:
        _api_service_instance = APIService(base_url, timeout)
    
    return _api_service_instance

async def close_api_service():
    """Close singleton API service"""
    global _api_service_instance
    
    if _api_service_instance:
        await _api_service_instance._close_session()
        _api_service_instance = None