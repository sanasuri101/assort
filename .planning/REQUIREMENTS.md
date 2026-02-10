# Requirements: Assort Health

**Defined:** 2026-02-09
**Core Value:** A patient can call their doctor's office, speak with the AI agent, and book an appointment that shows up correctly in the provider's scheduling system — accurately, every time.

## v1 Requirements

### Foundation

- [ ] **FNDN-01**: Docker Compose starts all services (FastAPI, Redis, Frontend) with one command
- [ ] **FNDN-02**: Redis 7+ configured with AOF persistence and vector search module
- [ ] **FNDN-03**: Environment-based configuration for API keys, provider settings, secrets
- [ ] **FNDN-04**: Health check endpoints for all services

### HIPAA & Security

- [ ] **HIPA-01**: HIPAA audit middleware logs every PHI access (timestamp, caller, resource, action)
- [ ] **HIPA-02**: All PHI encrypted at rest and in transit (TLS for API, encrypted Redis)
- [ ] **HIPA-03**: Identity verification gate — no PHI accessible until patient verified by name + DOB
- [ ] **HIPA-04**: Clinical question detection — AI never provides medical advice, always transfers
- [ ] **HIPA-05**: Emergency detection — immediate routing for emergency keywords, bypasses all other logic
- [ ] **HIPA-06**: API authentication via API keys for provider dashboard access

### EHR Service

- [ ] **EHR-01**: Abstract EHR service interface (lookup_patient, get_availability, book_appointment, check_insurance)
- [ ] **EHR-02**: MockEHRAdapter with ~50 fake patients, realistic provider schedules, insurance plans
- [ ] **EHR-03**: FHIR R4 resource types (Patient, Appointment, Schedule, Slot, Practitioner, Coverage)
- [ ] **EHR-04**: Appointment booking returns confirmation number and validates slot availability at booking time
- [ ] **EHR-05**: Patient lookup supports name + DOB matching with fuzzy matching for name variations

### Voice Pipeline

- [ ] **VOIC-01**: Pipecat pipeline with DailyTransport (WebRTC audio transport)
- [ ] **VOIC-02**: Deepgram Nova-3 STT with streaming partials for low-latency transcription
- [ ] **VOIC-03**: GPT-4o LLM with function calling for EHR operations
- [ ] **VOIC-04**: Cartesia Sonic TTS with streaming for natural speech output
- [ ] **VOIC-05**: Twilio SIP → Daily.co room routing for PSTN inbound calls
- [ ] **VOIC-06**: Sub-500ms voice response latency (measured end-to-end)
- [ ] **VOIC-07**: Interruption handling — patient can interrupt AI mid-sentence
- [ ] **VOIC-08**: Provider-specific system prompt with practice name, personality, and scheduling rules

### Call Flow

- [ ] **CALL-01**: Call state machine (RINGING → GREETING → ROUTING → VERIFIED → RESOLVING → COMPLETED/TRANSFERRED/ABANDONED)
- [ ] **CALL-02**: Scheduling flow — verify identity → search availability → offer slots → confirm → book → SMS confirmation
- [ ] **CALL-03**: Knowledge base flow — answer office questions (hours, insurance, directions) without identity verification
- [ ] **CALL-04**: Transfer flow — detect clinical/complex questions → transfer to staff with conversation context
- [ ] **CALL-05**: Emergency flow — detect emergency keywords → play emergency message → transfer to 911/nurse line immediately
- [ ] **CALL-06**: Confirmation readback — always confirm full appointment details before booking

### Transcript & Analytics

- [ ] **TRNS-01**: Full conversation transcript stored with timestamps per utterance
- [ ] **TRNS-02**: Call outcome classification (scheduled, answered, transferred, abandoned)
- [ ] **TRNS-03**: Call metadata: duration, resolution time, outcome, provider, patient (if verified)

### Learning Engine

- [ ] **LERN-01**: Post-call transcript analysis via Gemini (extract successful patterns, failed interactions, FAQ candidates)
- [ ] **LERN-02**: Gemini embeddings generated for extracted knowledge, stored in Redis Vector Search
- [ ] **LERN-03**: Knowledge base grows from extracted FAQ patterns (pending human review queue)
- [ ] **LERN-04**: Prompt version tracking and comparison via W&B Weave eval metrics
- [ ] **LERN-05**: Safety filter — HIPAA compliance check on every extracted pattern before storage

### Provider Dashboard

