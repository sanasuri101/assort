import httpx
import logging
import time
from typing import Optional, Any, Dict

from app.config import settings

logger = logging.getLogger(__name__)

class DailyService:
    """
    Service for Daily.co operations, including room creation and token generation.
    """

    def __init__(self):
        self.api_key = settings.daily_api_key
        self.base_url = "https://api.daily.co/v1"
        logger.info("DailyService initialized")

    async def create_room(self, room_name: Optional[str] = None, expires_in_minutes: int = 60) -> Dict[str, Any]:
        """Create a new Daily.co room."""
        if not self.api_key:
            raise ValueError("Daily API key not configured")

        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            data = {
                "properties": {
                    "exp": int(time.time()) + (expires_in_minutes * 60),
                    "eject_at_room_exp": True,
                    "enable_chat": False,
                }
            }
            if room_name:
                data["name"] = room_name

            resp = await client.post(f"{self.base_url}/rooms", headers=headers, json=data)
            
            if resp.status_code != 200:
                logger.error(f"Failed to create room: {resp.text}")
                raise Exception(f"Daily API error: {resp.text}")
            
            return resp.json()

    async def get_meeting_token(
        self, 
        room_name: str, 
        user_name: str = "user", 
        is_owner: bool = False,
        expires_in_minutes: int = 60
    ) -> str:
        """Generate a meeting token for a Daily.co room."""
        if not self.api_key:
            raise ValueError("Daily API key not configured")

        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            data = {
                "properties": {
                    "room_name": room_name,
                    "user_name": user_name,
                    "is_owner": is_owner,
                    "exp": int(time.time()) + (expires_in_minutes * 60),
                }
            }

            resp = await client.post(f"{self.base_url}/meeting-tokens", headers=headers, json=data)
            
            if resp.status_code != 200:
                logger.error(f"Failed to create token: {resp.text}")
                raise Exception(f"Daily API error: {resp.text}")
            
            return resp.json()["token"]

    async def delete_room(self, room_name: str):
        """Delete a Daily.co room."""
        if not self.api_key:
            raise ValueError("Daily API key not configured")

        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            resp = await client.delete(f"{self.base_url}/rooms/{room_name}", headers=headers)
            if resp.status_code != 200:
                logger.warning(f"Failed to delete room {room_name}: {resp.text}")

_daily_service: Optional[DailyService] = None

def get_daily_service() -> DailyService:
    global _daily_service
    if _daily_service is None:
        _daily_service = DailyService()
    return _daily_service
