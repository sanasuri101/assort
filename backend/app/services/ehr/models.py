"""
FHIR R4 compatible Pydantic models for the EHR Service.
Lightweight implementation to avoid heavy dependency overhead.
"""

from datetime import date, datetime
from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNKNOWN = "unknown"


class AppointmentStatus(str, Enum):
    PROPOSED = "proposed"
    PENDING = "pending"
    BOOKED = "booked"
    ARRIVED = "arrived"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"
    NOSHOW = "noshow"


class VisitType(str, Enum):
    ROUTINE = "routine"
    URGENT = "urgent"
    CHECKUP = "checkup"
    FOLLOWUP = "followup"


class Coding(BaseModel):
    system: str
    code: str
    display: Optional[str] = None


class Identifier(BaseModel):
    use: Optional[str] = None
    system: Optional[str] = None
    value: str


class HumanName(BaseModel):
    use: Optional[str] = None
    family: str
    given: List[str] = []
    
    @property
    def full_name(self) -> str:
        return f"{' '.join(self.given)} {self.family}"


class ContactPoint(BaseModel):
    system: str  # phone, email, etc.
    value: str
    use: Optional[str] = None


class Patient(BaseModel):
    resourceType: str = "Patient"
    id: str
    identifier: List[Identifier] = []
    active: bool = True
    name: List[HumanName] = []
    telecom: List[ContactPoint] = []
    gender: Optional[Gender] = None
    birthDate: date


class Practitioner(BaseModel):
    resourceType: str = "Practitioner"
    id: str
    identifier: List[Identifier] = []
    name: List[HumanName] = []
    telecom: List[ContactPoint] = []


class Slot(BaseModel):
    resourceType: str = "Slot"
    id: str
    schedule: dict  # Reference to Schedule
    status: str  # busy | free | busy-unavailable | busy-tentative
    start: datetime
    end: datetime
    comment: Optional[str] = None


class Coverage(BaseModel):
    resourceType: str = "Coverage"
    id: str
    status: str = "active"
    subscriberId: Optional[str] = None
    beneficiary: dict  # Reference to Patient
    payor: List[dict] = []  # Reference to Organization
    class_type: Optional[List[dict]] = Field(None, alias="class")  # Plan details


class Appointment(BaseModel):
    resourceType: str = "Appointment"
    id: str
    status: AppointmentStatus
    visit_type: VisitType
    start: datetime
    end: datetime
    participant: List[dict] = []  # List of participants (patient, practitioner)
    description: Optional[str] = None
