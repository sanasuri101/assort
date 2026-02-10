# Stack Research: Healthcare AI Voice Platform

**Confidence: HIGH** — Stack is well-established; Pipecat + Daily.co is the dominant pattern for voice AI in 2025.

## Recommended Stack

### Voice Pipeline
| Component | Recommendation | Version | Rationale |
|-----------|---------------|---------|-----------|
| Pipeline Framework | **Pipecat** | 0.0.54+ | Open-source, modular frame/processor architecture. Daily.co team builds it. Proven in production voice agents. |
| Transport | **Daily.co WebRTC** | `DailyTransport` | First-class Pipecat integration, global edge infrastructure, telephony dial-in/dial-out, free 1:1 voice minutes |
| STT | **Deepgram Nova-3** | Latest | Best real-time accuracy, streaming with partials, medical vocabulary support. Sub-200ms latency. |
| LLM | **GPT-4o** | 2024-11+ | Best instruction-following for function calling (scheduling, EHR lookup). Consider GPT-4o-mini for cost optimization later. |
| TTS | **Cartesia Sonic** | Latest | Best latency/quality ratio. ElevenLabs Flash is alternative. Natural voice critical for healthcare trust. |
| Telephony | **Twilio SIP** | — | Connect Daily.co rooms to phone numbers. Patients call PSTN → SIP → Daily room → Pipecat pipeline. |

### Backend
| Component | Recommendation | Version | Rationale |
|-----------|---------------|---------|-----------|
| API Framework | **FastAPI** | 0.115+ | Async-native, Pydantic v2 validation, OpenAPI docs, HIPAA middleware pattern |
| State Store | **Redis 7+** | 7.4+ | Unified: call state (Hashes), knowledge base (JSON + Vector Search), pub/sub for events |
| Vector Search | **Redis Vector Search** | Built-in | HNSW algorithm, hybrid search (vector + metadata filter). No separate vector DB needed. |
| Embeddings | **Google Gemini** | text-embedding-004 | 768-dim, good semantic quality. Alternative: OpenAI text-embedding-3-small |
| Task Queue | **Redis Streams** or **Celery** | — | Post-call analysis jobs. Redis Streams keeps it in-process; Celery if jobs get complex. |
| Eval/Logging | **Weights & Biases Weave** | Latest | Trace LLM calls, evaluate prompt quality, track learning loop metrics |

### Frontend
| Component | Recommendation | Version | Rationale |
|-----------|---------------|---------|-----------|
| Framework | **React 19** | 19.x | Concurrent features, Server Components ready |
| Build Tool | **Vite** | 6.x | Fast dev server, optimized builds |
| Styling | **Tailwind CSS** | 4.x | Utility-first, rapid UI development |
| Components | **Radix UI** | Latest | Accessible primitives, unstyled. Combine with Tailwind. |
| WebRTC | **Daily.co React SDK** | Latest | Pre-built hooks for call state, tracks, participants |
| Charts | **Recharts** or **Tremor** | Latest | Dashboard analytics visualization |

### Infrastructure
| Component | Recommendation | Rationale |
|-----------|---------------|-----------|
| Local Dev | **Docker Compose** | Redis + FastAPI + Frontend in one `docker-compose up` |
| Deployment | **Docker Compose** (v1) | Single-instance demo. Kubernetes later if needed. |
| Secrets | **Environment variables** | `.env` files, Docker secrets for production |

## What NOT to Use
- **LangChain** — Unnecessary abstraction layer. Direct OpenAI/Gemini SDK calls through Pipecat are simpler.
- **Pinecone/Weaviate** — Redis Vector Search handles our scale. Separate vector DB adds ops complexity.
- **Next.js** — SSR unnecessary for provider dashboard. Vite + React is lighter.
- **WebSocket for voice** — WebRTC via Daily.co handles all real-time audio. Don't build custom WS transport.
- **MongoDB** — Redis covers state + vectors + pub/sub. No need for a separate document store at v1 scale.

## Key Architecture Decision: Chained vs Speech-to-Speech
For v1, use the **chained pipeline** (STT → LLM → TTS). Reasons:
1. Maximum control over each stage (critical for HIPAA — we need to inspect/log text between stages)
2. Function calling (EHR lookup, scheduling) requires text-based LLM
3. Proven pattern with sub-500ms achievable via streaming
4. Speech-to-speech models (GPT-4o Realtime) don't support function calling well yet
