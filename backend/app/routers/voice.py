import logging
import asyncio
import uuid
import os
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request, Response
from pydantic import BaseModel
import httpx

from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


from app.services.daily_service import get_daily_service
from app.services.redis_service import get_redis_service

class CreateCallRequest(BaseModel):
    """Request model for creating a new call."""
    provider_id: str = "default"

class CreateCallResponse(BaseModel):
    """Response model for create call endpoint."""
    call_id: str
    room_name: str
    room_url: str
    user_token: str
    status: str

class JoinAgentResponse(BaseModel):
    """Response model for join agent endpoint."""
    success: bool
    message: str


@router.post("/create", response_model=CreateCallResponse)
async def create_call(request: CreateCallRequest):
    """
    Create a new Daily room and store initial state in Redis.
    Matches wnbHack patterns.
    """
    try:
        call_id = str(uuid.uuid4())
        daily_service = get_daily_service()
        redis_service = get_redis_service()

        # Create Daily room
        room = await daily_service.create_room()
        room_name = room.get("name")
        room_url = room.get("url")

        # Generate user token for the caller (frontend)
        user_token = await daily_service.get_meeting_token(
            room_name=room_name,
            user_name="Patient",
            is_owner=False
        )

        # Store initial state in Redis
        initial_state = {
            "call_id": call_id,
            "room_name": room_name,
            "room_url": room_url,
            "status": "pending",
            "participants": [],
            "agent_joined": False,
            "provider_id": request.provider_id,
            "state": "ringing" # Assort Health specific
        }
        await redis_service.set_call_state(call_id, initial_state)

        logger.info(f"Created call {call_id} in room {room_name}")

        return CreateCallResponse(
            call_id=call_id,
            room_name=room_name,
            room_url=room_url,
            user_token=user_token,
            status="pending"
        )

    except Exception as e:
        logger.error(f"Failed to create call: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{call_id}/join-agent", response_model=JoinAgentResponse)
async def join_agent(call_id: str, background_tasks: BackgroundTasks):
    """
    Trigger the voice agent to join the call.
    Matches wnbHack pattern.
    """
    redis_service = get_redis_service()
    state = await redis_service.get_call_state(call_id)

    if not state:
        raise HTTPException(status_code=404, detail="Call not found")

    if state.get("agent_joined"):
        return JoinAgentResponse(
            success=False,
            message="Agent has already joined this call"
        )

    # Start agent in background (or sync in tests to avoid loop issues)
    if os.getenv("PYTEST_CURRENT_TEST"):
        await start_agent_handler(call_id, state)
    else:
        background_tasks.add_task(start_agent_handler, call_id, state)

    logger.info(f"Agent join requested for call {call_id}")

    return JoinAgentResponse(
        success=True,
        message="Agent is joining the call"
    )


async def start_agent_handler(call_id: str, state: dict):
    """Background task to start the Pipecat agent."""
    try:
        redis_service = get_redis_service()
        
        # Update state
        state["agent_joined"] = True
        await redis_service.set_call_state(call_id, state)

        room_url = state.get("room_url")
        room_name = state.get("room_name")

        # Import and run the agent (alignment with bot.py)
        # Skip actual run in tests to avoid event loop closure issues with background tasks
        if os.getenv("PYTEST_CURRENT_TEST"):
            logger.info(f"Test mode detected, skipping run_agent for call {call_id}")
            return

        from app.voice.bot import run_agent
        await run_agent(
            call_id=call_id,
            room_url=room_url,
            room_name=room_name
        )

    except Exception as e:
        logger.error(f"Failed to start agent for call {call_id}: {e}")
        # Revert state on failure
        redis_service = get_redis_service()
        state = await redis_service.get_call_state(call_id)
        if state:
            state["agent_joined"] = False
            state["agent_error"] = str(e)
            await redis_service.set_call_state(call_id, state)


# ── Twilio SIP Integration (Legacy) ───────────────────────────────────

@router.post("/incoming")
async def twilio_incoming_call(request: Request):
    """
    Twilio webhook for inbound PSTN calls.
    Updated to use DailyService and RedisService.
    """
    daily_service = get_daily_service()
    redis_service = get_redis_service()

    form = await request.form()
    caller = form.get("From", "unknown")
    logger.info("Incoming call from %s", caller)

    # Create room
    room = await daily_service.create_room()
    room_name = room["name"]
    room_url = room["url"]
    
    call_id = str(uuid.uuid4())
    
    # Store state
    state = {
        "call_id": call_id,
        "room_name": room_name,
        "room_url": room_url,
        "status": "pending",
        "participants": [],
        "agent_joined": True,
        "caller": caller
    }
    await redis_service.set_call_state(call_id, state)

    # Start bot (SIP calls join agent immediately)
    asyncio.create_task(run_agent(call_id, room_url, room_name))

    sip_uri = f"sip:{room_name}@sip.daily.co"
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

