# Assort Health

## What This Is

AI patient experience platform for healthcare providers. An inbound voice agent that answers patient phone calls, books appointments, answers office questions, and transfers clinical matters to staff — replacing hold queues and reducing front-desk burden. Adapted from a proven AI voice sales agent architecture (wnbHack), redesigned for healthcare with HIPAA compliance, EHR integration, and provider-specific configuration.

## Core Value

A patient can call their doctor's office, speak with the AI agent, and book an appointment that shows up correctly in the provider's scheduling system — accurately, every time.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Inbound voice pipeline: patient calls → AI answers → natural conversation
- [ ] Identity verification before accessing patient records
- [ ] Appointment scheduling with correct provider, time slot, and visit type
- [ ] Mock EHR integration with FHIR-compatible interface design
- [ ] Knowledge base lookup for office questions (hours, insurance, directions)
- [ ] Clinical question detection → transfer to nursing/provider staff
- [ ] Emergency detection → route to 911 / nurse line
- [ ] Post-call transcript logging and resolution tracking
- [ ] Provider dashboard: call history, transcripts, resolution rates
- [ ] Learning loop: extract patterns from transcripts → improve prompts
- [ ] SMS appointment confirmation to patient
- [ ] Provider-specific configuration (scheduling rules, insurance, hours, personality)

### Out of Scope

- Real EHR integration (Athena, Epic, etc.) — requires partnership agreements, v2
- Multi-tenant / multi-provider support — single practice sufficient for demo
- HIPAA formal certification — design for compliance, certify later
- Production scaling — single instance for demo
- Outbound calling — inbound only for v1
- Medical advice, diagnoses, prescriptions — never, by design

## Context

**Origin:** Adapted from wnbHack hackathon repo — a self-improving AI voice sales agent with Pipecat pipeline, Redis state machine, learning loop, and React frontend. Core architecture patterns (voice pipeline, state management, learning loop) transfer directly; domain concepts need healthcare mapping.

**Healthcare mapping:**
- Sales agent → Patient experience agent
- Objection/rebuttal → Patient concern / clinical response
- Deal outcome → Resolution (scheduled, answered, transferred, abandoned)
- Pre-call LinkedIn research → Pre-call EHR/PMS patient lookup
- Country:Industry segments → Provider:Specialty segments

**Call volume distribution:**
- ~50% Scheduling (core value — must nail this)
- ~25% Office/insurance questions (no PHI needed)
- ~15% Clinical/complex (must transfer, never answer)
- ~10% Cancellations, rescheduling, edge cases

**Target metrics (from Assort Health real-world data):**
- 99% scheduling accuracy
- Average hold time: <1 minute (down from 11 minutes)
- 98%+ resolution rate
- Resolution without transfer = key ROI metric for providers

**EHR strategy:** Abstract interface with MockEHRAdapter for v1. FHIR R4 compatible. ~50 fake patients, realistic availability, insurance verification, appointment booking with confirmation numbers. Real adapters (Athenahealth → Epic → DrChrono → eClinicalWorks) plug in for v2.

## Constraints

- **HIPAA compliance**: Design all data handling for HIPAA from day one — encrypt PHI, verify identity before sharing, audit all access, never provide medical advice
- **Voice latency**: Must feel natural — sub-second response times, no awkward pauses
- **No medical advice**: Hard boundary — AI never diagnoses, prescribes, or advises clinically; always transfers
- **Emergency safety**: Must detect emergencies and route to 911 / nurse line immediately
- **Provider specificity**: Each practice has its own scheduling rules, insurance panels, hours, and agent personality

## Stack

- **Python 3.11+**: FastAPI, Pipecat, Redis, Weave (W&B), google-genai
- **Node 20+**: React 19, Vite, Tailwind, Daily.co SDK, Radix UI
- **Redis 7+**: State machine, vector search, knowledge base
- **Voice**: Pipecat → Whisper STT → GPT-4o LLM → TTS → Daily.co WebRTC
- **Infrastructure**: Docker Compose for local dev and deployment

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Mock EHR for v1 | Real integrations require partnerships; mock enables full demo flow | — Pending |
| Single practice for v1 | Multi-tenant adds complexity without demo value | — Pending |
| FHIR R4 interface design | Industry standard; clean adapter pattern for real EHR plugs | — Pending |
| Pipecat voice pipeline | Proven in wnbHack, handles audio pipeline orchestration | — Pending |
| Redis for state + vectors | Single store for call state, knowledge base, and vector search | — Pending |
| 4 independent layers | API, Voice, Learning, Frontend can be built in parallel | — Pending |

---
*Last updated: 2026-02-09 after initialization*
