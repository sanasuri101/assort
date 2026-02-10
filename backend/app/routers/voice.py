import time
import logging
import asyncio
import uuid
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request, Response
from pydantic import BaseModel
import httpx

from app.config import settings
from app.voice.bot import VoiceBot

router = APIRouter()
logger = logging.getLogger(__name__)


class CreateSessionRequest(BaseModel):
    provider_id: str = "default"


class CreateSessionResponse(BaseModel):
    room_url: str
    token: str


class StartAgentRequest(BaseModel):
    room_url: str
    token: str
    provider_id: str = "default"


async def _create_daily_room() -> dict:
    """Create a Daily.co room via REST API. Returns {url, name}."""
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {settings.daily_api_key}"}
        room_resp = await client.post(
            "https://api.daily.co/v1/rooms",
            headers=headers,
            json={
                "properties": {
                    "exp": int(time.time()) + 3600,
                    "eject_at_room_exp": True,
                    "enable_chat": False,
                }
            },
        )
        if room_resp.status_code != 200:
            logger.error(f"Failed to create room: {room_resp.text}")
            raise HTTPException(status_code=500, detail="Failed to create Daily room")
        return room_resp.json()


async def _create_daily_token(room_name: str) -> str:
    """Create a meeting token for a Daily.co room."""
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {settings.daily_api_key}"}
        token_resp = await client.post(
            "https://api.daily.co/v1/meeting-tokens",
            headers=headers,
            json={"properties": {"room_name": room_name}},
        )
        if token_resp.status_code != 200:
            logger.error(f"Failed to create token: {token_resp.text}")
            raise HTTPException(status_code=500, detail="Failed to create Daily token")
        return token_resp.json()["token"]


@router.post("/session", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest):
    """Create a Daily room and return the token/url for WebRTC clients."""
    if not settings.daily_api_key:
        raise HTTPException(status_code=500, detail="Daily API key not configured")

    room_data = await _create_daily_room()
    token = await _create_daily_token(room_data["name"])
    return CreateSessionResponse(room_url=room_data["url"], token=token)


@router.post("/agent/start")
async def start_agent(request: StartAgentRequest, background_tasks: BackgroundTasks):
    """Start the voice agent for a given room."""
    call_id = str(uuid.uuid4())
    background_tasks.add_task(run_bot, request.room_url, request.token, call_id, request.provider_id)
    return {"status": "started", "room_url": request.room_url, "call_id": call_id}


# ── Twilio SIP Integration ────────────────────────────────────────────

@router.post("/incoming")
async def twilio_incoming_call(request: Request):
    """
    Twilio webhook for inbound PSTN calls.
    Creates a Daily.co room, starts the bot, and returns TwiML
    that dials the Daily SIP endpoint so phone audio bridges to WebRTC.
    """
    if not settings.daily_api_key:
        raise HTTPException(status_code=500, detail="Daily API key not configured")

    # Parse Twilio form data
    form = await request.form()
    caller = form.get("From", "unknown")
    logger.info("Incoming call from %s", caller)

    # Create room + token for the bot
    room_data = await _create_daily_room()
    room_url = room_data["url"]
    room_name = room_data["name"]
    bot_token = await _create_daily_token(room_name)

    # Start bot in background
    call_id = str(uuid.uuid4())
    asyncio.create_task(run_bot(room_url, bot_token, call_id, provider_id="default"))

    # Build SIP URI for Daily room
    # Daily SIP format: sip:{room_name}@sip.daily.co
    sip_uri = f"sip:{room_name}@sip.daily.co"

    # Return TwiML that dials the Daily SIP endpoint
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Dial>
        <Sip>{sip_uri}</Sip>
    </Dial>
</Response>"""

    return Response(content=twiml, media_type="application/xml")


@router.post("/status")
async def twilio_call_status(request: Request):
    """Twilio call status callback — logs call lifecycle events."""
    form = await request.form()
    call_sid = form.get("CallSid", "unknown")
    call_status = form.get("CallStatus", "unknown")
    logger.info("Twilio status update: call=%s status=%s", call_sid, call_status)
    return {"received": True}


# ── Bot Runner ─────────────────────────────────────────────────────────

async def run_bot(room_url: str, token: str, call_id: str, provider_id: str):
    try:
        logger.info(f"Starting bot for room {room_url} with call_id {call_id}")
        bot = VoiceBot(room_url, token, call_id, provider_id)
        await bot.start()
        logger.info(f"Bot finished for room {room_url}")
    except Exception as e:
        logger.error(f"Bot failed: {e}")

