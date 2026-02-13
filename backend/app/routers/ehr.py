from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, HTTPException, status

from app.dependencies import get_ehr_service
from app.services.ehr.interface import EHRService
from app.services.ehr.models import Slot, Appointment, Patient, VisitType

router = APIRouter(
    tags=["ehr"],
    responses={404: {"description": "Not found"}},
)


@router.get("/patient/search", response_model=Optional[Patient])
async def search_patient(
    name: str = Query(..., description="Patient name (partial match supported)"),
    dob: str = Query(..., description="Date of birth (YYYY-MM-DD)"),
    ehr_service: EHRService = Depends(get_ehr_service),
):
    """
    Look up a patient by name and date of birth.
    Returns the patient resource if found, null otherwise.
    """
    return await ehr_service.lookup_patient(name, dob)


@router.get("/appointments/available", response_model=List[Slot])
async def get_available_slots(
    provider_id: str = Query(..., description="Provider ID"),
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    ehr_service: EHRService = Depends(get_ehr_service),
):
    """
    Get available appointment slots for a provider within a date range.
    """
    return await ehr_service.get_availability(provider_id, start_date, end_date)


@router.post("/appointments/book", response_model=Appointment, status_code=status.HTTP_201_CREATED)
async def book_appointment(
    patient_id: str = Query(..., description="Patient ID"),
    slot_id: str = Query(..., description="Slot ID to book"),
    visit_type: VisitType = Query(..., description="Type of visit"),
    ehr_service: EHRService = Depends(get_ehr_service),
):
    """
    Book an appointment for a patient in a specific slot.
    """
    try:
        return await ehr_service.book_appointment(patient_id, slot_id, visit_type)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
