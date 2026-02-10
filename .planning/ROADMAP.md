# Roadmap: Assort Health

## Overview

Build an AI patient experience platform from foundation to demo-ready in 6 phases. Start with infrastructure and data layer, build the EHR service abstraction, wire up the voice pipeline, add healthcare-specific tools and safety guards, implement the learning engine, and finish with the provider dashboard. Phases 5 and 6 can run in parallel since they depend on different layers.

## Phases

- [ ] **Phase 1: Foundation** - Infrastructure, Redis, FastAPI skeleton, Docker Compose, HIPAA middleware
- [ ] **Phase 2: EHR Service** - Abstract interface, MockEHRAdapter, FHIR R4 resources, patient/provider data
- [ ] **Phase 3: Voice Pipeline** - Pipecat + Daily.co + Deepgram + GPT-4o + Cartesia, basic conversation flow
- [ ] **Phase 4: Healthcare Call Flow** - Identity verification, scheduling, knowledge base, clinical routing, emergency detection
- [ ] **Phase 5: Learning Engine** - Post-call analysis, pattern extraction, prompt optimization, W&B Weave eval
- [ ] **Phase 6: Provider Dashboard** - React frontend with call history, analytics, knowledge management, settings

## Phase Details

### Phase 1: Foundation
**Goal**: All services start with one command, Redis is configured for state + vectors, HIPAA audit middleware is in place, API skeleton accepts requests.
**Depends on**: Nothing (first phase)
**Requirements**: FNDN-01, FNDN-02, FNDN-03, FNDN-04, HIPA-01, HIPA-02, HIPA-06
**Success Criteria** (what must be TRUE):
  1. `docker-compose up` starts FastAPI, Redis, and frontend dev server
  2. Redis has vector search module loaded and AOF persistence enabled
  3. Every API request touching PHI is logged with timestamp, caller, resource, action
  4. Health check endpoints return 200 for all services
  5. API authentication rejects unauthenticated requests
**Plans**: 3 plans

Plans:
- [ ] 01-01: Docker Compose setup (Redis 7+ with vector search, FastAPI, frontend stub)
- [ ] 01-02: FastAPI skeleton with HIPAA audit middleware and auth
- [ ] 01-03: Environment config, health checks, and project structure

### Phase 2: EHR Service
**Goal**: Abstract EHR interface implemented with MockEHRAdapter that returns realistic patient data, provider schedules, and appointment booking — all using FHIR R4 resource types.
**Depends on**: Phase 1
**Requirements**: EHR-01, EHR-02, EHR-03, EHR-04, EHR-05
**Success Criteria** (what must be TRUE):
  1. `lookup_patient(name, dob)` returns matching patient from mock database with fuzzy name matching
  2. `get_availability(provider_id, date_range)` returns realistic time slots
  3. `book_appointment(patient_id, slot_id, visit_type)` creates appointment and returns confirmation number
  4. All data models use FHIR R4 resource types (Patient, Appointment, Schedule, Slot, Practitioner, Coverage)
  5. `check_insurance(patient_id, plan)` verifies coverage
**Plans**: 3 plans

Plans:
- [ ] 02-01: EHR service interface and FHIR R4 data models
- [ ] 02-02: MockEHRAdapter with 50 fake patients, provider schedules, insurance plans
- [ ] 02-03: API endpoints exposing EHR operations and integration tests

### Phase 3: Voice Pipeline
**Goal**: Pipecat voice pipeline handles inbound calls via Daily.co WebRTC, transcribes with Deepgram, responds via GPT-4o, and speaks with Cartesia — achieving sub-500ms latency with streaming at every stage.
**Depends on**: Phase 1
**Requirements**: VOIC-01, VOIC-02, VOIC-03, VOIC-04, VOIC-05, VOIC-06, VOIC-07, VOIC-08, CALL-01, TRNS-01
**Success Criteria** (what must be TRUE):
  1. Inbound call on Twilio number connects to Pipecat pipeline via Daily.co room
  2. AI greets caller with provider-specific greeting
  3. Patient speech is transcribed in real-time (streaming partials visible)
  4. AI responds naturally with <500ms latency (measured)
  5. Patient can interrupt AI mid-sentence and AI stops/adjusts
  6. Full conversation transcript is stored in Redis with timestamps
**Plans**: 4 plans

