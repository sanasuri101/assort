import pytest
from httpx import AsyncClient
from app.services.ehr.models import VisitType


@pytest.mark.asyncio
async def test_search_patient_api(client: AsyncClient):
    # Simple test: Call without params -> 422
    response = await client.get("/api/ehr/patient/search")
    assert response.status_code == 422
    
    # Verify we get *some* response structure even if null
    response = await client.get("/api/ehr/patient/search?name=NonExistent&dob=2000-01-01")
    assert response.status_code == 200
    assert response.json() is None


@pytest.mark.asyncio
async def test_get_availability_api(client: AsyncClient):
    import uuid
    provider_id = str(uuid.uuid4())
    
    response = await client.get(
        f"/api/ehr/appointments/available?provider_id={provider_id}&start_date=2025-01-01&end_date=2025-01-05"
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_book_appointment_api_validation(client: AsyncClient):
    # Test missing params
    response = await client.post("/api/ehr/appointments/book")
    assert response.status_code == 422

