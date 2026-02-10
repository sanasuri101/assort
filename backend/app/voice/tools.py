"""
EHR Tool wrappers for OpenAI function calling in the voice pipeline.

All tools are always registered with the LLM. Gated tools check
call_state == VERIFIED before executing. If not verified, they return
a structured error that the LLM incorporates into its response.
"""

import json
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from app.services.ehr.interface import EHRService
from app.voice.call_state import CallState, CallStateMachine

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tool schemas (OpenAI function-calling format)
# ---------------------------------------------------------------------------

TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "verify_patient",
            "description": "Verify a caller's identity by looking up their name and date of birth in the EHR system. Use this BEFORE any other EHR tools.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The patient's full name, e.g. 'John Smith'",
                    },
                    "date_of_birth": {
                        "type": "string",
                        "description": "The patient's date of birth in YYYY-MM-DD format, e.g. '1990-05-15'",
                    },
                },
                "required": ["name", "date_of_birth"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_providers",
            "description": "List all available healthcare providers/doctors in the practice. Use this when the patient wants to know who they can see.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_availability",
            "description": "Get available appointment slots for a specific provider within a date range. Requires identity verification first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "provider_id": {
                        "type": "string",
                        "description": "The unique ID of the healthcare provider/doctor.",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date for availability search in YYYY-MM-DD format. Calculate this based on the user's request (e.g. 'next Tuesday').",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date for availability search in YYYY-MM-DD format. Calculate this based on the user's request.",
                    },
                },
                "required": ["provider_id", "start_date", "end_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": "Book an appointment for the verified patient in a specific time slot. ALWAYS confirm details with the patient before calling this.",
            "parameters": {
                "type": "object",
                "properties": {
                    "slot_id": {
                        "type": "string",
                        "description": "The ID of the available time slot to book.",
                    },
                    "visit_type": {
                        "type": "string",
                        "enum": ["routine", "urgent", "checkup", "followup"],
                        "description": "Type of visit. Map patient language: 'check-up'/'annual' → checkup, 'follow-up' → followup, 'sick visit' → urgent, otherwise → routine.",
                    },
                },
                "required": ["slot_id", "visit_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_insurance",
            "description": "Check insurance coverage for the verified patient. Requires identity verification first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plan_id": {
                        "type": "string",
                        "description": "The insurance plan ID to verify coverage against.",
                    },
                },
                "required": ["plan_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "Answer general questions about the medical practice (hours, location, insurance, policies). Does NOT require verification.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The user's question, e.g. 'What are your hours?' or 'Do you take Aetna?'",
                    },
                },
                "required": ["query"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Tool execution handlers
# ---------------------------------------------------------------------------

def _gate_check_error() -> str:
    """Return structured error for gated tools called before verification."""
    return json.dumps({
        "error": "identity_not_verified",
        "message": "I need to verify your identity first. Can I get your full name and date of birth?",
    })


async def execute_search_knowledge_base(
    call_id: str,
    call_state: CallStateMachine,
    ehr_service: EHRService,
    *,
    query: str,
) -> str:
    """Query knowledge base. UNGATED."""
    from app.voice.knowledge import KnowledgeBase
    from app.config import settings
    
    # Initialize KB (could be singleton in real app)
    kb = KnowledgeBase(settings.redis_url)
    try:
        results = await kb.query(query)
        await kb.close()
        
        if not results:
            return json.dumps({"found": False, "message": "I don't have that information handy. I can transfer you to the front desk if you like."})
            
        return json.dumps({
            "found": True,
            "answer": results[0]["content"]
        })
    except Exception as e:
        logger.error(f"KB query error: {e}")
        await kb.close()
        return json.dumps({"error": "kb_error", "message": "I'm having trouble accessing my information database."})
    return json.dumps({
        "error": "identity_not_verified",
        "message": "I need to verify your identity first. Can I get your full name and date of birth?",
    })


async def execute_verify_patient(
    call_id: str,
    call_state: CallStateMachine,
    ehr_service: EHRService,
    *,
    name: str,
    date_of_birth: str,
) -> str:
    """
    Verify patient identity. NOT gated — this IS the verification.
    On match: transitions call state to VERIFIED, stores patient_id.
    """
    try:
        patient = await ehr_service.lookup_patient(name, date_of_birth)
    except Exception as e:
        logger.error("EHR lookup failed: %s", e)
        return json.dumps({"error": "lookup_failed", "message": "I'm having trouble looking that up. Could you try again?"})

    if patient is None:
        logger.info("Call %s: verification failed for %s / %s", call_id, name, date_of_birth)
        return json.dumps({
            "verified": False,
            "message": "I couldn't find a patient matching that name and date of birth. Could you double-check the spelling or try again?",
        })

    # Verification success — transition state
    try:
        current_state = await call_state.get_state(call_id)
        # Allow transition from ROUTING or GREETING
        if current_state in (CallState.ROUTING, CallState.GREETING):
            await call_state.transition(call_id, CallState.VERIFIED)
        await call_state.set_metadata(call_id, "patient_id", patient.id)
        await call_state.set_metadata(call_id, "patient_name", patient.name[0].full_name)
    except Exception as e:
        logger.error("State transition failed: %s", e)

    logger.info("Call %s: patient verified — %s", call_id, patient.name[0].full_name)
    return json.dumps({
        "verified": True,
        "patient_id": patient.id,
        "patient_name": patient.name[0].full_name,
    })


async def execute_get_availability(
    call_id: str,
    call_state: CallStateMachine,
    ehr_service: EHRService,
    *,
    provider_id: str,
    start_date: str,
    end_date: str,
) -> str:
    """Get available slots. GATED — requires VERIFIED state."""
    if not await call_state.is_verified(call_id):
        return _gate_check_error()

    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        slots = await ehr_service.get_availability(provider_id, start, end)
        return json.dumps({
            "slots": [
                {
                    "slot_id": s.id,
                    "start": s.start.isoformat(),
                    "end": s.end.isoformat(),
                }
                for s in slots[:10]  # Limit to 10 to not overwhelm
            ],
            "total_available": len(slots),
        })
    except Exception as e:
        logger.error("get_availability failed: %s", e)
        return json.dumps({"error": "availability_error", "message": str(e)})


async def execute_book_appointment(
    call_id: str,
    call_state: CallStateMachine,
    ehr_service: EHRService,
    *,
    slot_id: str,
    visit_type: str,
) -> str:
    """Book an appointment. GATED — requires VERIFIED state."""
    if not await call_state.is_verified(call_id):
        return _gate_check_error()

    # Get patient_id from call metadata
    call_info = await call_state.get_call_info(call_id)
    patient_id = call_info.get("patient_id") if call_info else None
    if not patient_id:
        return json.dumps({"error": "no_patient", "message": "Patient information not found."})

    try:
        from app.services.ehr.models import VisitType
        
        appointment = await ehr_service.book_appointment(
            patient_id=patient_id, # type: ignore
            slot_id=slot_id,
            visit_type=VisitType(visit_type)
        )
        
        # Track outcome
        await call_state.set_metadata(call_id, "scheduled", "true")
        await call_state.set_metadata(call_id, "appointment_details", f"{appointment.start}")

        # Transition to RESOLVING then COMPLETED
        try:
            current = await call_state.get_state(call_id)
            if current == CallState.VERIFIED:
                await call_state.transition(call_id, CallState.RESOLVING)
        except Exception:
            pass

        return json.dumps({
            "status": "booked",
            "appointment_id": appointment.id,
            "start": appointment.start.isoformat(),
            "end": appointment.end.isoformat(),
            "visit_type": appointment.visit_type.value,
            "status": appointment.status.value,
            "location": settings.practice_location
        })
    except ValueError as e:
        return json.dumps({"error": "booking_failed", "message": str(e)})
    except Exception as e:
        logger.error("book_appointment failed: %s", e)
        return json.dumps({"error": "booking_error", "message": str(e)})


async def execute_check_insurance(
    call_id: str,
    call_state: CallStateMachine,
    ehr_service: EHRService,
    *,
    plan_id: str,
) -> str:
    """Check insurance coverage. GATED — requires VERIFIED state."""
    if not await call_state.is_verified(call_id):
        return _gate_check_error()

    call_info = await call_state.get_call_info(call_id)
    patient_id = call_info.get("patient_id") if call_info else None
    if not patient_id:
        return json.dumps({"error": "no_patient", "message": "Patient information not found."})

    try:
        coverage = await ehr_service.check_insurance(patient_id, plan_id)
        return json.dumps({
            "status": coverage.status,
            "payor": [p.get("display", "Unknown") for p in coverage.payor],
        })
    except ValueError as e:
        return json.dumps({"error": "insurance_error", "message": str(e)})
    except Exception as e:
        logger.error("check_insurance failed: %s", e)
        return json.dumps({"error": "insurance_error", "message": str(e)})


async def execute_list_providers(
    call_id: str,
    call_state: CallStateMachine,
    ehr_service: EHRService,
) -> str:
    """List providers. GATED — requires VERIFIED state."""
    if not await call_state.is_verified(call_id):
        return _gate_check_error()

    try:
        providers = await ehr_service.list_practitioners()
        return json.dumps({
            "providers": [
                {
                    "id": p.id,
                    "name": p.name[0].full_name,
                }
                for p in providers
            ]
        })
    except Exception as e:
        logger.error("list_providers failed: %s", e)
        return json.dumps({"error": "list_providers_error", "message": str(e)})


# ---------------------------------------------------------------------------
# Tool dispatcher
# ---------------------------------------------------------------------------

TOOL_HANDLERS = {
    "verify_patient": execute_verify_patient,
    "list_providers": execute_list_providers,
    "get_availability": execute_get_availability,
    "book_appointment": execute_book_appointment,
    "check_insurance": execute_check_insurance,
    "search_knowledge_base": execute_search_knowledge_base,
}


async def dispatch_tool(
    tool_name: str,
    tool_args: Dict[str, Any],
    call_id: str,
    call_state: CallStateMachine,
    ehr_service: EHRService,
) -> str:
    """Route a function call to the appropriate handler."""
    handler = TOOL_HANDLERS.get(tool_name)
    if handler is None:
        return json.dumps({"error": "unknown_tool", "message": f"Unknown tool: {tool_name}"})

    return await handler(call_id, call_state, ehr_service, **tool_args)
