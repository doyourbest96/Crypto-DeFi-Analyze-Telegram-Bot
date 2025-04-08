import logging
import aiohttp

logger = logging.getLogger(__name__)

class APIClient:
    """Client for making API requests to the token analyzer API server"""
    
    def __init__(self):
        self._session = None
    
    async def _get_session(self):
        """Get or create HTTP session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        """Close HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    async def get(self, url, params=None):
        """Make a GET request to the API server"""
        session = await self._get_session()
        
        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"API error: {response.status} - {error_text}")
                    return {"error": f"API error: {response.status}", "detail": error_text}
        except Exception as e:
            logger.error(f"Request error: {str(e)}")
            return {"error": f"Request failed: {str(e)}"}

# Create a singleton instance
api_client = APIClient()
