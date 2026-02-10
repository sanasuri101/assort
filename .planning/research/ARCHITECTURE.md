# Architecture Research: Healthcare AI Voice Platform

**Confidence: HIGH** — Architecture directly maps from wnbHack patterns; healthcare domain adds HIPAA middleware and EHR adapter layers.

## System Components

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND (React)                     │
│  Provider Dashboard │ Call Monitor │ Knowledge Mgmt     │
└──────────────┬──────────────────────────────────────────┘
               │ REST/WebSocket
┌──────────────▼──────────────────────────────────────────┐
│                   API LAYER (FastAPI)                    │
│  HIPAA Middleware │ Auth │ Provider Config │ Analytics   │
└──────┬────────────┬──────────────────────┬──────────────┘
       │            │                      │
┌──────▼──────┐ ┌───▼───────────┐  ┌──────▼──────────────┐
│ VOICE       │ │ EHR SERVICE   │  │ LEARNING ENGINE     │
│ PIPELINE    │ │ (Mock/Real)   │  │                     │
│             │ │               │  │ Transcript Analyzer │
│ Daily.co ◄──┤ │ Patient DB    │  │ Pattern Extractor   │
│ Pipecat  ◄──┤ │ Schedule DB   │  │ Prompt Optimizer    │
│ Deepgram    │ │ Insurance DB  │  │ W&B Eval            │
│ GPT-4o      │ │ FHIR R4 API   │  │                     │
│ Cartesia    │ │               │  │                     │
└──────┬──────┘ └───────────────┘  └──────┬──────────────┘
       │                                   │
┌──────▼───────────────────────────────────▼──────────────┐
│                     REDIS 7+                            │
│  Call State │ Knowledge Base │ Vectors │ Event Streams  │
└─────────────────────────────────────────────────────────┘
```

## Component Boundaries

### 1. API Layer
**Responsibility:** HTTP API, authentication, HIPAA middleware, provider configuration, analytics queries.

**Talks to:** Redis (state), EHR Service, Frontend (serves API), Voice Pipeline (call lifecycle events)

**Key patterns:**
- HIPAA audit middleware logs every PHI access with timestamp, user, resource, action
- Provider config loaded from Redis on each request (hot-reloadable)
- Auth via API keys for provider dashboard (JWT tokens for sessions)

### 2. Voice Pipeline
**Responsibility:** Handle inbound calls, run conversation, execute tools (schedule, lookup, transfer).

**Talks to:** Daily.co (WebRTC transport), Redis (call state), EHR Service (patient lookup, scheduling), API Layer (call lifecycle events)

**Key patterns:**
- Pipecat pipeline: `Transport → STT → UserContextAggregator → LLM → TTS → Transport`
- Function calling for EHR operations (lookup_patient, get_availability, book_appointment)
- Redis call state machine: `call:{id}` hash with status progression
- Interruption handling via Pipecat's system frames

**Call state machine:**
```
RINGING → GREETING → ROUTING → VERIFIED → RESOLVING → COMPLETED
                                    ↓
                              TRANSFERRING → TRANSFERRED
                                    ↓
                               ABANDONED (patient hung up)
```

### 3. EHR Service
**Responsibility:** Abstract interface to patient records, scheduling, insurance verification.

**Talks to:** API Layer, Voice Pipeline (via function calls)

**Key patterns:**
- Abstract `EHRService` interface with methods: `lookup_patient()`, `get_availability()`, `book_appointment()`, `check_insurance()`, `get_patient_appointments()`
- `MockEHRAdapter` for v1 — returns realistic fake data
- FHIR R4 resource types: Patient, Appointment, Schedule, Slot, Coverage, Practitioner
- Real adapters (Athena, Epic) plug into same interface later

### 4. Learning Engine
**Responsibility:** Post-call analysis, pattern extraction, prompt optimization, eval tracking.

**Talks to:** Redis (read transcripts, write patterns/embeddings), W&B Weave (eval metrics)

**Key patterns:**
- Triggered after call completes (Redis Stream consumer)
- Gemini analyzes transcript → extracts: successful patterns, failed interactions, new FAQ candidates
- Embeddings generated for extracted knowledge → stored in Redis Vector Search
- Prompt optimization: compare prompt versions via W&B Weave eval metrics
- Knowledge base grows organically from real call patterns

### 5. Frontend Dashboard
**Responsibility:** Provider-facing UI for monitoring, configuration, analytics.

**Talks to:** API Layer (REST), WebSocket (real-time call events)

**Key patterns:**
- React SPA with Vite build
- Pages: Dashboard (metrics), Calls (history + transcripts), Knowledge Base (manage), Settings (provider config)
- Real-time call status via WebSocket (active calls, live transcripts)
- Responsive design but desktop-first (providers use desktops)

## Data Flow

### Inbound Call Flow
```
1. Patient dials → Twilio SIP → Daily.co Room
2. Pipecat pipeline starts → Greeting frame plays
3. Patient speaks → Deepgram STT (streaming partials)
4. Text → GPT-4o with system prompt + provider config
5. LLM decides:
   a. Need identity? → Ask name + DOB → verify via EHR
   b. Scheduling? → Function call: get_availability() → offer slots → book_appointment()  
   c. Knowledge question? → Vector search Redis knowledge base
   d. Clinical? → Transfer via Daily.co SIP → end call
   e. Emergency? → Play emergency message → transfer immediately
6. LLM response → Cartesia TTS (streaming) → Audio to patient
7. Call completes → Store transcript in Redis
8. Learning engine picks up transcript → analyze → extract → embed
```

### Data Storage (Redis)
```
call:{id}                → Hash: status, provider_id, patient_id, start_time, outcome
call:{id}:transcript     → List: timestamped utterances
call:{id}:events         → Stream: lifecycle events
provider:{id}:config     → JSON: scheduling rules, insurance, hours, prompts
provider:{id}:knowledge  → JSON+Vector: FAQ entries with embeddings
patient:{id}             → JSON: mock patient data (v1)
schedule:{provider_id}   → JSON: availability slots
patterns:{provider_id}   → JSON+Vector: learned patterns from calls
```

## Build Order (Dependencies)

```
Phase 1: Foundation
  → Redis setup, FastAPI skeleton, Docker Compose, HIPAA middleware pattern

Phase 2: EHR Service
  → Abstract interface + MockEHRAdapter + FHIR resources

Phase 3: Voice Pipeline  
  → Pipecat + Daily.co + STT/TTS + basic conversation
  → Depends on: EHR Service (for function calling)

Phase 4: Healthcare Tools
  → Identity verification, scheduling, knowledge base, clinical routing
  → Depends on: Voice Pipeline + EHR Service

Phase 5: Learning Engine
  → Post-call analysis, pattern extraction, prompt optimization
  → Depends on: Completed calls (transcripts)

Phase 6: Frontend Dashboard
  → Can start in parallel with Phase 3+ (API endpoints exist)
```
