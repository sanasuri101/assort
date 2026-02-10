# Features Research: Healthcare AI Voice Platform

**Confidence: HIGH** — Healthcare front-desk automation is a well-defined problem space with clear feature expectations.

## Table Stakes (Must have or providers leave)

### Inbound Call Handling
- Answer calls within 2 rings (no hold queue)
- Natural greeting with practice name
- Handle simultaneous callers (queue or parallel)
- Graceful fallback to voicemail if system unavailable
- **Complexity: Medium** — Pipecat + Daily.co handle this natively

### Appointment Scheduling
- Search provider availability by name, specialty, or next-available
- Book appointment with correct visit type (follow-up, new patient, annual, urgent)
- Confirm date, time, provider, location
- Send SMS/email confirmation
- Cancel and reschedule existing appointments
- **Complexity: High** — Core value. Requires EHR integration + scheduling logic + conflict detection

### Patient Identity Verification
- Verify patient by name + DOB (minimum)
- Match to existing patient record
- Handle new patient registration
- Never share PHI before verification succeeds
- **Complexity: Medium** — Must happen before any PHI access. Critical for HIPAA.

### Knowledge Base (Non-PHI)
- Office hours, locations, directions
- Accepted insurance plans
- Parking information, building access
- General practice information
- **Complexity: Low** — Static content per provider, no PHI concerns

### Clinical Routing
- Detect clinical questions (symptoms, medications, lab results)
- Detect emergency keywords (chest pain, difficulty breathing, suicidal ideation)
- Transfer to appropriate department with context
- Never provide medical advice
- **Complexity: Medium** — Classification problem. False negatives are dangerous.

### Call Transcript & Logging
- Record full conversation transcript
- Log call outcome (scheduled, answered, transferred, abandoned)
- Capture call duration, wait time, resolution time
- **Complexity: Low** — Pipecat provides transcript via STT. Store in Redis.

## Differentiators (Competitive advantage)

### Learning Loop
- Post-call transcript analysis to extract patterns
- Identify common questions → add to knowledge base
- Prompt optimization from successful call patterns
- Track improvement over time with W&B Weave
- **Complexity: High** — This is the "self-improving" aspect from wnbHack

### Provider Dashboard
- Real-time call monitoring
- Historical call analytics (volume, resolution rates, common reasons)
- Provider schedule overview
- Knowledge base management UI
- **Complexity: Medium** — Standard React dashboard

### Provider-Specific Personality
- Custom greeting, tone, vocabulary per practice
- Practice-specific scheduling rules (buffer time, visit type durations)
- Hierarchical prompt fallback (provider → specialty → default)
- **Complexity: Medium** — Config-driven, not code-driven

### SMS Integration
- Appointment confirmation via SMS
- Appointment reminders
- Post-call follow-up
- **Complexity: Low** — Twilio SMS API

### Multi-Language Support
- Spanish language support (covers ~13% of US patients)
- Language detection and automatic switching
- **Complexity: Medium** — STT/TTS providers support it; prompts need translation

## Anti-Features (Deliberately NOT building)

| Anti-Feature | Why Not |
|-------------|---------|
| Medical advice | Legal liability, patient safety, HIPAA. Always transfer. |
| Prescription refills | Clinical workflow — requires provider authorization |
| Lab result sharing | PHI + clinical interpretation needed — transfer to nurse |
| Insurance pre-authorization | Complex, provider-specific, requires human judgment |
| Outbound calling (reminders) | Different regulatory requirements, v2+ |
| Video calls | Adds complexity without core value. Voice-only for v1. |
| Chat/text channels | Different interaction model. Voice-first. |

## Feature Dependencies

```
Identity Verification ──→ Appointment Scheduling (must verify before booking)
                      ──→ Any PHI Access
Knowledge Base ──→ No dependencies (public info)
Clinical Routing ──→ Transfer Infrastructure (Daily.co SIP transfer)
Learning Loop ──→ Call Transcripts (needs completed call data)
Dashboard ──→ Call Transcripts + Analytics (read-only views)
```
