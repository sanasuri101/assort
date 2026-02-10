from app.services.ehr.interface import EHRService
from app.services.ehr.mock import MockEHRAdapter

def get_ehr_service() -> EHRService:
    """
    Factory function to return the EHR service implementation.
    Currently defaults to MockEHRAdapter as the intentional mock.
    """
    return MockEHRAdapter()