Plans:
- [ ] 03-01: Pipecat pipeline with DailyTransport, Deepgram STT, Cartesia TTS
- [ ] 03-02: GPT-4o integration with system prompts and function calling framework
- [ ] 03-03: Twilio SIP → Daily.co routing for PSTN inbound calls
- [ ] 03-04: Call state machine, transcript storage, and interruption handling

### Phase 4: Healthcare Call Flow
**Goal**: All three call types work end-to-end: scheduling (verify → search → book → confirm → SMS), knowledge base answers, and clinical/emergency transfers. HIPAA verification gate enforced.
**Depends on**: Phase 2, Phase 3
**Requirements**: HIPA-03, HIPA-04, HIPA-05, CALL-02, CALL-03, CALL-04, CALL-05, CALL-06, TRNS-02, TRNS-03, SMS-01
**Success Criteria** (what must be TRUE):
  1. Patient can verify identity (name + DOB) and agent confirms match against mock EHR
  2. No EHR function calls fire before identity verification succeeds
  3. Scheduling flow books appointment with readback confirmation and SMS notification
  4. Knowledge base answers office questions (hours, insurance, directions) without requiring verification
  5. Clinical questions trigger transfer to staff with conversation context passed
  6. Emergency keywords immediately route to 911/nurse line, bypassing all other logic
  7. Call outcome is classified (scheduled, answered, transferred, abandoned)
**Plans**: 4 plans

Plans:
- [ ] 04-01: Identity verification gate and pre/post-verification system prompts
- [ ] 04-02: Scheduling flow with EHR function calls, slot confirmation, and booking
- [ ] 04-03: Knowledge base vector search and clinical/emergency routing
- [ ] 04-04: SMS confirmation (Twilio), call outcome tracking, and end-to-end testing

### Phase 5: Learning Engine
**Goal**: Post-call analysis extracts patterns and grows the knowledge base. Prompt versions are tracked and compared via W&B Weave. Safety filters prevent HIPAA-violating patterns from entering the system.
**Depends on**: Phase 4
**Requirements**: LERN-01, LERN-02, LERN-03, LERN-04, LERN-05
**Success Criteria** (what must be TRUE):
  1. Completed call triggers automatic transcript analysis (async, via Redis Stream)
  2. Extracted patterns include: successful resolution strategies, new FAQ candidates, failed interaction points
  3. Gemini embeddings are stored in Redis Vector Search and queryable
  4. HIPAA compliance filter blocks patterns containing PHI from entering knowledge base
  5. W&B Weave dashboard shows prompt version comparisons and eval metrics
**Plans**: 3 plans

Plans:
- [ ] 05-01: Post-call transcript analysis pipeline (Redis Stream consumer + Gemini)
- [ ] 05-02: Pattern extraction, embedding generation, and knowledge base growth
- [ ] 05-03: W&B Weave integration, prompt versioning, and HIPAA safety filter

### Phase 6: Provider Dashboard
**Goal**: Provider can view call history and transcripts, manage knowledge base, configure practice settings, and monitor learning loop patterns — all through a polished React dashboard.
**Depends on**: Phase 1 (API Layer)
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, DASH-05
**Success Criteria** (what must be TRUE):
  1. Dashboard home shows call volume, resolution rate, average handle time, and top call reasons
  2. Call history page shows filterable list with full transcript viewer
  3. Knowledge base page allows adding, editing, and deleting FAQ entries
  4. Settings page allows updating practice name, hours, insurance plans, and scheduling rules
  5. Learning loop page shows extracted patterns with approve/reject actions
**Plans**: 4 plans

Plans:
- [ ] 06-01: React + Vite project setup, design system (Tailwind + Radix), routing
- [ ] 06-02: Dashboard home (metrics cards, charts) and call history page (list + transcript viewer)
- [ ] 06-03: Knowledge base management and provider settings pages
- [ ] 06-04: Learning loop visibility page and real-time call status (WebSocket)

## Progress

**Execution Order:**
Phase 1 → Phase 2 & 3 (parallel) → Phase 4 → Phase 5 & 6 (parallel)

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 0/3 | Not started | - |
| 2. EHR Service | 0/3 | Not started | - |
| 3. Voice Pipeline | 0/4 | Not started | - |
| 4. Healthcare Call Flow | 0/4 | Not started | - |
| 5. Learning Engine | 0/3 | Not started | - |
| 6. Provider Dashboard | 0/4 | Not started | - |
