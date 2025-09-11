"""
Complete API Service for Middleware Engine
Handles validated data transmission to external APIs
"""

import asyncio
import json
from configuration.logger import logger
from erba.models import APIResult, ErbaMessage
from erba.constants import API_TIMEOUT, BASE_API_URL
from typing import (
    Dict, 
    Any
)
from aiohttp import (
    ClientError,
    TCPConnector,
    ClientSession,
    ClientTimeout
)

class APIService:
    """Handles API communication for validated analyzer data"""
    
    def __init__(self, base_url: str = "http://localhost:8000", timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = None
        self.retry_attempts = 3
        self.retry_delay = 1.0
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_session()
        return self
        
    async def __aexit__(self):
        """Async context manager exit"""
        await self._close_session()
    
    async def _ensure_session(self):
        """Ensure session is created"""
        if not self.session or self.session.closed:
            connector = TCPConnector(
                limit=10,
                limit_per_host=5,
                keepalive_timeout=30
            )
            
            self.session = ClientSession(
                timeout=ClientTimeout(total=self.timeout),
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'Middleware-Engine/1.0'
                },
                connector=connector
            )

            logger.info("Session Created Successfully")

    async def _close_session(self):
        """Close session if exists"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
            logger.info("Session Closed Successfully")

    async def send_analyzer_data(self, validated_message: ErbaMessage) -> APIResult:
        """Send validated analyzer data to API with retry logic"""
    
        await self._ensure_session()
        payload: dict[str, Any] = validated_message.model_dump()

        if not isinstance(payload, dict):
            logger.error("The payload must be of type dict")
            return APIResult(success=False, error="Payload must be of type dict")

        endpoint = f"{self.base_url}/lab-results/"
        last_error = None
    
        for attempt in range(self.retry_attempts):
            try:
                logger.debug(f"API attempt {attempt + 1}/{self.retry_attempts} to {endpoint}")
            
                async with self.session.post(endpoint, json=payload) as response:
                    logger.debug(f"Request sent: {response.status} - Content-Length: {len(json.dumps(payload))}")
                
                    # Fetch the response
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
                        return APIResult(
                            success=True,
                            data=response_data,
                            status_code=response.status,
                            retry_attempted=attempt > 0
                        )
                
                    # Client errors (don't retry)
                    elif 400 <= response.status < 500:
                        error_msg = f"Client error {response.status}: {response_data}"
                        return APIResult(
                            success=False,
                            error=error_msg,
                            data=response_data,
                            status_code=response.status,
                            retry_attempted=False
                        )
                
                    # Server errors (retry)
                    else:
                        error_msg = f"Server error {response.status}: {response_data}"
                        last_error = error_msg
                        
                        if attempt < self.retry_attempts - 1:
                            await asyncio.sleep(self.retry_delay * (attempt + 1))
                            continue
                        
                        return APIResult(
                            success=False,
                            error=error_msg,
                            data=response_data,
                            status_code=response.status,
                            retry_attempted=True
                        )
                    
            except TimeoutError:
                error_msg = f"Request timeout after {self.timeout}s (attempt {attempt + 1})"
                logger.warning(error_msg)
                last_error = error_msg
                
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                    
            except ClientError as e:
                error_msg = f"Client connection error: {str(e)} (attempt {attempt + 1})"
                logger.warning(error_msg)
                last_error = error_msg
                
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue

            except AttributeError as e:
                error_msg = f"Attribute not found: {type(logger)} -> {str(e)}"
                logger.warning(error_msg)
                last_error = error_msg
                break
                    
            except Exception as e:
                error_msg = f"Unexpected error: {str(e)} (attempt {attempt + 1})"
                logger.warning(error_msg)
                last_error = error_msg
                break
    
        logger.error(f"All {self.retry_attempts} API attempts failed. Last error: {last_error}")
        return APIResult(
            success=False,
            error=last_error or 'All retry attempts failed',
            status_code=0,
            retry_attempted=True
        )

    
    async def health_check(self) -> Dict[str, Any]:
        """Check API health/connectivity"""
        try:
            await self._ensure_session()
            
            health_endpoint = f"{self.base_url}/health"
            
            async with self.session.get(health_endpoint, timeout=ClientTimeout(total=5)) as response:
                if response.status == 200:
                    return {
                        'healthy': True,
                        'status_code': response.status,
                        'response_time_ms': 0
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

_api_service_instance = None

# Helper methods to access api service methods
def get_api_service() -> APIService:
    """Get singleton API service instance"""
    global _api_service_instance
    
    base_url: str = BASE_API_URL
    timeout: int = API_TIMEOUT

    if _api_service_instance is None:
        _api_service_instance = APIService(base_url, timeout)
    
    return _api_service_instance

async def close_api_service():
    """Close API service"""
    global _api_service_instance
    
    if _api_service_instance:
        await _api_service_instance._close_session()
        _api_service_instance = None