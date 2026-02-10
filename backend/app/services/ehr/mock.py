import random
import uuid
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict

from faker import Faker

from app.services.ehr.interface import EHRService
from app.services.ehr.models import (
    Patient,
    Slot,
    Appointment,
    Coverage,
    Practitioner,
    HumanName,
    Identifier,
    ContactPoint,
    Gender,
    AppointmentStatus,
    VisitType,
)

fake = Faker()


class MockEHRAdapter(EHRService):
    def __init__(self):
        self.patients: Dict[str, Patient] = {}
        self.practitioners: Dict[str, Practitioner] = {}
        self.slots: Dict[str, Slot] = {}
        self.appointments: Dict[str, Appointment] = {}
        self.coverages: Dict[str, Coverage] = {}
        
        self._seed_data()

    def _seed_data(self):
        # 1. Create Practitioners
        for _ in range(5):
            practitioner_id = str(uuid.uuid4())
            name = HumanName(
                family=fake.last_name(),
                given=[fake.first_name()],
                use="official"
            )
            practitioner = Practitioner(
                id=practitioner_id,
                name=[name],
                telecom=[ContactPoint(system="email", value=fake.email())]
            )
            self.practitioners[practitioner_id] = practitioner

        # 2. Create Patients
        for _ in range(50):
            patient_id = str(uuid.uuid4())
            gender = random.choice([Gender.MALE, Gender.FEMALE])
            patient = Patient(
                id=patient_id,
                name=[HumanName(
                    family=fake.last_name(),
                    given=[fake.first_name_male() if gender == Gender.MALE else fake.first_name_female()],
                    use="official"
                )],
                telecom=[ContactPoint(system="phone", value=fake.phone_number())],
                gender=gender,
                birthDate=fake.date_of_birth(minimum_age=18, maximum_age=90),
                identifier=[Identifier(system="http://hospital.org/mrn", value=str(fake.random_int(min=10000, max=99999)))]
            )
            self.patients[patient_id] = patient
            
            # Create Coverage for patient
            coverage = Coverage(
                id=str(uuid.uuid4()),
                beneficiary={"reference": f"Patient/{patient_id}"},
                payor=[{"display": fake.company()}],
                class_type=[{"name": random.choice(["Gold Plan", "Silver Plan", "Bronze Plan"])}]
            )
            self.coverages[patient_id] = coverage

        # 3. Create Slots (Next 30 days)
        today = date.today()
        for practitioner_id in self.practitioners:
            for day_offset in range(30):
                current_date = today + timedelta(days=day_offset)
                if current_date.weekday() >= 5:  # Skip weekends
                    continue
                
                # 9 AM to 5 PM
                start_time = datetime.combine(current_date, datetime.min.time()).replace(hour=9)
                while start_time.hour < 17:
                    end_time = start_time + timedelta(minutes=30)
                    slot_id = str(uuid.uuid4())
                    slot = Slot(
                        id=slot_id,
                        schedule={"reference": f"Schedule/{practitioner_id}"},
                        status="free",
                        start=start_time,
                        end=end_time
                    )
                    self.slots[slot_id] = slot
                    start_time = end_time

    async def lookup_patient(self, name: str, dob: str) -> Optional[Patient]:
        # Fuzzy match name (case insensitive, partial match)
        target_name = name.lower()
        target_dob = datetime.strptime(dob, "%Y-%m-%d").date()

        for patient in self.patients.values():
            full_name = patient.name[0].full_name.lower()
            if (target_name in full_name or full_name in target_name) and patient.birthDate == target_dob:
                return patient
        return None

    async def lookup_patient_by_id(self, patient_id: str) -> Optional[Patient]:
        return self.patients.get(patient_id)

    async def get_availability(
        self, provider_id: str, start_date: date, end_date: date
    ) -> List[Slot]:
        available_slots = []
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())

        for slot in self.slots.values():
            # Check if slot is for this provider (conceptually via schedule ref which links to practitioner)
            # For simplicity in mock, we'll assume provider_id matches the schedule ref suffix if we parsed it,
            # but our seed uses practitioner_id in schedule ref.
            
            # Extract practitioner ID from schedule reference "Schedule/{id}"
            schedule_ref = slot.schedule.get("reference", "")
            if schedule_ref.endswith(provider_id) and \
               slot.status == "free" and \
               start_datetime <= slot.start <= end_datetime:
                available_slots.append(slot)
        
        return sorted(available_slots, key=lambda s: s.start)

    async def book_appointment(
        self, patient_id: str, slot_id: str, visit_type: VisitType
    ) -> Appointment:
        if slot_id not in self.slots:
            raise ValueError("Slot found not")
        
        slot = self.slots[slot_id]
        if slot.status != "free":
            raise ValueError("Slot is not free")

        # Update slot status
        slot.status = "busy"
        
        # Create appointment
        appointment_id = str(uuid.uuid4())
        appointment = Appointment(
            id=appointment_id,
            status=AppointmentStatus.BOOKED,
            visit_type=visit_type,
            start=slot.start,
            end=slot.end,
            participant=[
                {"actor": {"reference": f"Patient/{patient_id}"}, "status": "accepted"},
                {"actor": slot.schedule, "status": "accepted"} # Using schedule ref for practitioner context
            ],
            description=f"{visit_type.value} appointment"
        )
        self.appointments[appointment_id] = appointment
        return appointment

    async def check_insurance(self, patient_id: str, plan_id: str) -> Coverage:
        # In mock, we just return the coverage we have, ignoring plan_id verification for now
        if patient_id in self.coverages:
            return self.coverages[patient_id]
        
        # Return a default coverage if none found? Or raise?
        # Requirement says "verifies coverage".
        raise ValueError("Coverage not found for patient")

    async def list_practitioners(self) -> List[Practitioner]:
        """List all practitioners."""
        return list(self.practitioners.values())
