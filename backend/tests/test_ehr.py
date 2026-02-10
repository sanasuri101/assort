import pytest
import uuid
from datetime import date, timedelta
from app.services.ehr.mock import MockEHRAdapter
from app.services.ehr.models import VisitType


@pytest.fixture
def ehr_service():
    return MockEHRAdapter()


@pytest.mark.asyncio
async def test_lookup_patient(ehr_service):
    # Get a real patient from seed data
    patient = list(ehr_service.patients.values())[0]
    full_name = patient.name[0].full_name
    dob = patient.birthDate.strftime("%Y-%m-%d")

    # Test exact match
    found = await ehr_service.lookup_patient(full_name, dob)
    assert found is not None
    assert found.id == patient.id

    # Test case insensitive
    found = await ehr_service.lookup_patient(full_name.upper(), dob)
    assert found is not None
    assert found.id == patient.id

    # Test partial match
    partial_name = full_name.split()[0]
    found = await ehr_service.lookup_patient(partial_name, dob)
    assert found is not None
    assert found.id == patient.id

    # Test not found
    found = await ehr_service.lookup_patient("Non Existent", "2000-01-01")
    assert found is None


@pytest.mark.asyncio
async def test_get_availability(ehr_service):
    # Get a practitioner
    practitioner_id = list(ehr_service.practitioners.keys())[0]
    
    start_date = date.today()
    end_date = start_date + timedelta(days=5)

    slots = await ehr_service.get_availability(practitioner_id, start_date, end_date)
    
    assert isinstance(slots, list)
    # Might be empty if weekends, but unlikely with 5 days range unless M-F all skipped
    # Mock generates slots for M-F
    
    # Verify slot structure
    if slots:
        slot = slots[0]
        assert slot.status == "free"
        assert slot.schedule["reference"].endswith(practitioner_id)


@pytest.mark.asyncio
async def test_book_appointment(ehr_service):
    # Setup
    practitioner_id = list(ehr_service.practitioners.keys())[0]
    patient_id = list(ehr_service.patients.keys())[0]
    
    start_date = date.today()
    end_date = start_date + timedelta(days=7)
    
    slots = await ehr_service.get_availability(practitioner_id, start_date, end_date)
    if not slots:
        pytest.skip("No slots available for testing")
        
    target_slot = slots[0]
    
    # Test booking
    appointment = await ehr_service.book_appointment(
        patient_id=patient_id,
        slot_id=target_slot.id,
        visit_type=VisitType.ROUTINE
    )
    
    assert appointment.status == "booked"
    assert appointment.start == target_slot.start
    assert appointment.end == target_slot.end
    
    # Verify slot is now busy
    updated_slots = await ehr_service.get_availability(practitioner_id, start_date, end_date)
    busy_slot = next((s for s in ehr_service.slots.values() if s.id == target_slot.id), None)
    assert busy_slot.status == "busy"
    
    # Verify double booking fails
    with pytest.raises(ValueError, match="Slot is not free"):
        await ehr_service.book_appointment(
            patient_id=patient_id,
            slot_id=target_slot.id,
            visit_type=VisitType.URGENT
        )
