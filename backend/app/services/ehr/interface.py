from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import date

from app.services.ehr.models import Patient, Slot, Appointment, Coverage, VisitType, Practitioner


class EHRService(ABC):
    """Abstract interface for EHR operations."""

    @abstractmethod
    async def lookup_patient(self, name: str, dob: str) -> Optional[Patient]:
        """
        Find a patient by name and date of birth.
        Should support fuzzy matching for name.
        """
        pass

    @abstractmethod
    async def lookup_patient_by_id(self, patient_id: str) -> Optional[Patient]:
        """
        Find a patient by their unique ID.
        """
        pass

    @abstractmethod
    async def get_availability(
        self, provider_id: str, start_date: date, end_date: date
    ) -> List[Slot]:
        """
        Get available appointment slots for a provider within a date range.
        """
        pass

    @abstractmethod
    async def book_appointment(
        self, patient_id: str, slot_id: str, visit_type: VisitType
    ) -> Appointment:
        """
        Book an appointment for a patient in a specific slot.
        """
        pass

    @abstractmethod
    async def check_insurance(self, patient_id: str, plan_id: str) -> Coverage:
        """
        Verify insurance coverage for a patient.
        """
        pass

    @abstractmethod
    async def list_practitioners(self) -> List[Practitioner]:
        """
        List all available practitioners.
        """
        pass
