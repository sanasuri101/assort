# Research Summary: Healthcare AI Voice Platform

## Stack Recommendation
**Pipecat + Daily.co + Deepgram Nova-3 + GPT-4o + Cartesia Sonic** for the voice pipeline. **FastAPI + Redis 7+** for backend (unified state, vectors, pub/sub). **React 19 + Vite + Tailwind** for provider dashboard. Use chained pipeline (STT → LLM → TTS) for v1 — gives maximum control for HIPAA logging between stages. Target sub-500ms voice response latency via streaming at every stage.

## Table Stakes Features
1. Inbound call handling with natural greeting
2. Identity verification (name + DOB) before any PHI access
3. Appointment scheduling (provider, time, visit type, confirmation)
4. Knowledge base for non-PHI questions (hours, insurance, directions)
5. Clinical question detection → transfer to staff
6. Emergency detection → immediate 911/nurse routing
7. Call transcript logging and resolution tracking

## Key Architecture Insight
4 independent layers map cleanly from the SEED: API Layer, Voice Pipeline, Learning Engine, Frontend Dashboard. Redis 7+ serves as the unified data layer (call state via Hashes, knowledge base via JSON + Vector Search, events via Streams). EHR Service is an abstract interface with MockEHRAdapter for v1, FHIR R4 resource types for future real adapters.

## Critical Pitfalls to Address
1. **PHI leakage before verification** (CRITICAL) — State gate: call must be `VERIFIED` before EHR functions fire
2. **Emergency detection false negatives** (CRITICAL) — Separate pre-LLM keyword classifier, not just prompt instructions  
3. **Voice latency >1s** (HIGH) — 40% abandonment rate. Stream everything, pre-warm connections.
4. **Scheduling accuracy** (HIGH) — Confirm all details back to patient, validate slot at booking time
5. **Learning loop feedback cycles** (MEDIUM) — HIPAA filter on extracted patterns, human review queue
6. **Redis SPOF** (MEDIUM) — Enable AOF persistence, connection retry logic
7. **SIP integration complexity** (MEDIUM) — Use Daily.co built-in SIP, test bidirectional audio first
8. **Prompt injection** (MEDIUM) — Clear delimiters, function-call-only data access

## Build Order
Foundation → EHR Service → Voice Pipeline → Healthcare Tools → Learning Engine → Frontend (can overlap with Phase 3+)