- [ ] **DASH-01**: Dashboard home: call volume, resolution rate, average handle time, top call reasons
- [ ] **DASH-02**: Call history page: filterable list of calls with transcript viewer
- [ ] **DASH-03**: Knowledge base management: add/edit/delete FAQ entries for the practice
- [ ] **DASH-04**: Provider settings: practice name, hours, insurance plans, scheduling rules
- [ ] **DASH-05**: Learning loop visibility: view extracted patterns, approve/reject pending knowledge

### SMS & Notifications

- [ ] **SMS-01**: SMS appointment confirmation sent to patient after successful booking (via Twilio)

## v2 Requirements

### Multi-Provider
- **MULT-01**: Multi-tenant architecture — multiple practices with isolated data
- **MULT-02**: Provider onboarding flow with guided configuration

### Real EHR Integration
- **REHR-01**: Athenahealth adapter implementing EHR service interface
- **REHR-02**: Epic (MyChart) adapter with App Orchard certification
- **REHR-03**: DrChrono adapter for specialty practices

### Advanced Voice
- **ADVV-01**: Multi-language support (Spanish at minimum)
- **ADVV-02**: Simultaneous caller handling (queue or parallel rooms)
- **ADVV-03**: Voicemail fallback when system unavailable

### Compliance
- **COMP-01**: Formal HIPAA certification and BAA process
- **COMP-02**: SOC 2 Type II audit trail

### Engagement
- **ENGM-01**: Appointment reminder SMS (24h and 1h before)
- **ENGM-02**: Post-call satisfaction survey via SMS
- **ENGM-03**: Patient portal for self-scheduling

## Out of Scope

| Feature | Reason |
|---------|--------|
| Medical advice / clinical responses | Legal liability, patient safety — always transfer to staff |
| Prescription refills | Requires provider clinical authorization — transfer to nursing |
| Lab result sharing | PHI + clinical interpretation needed — transfer to provider |
| Insurance pre-authorization | Complex, provider-specific — requires human judgment |
| Outbound calling | Different regulatory model — inbound only for v1 |
| Video consultations | Adds complexity without core value — voice-only |
| Chat/text messaging channel | Different interaction model — voice-first |
| Production scaling (K8s, load balancing) | Single-instance Docker Compose sufficient for demo |
| Mobile app | Web dashboard is desktop-first for providers |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FNDN-01 | Phase 1 | Pending |
| FNDN-02 | Phase 1 | Pending |
| FNDN-03 | Phase 1 | Pending |
| FNDN-04 | Phase 1 | Pending |
| HIPA-01 | Phase 1 | Pending |
| HIPA-02 | Phase 1 | Pending |
| HIPA-03 | Phase 4 | Pending |
| HIPA-04 | Phase 4 | Pending |
| HIPA-05 | Phase 4 | Pending |
| HIPA-06 | Phase 1 | Pending |
| EHR-01 | Phase 2 | Pending |
| EHR-02 | Phase 2 | Pending |
| EHR-03 | Phase 2 | Pending |
| EHR-04 | Phase 2 | Pending |
| EHR-05 | Phase 2 | Pending |
| VOIC-01 | Phase 3 | Pending |
| VOIC-02 | Phase 3 | Pending |
| VOIC-03 | Phase 3 | Pending |
| VOIC-04 | Phase 3 | Pending |
| VOIC-05 | Phase 3 | Pending |
| VOIC-06 | Phase 3 | Pending |
| VOIC-07 | Phase 3 | Pending |
| VOIC-08 | Phase 3 | Pending |
| CALL-01 | Phase 3 | Pending |
| CALL-02 | Phase 4 | Pending |
| CALL-03 | Phase 4 | Pending |
| CALL-04 | Phase 4 | Pending |
| CALL-05 | Phase 4 | Pending |
| CALL-06 | Phase 4 | Pending |
| TRNS-01 | Phase 3 | Pending |
| TRNS-02 | Phase 4 | Pending |
| TRNS-03 | Phase 4 | Pending |
| LERN-01 | Phase 5 | Pending |
| LERN-02 | Phase 5 | Pending |
| LERN-03 | Phase 5 | Pending |
| LERN-04 | Phase 5 | Pending |
| LERN-05 | Phase 5 | Pending |
| DASH-01 | Phase 6 | Pending |
| DASH-02 | Phase 6 | Pending |
| DASH-03 | Phase 6 | Pending |
| DASH-04 | Phase 6 | Pending |
| DASH-05 | Phase 6 | Pending |
| SMS-01 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 35 total
- Mapped to phases: 35
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-09*
*Last updated: 2026-02-09 after roadmap creation*
