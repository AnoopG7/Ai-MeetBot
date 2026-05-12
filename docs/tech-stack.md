# Technology Stack — Personal Finance Advisor AI Agent

> Every library, model, service, and tool selected with rationale. Built on **LiveKit Agents** for real-time audio/WebRTC infrastructure.

---

## 1. Runtime & Language

| Choice | Version | Why |
|--------|---------|-----|
| **Python** | 3.12+ | AI/ML ecosystem leader. PyTorch, LiveKit Agents, LangChain, FastAPI all native. |
| **Node.js** | 20 LTS | Frontend build tooling (Vite, pnpm). LiveKit React SDK. |
| **TypeScript** | 5.x | Type safety in the frontend. |

---

## 2. Core Framework: LiveKit Agents

| Aspect | Detail |
|--------|--------|
| **What it does** | Real-time audio pipeline: VAD → STT → LLM → TTS with WebRTC transport, barge-in, state management |
| **What we don't write** | WebRTC server, audio buffers, Opus codec, ICE/STUN/TURN, VAD integration, interruption handling, session lifecycle |
| **What we still own** | Finance RAG, CV pipeline, emotion fusion, compliance, memory, tools |
| **License** | Apache 2.0 |
| **Stars** | 10.4k |
| **Backed by** | LiveKit (YC W22, $10M+) |

```python
# Total code to get a voice conversation started:
session = AgentSession(
    vad=silero.VAD(),
    stt=deepgram.STT(model="nova-3"),
    llm=openai.LLM(model="gpt-4o-mini"),
    tts=cartesia.TTS(model="sonic-2-english"),
)
agent = Agent(instructions="...", tools=[...])
await session.start(agent=agent, room=ctx.room)
```

### LiveKit Plugin Ecosystem

| Category | Plugin | Use |
|----------|--------|-----|
| **VAD** | `livekit-plugins-silero` | Voice Activity Detection (local, <1ms) |
| **STT** | `livekit-plugins-whisper` | Local Whisper large-v3 (free, ~1s latency) |
| **STT** | `livekit-plugins-deepgram` | Deepgram Nova-3 (API, ~300ms) |
| **LLM** | `livekit-plugins-openai` | GPT-4o-mini (API, cheap) |
| **LLM** | Ollama via OpenAI-compatible API | Llama 3.1 8B (local, free) |
| **TTS** | `livekit-plugins-cartesia` | Sonic 2 (API, ~200ms, best quality) |
| **TTS** | `livekit-plugins-elevenlabs` | ElevenLabs (API, ~300ms, voice cloning) |
| **TTS** | Edge TTS via custom plugin | Free, Indian voices |

**Plugin architecture:** Every plugin follows the same interface. Switching providers = changing one import.

---

## 3. Backend API (Non-Agent)

For admin, health checks, config:

| Choice | Why |
|--------|-----|
| **FastAPI** | Async-first, auto OpenAPI docs, Pydantic v2, industry standard |

Not used for the real-time conversation (LiveKit handles that), only for:
- `GET /health` — service status
- `POST /ingest` — trigger RAG document re-indexing
- `GET /metrics` — Prometheus metrics
- Admin auth endpoints

---

## 4. Speech-to-Text (STT)

### Default: Deepgram Nova-3 (via LiveKit plugin)

| Aspect | Detail |
|--------|--------|
| **Why this** | Best latency (300ms), best WER (97%), handles Hindi/Hinglish natively |
| **Cost** | $0.0043/min (very cheap) |
| **Alternative** | Whisper large-v3 via `livekit-plugins-whisper` — free, local, ~1-2s latency |

### Voice Activity Detection: Silero VAD

| Aspect | Detail |
|--------|--------|
| **What** | < 1ms per 30ms chunk on CPU. 0.5% false positive rate. |
| **Integration** | Built into LiveKit Agents via `livekit-plugins-silero` |

### Audio Capture
- **Browser:** WebRTC via LiveKit SDK (`getUserMedia` → LiveKit track)
- **Format:** 16kHz, 16-bit PCM mono (automatic via LiveKit)

---

## 5. Text-to-Speech (TTS)

### Default: Cartesia Sonic 2 (via LiveKit plugin)

| Aspect | Detail |
|--------|--------|
| **Why this** | 200ms to first chunk. Indian English voices. Natural prosody. |
| **Cost** | $0.03/min |
| **Alternative** | Edge TTS — free, Indian voices, internet-dependent |
| **Alternative 2** | ElevenLabs — best quality, voice cloning, $5/mo+ |

### Fallback Chain
Cartesia → Edge TTS → ElevenLabs

---

## 6. Large Language Model

### Primary: GPT-4o-mini (via LiveKit plugin)

| Aspect | Detail |
|--------|--------|
| **Why this** | $0.15/1M input tokens. Fast. Strong reasoning. |
| **Local alt** | Llama 3.1 8B via Ollama (OpenAI-compatible API) — free, ~4.7GB RAM |

### Strategy
```python
# Config-driven: swap providers without code changes
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")

if LLM_PROVIDER == "openai":
    llm = openai.LLM(model="gpt-4o-mini")
elif LLM_PROVIDER == "ollama":
    llm = openai.LLM(  # OpenAI-compatible wrapper
        base_url="http://ollama:11434/v1",
        model="llama3.1:8b-instruct-q4_K_M",
    )
```

**Never:** GPT-4 or Claude as primary (too expensive). Keep for fallback only.

---

## 7. Embeddings

| Model | Why | Details |
|-------|-----|---------|
| **BAAI/bge-small-en-v1.5** | Best size/quality tradeoff | 384 dim, 33MB, MTEB 59.3 |
| **BAAI/bge-reranker-v2-m3** | Cross-encoder reranker | ~500ms, boosts precision@5 significantly |

---

## 8. Vector Database

| Choice | Why |
|--------|-----|
| **Qdrant** | Native sparse vectors (hybrid search), filtering, quantization. Best open-source vector DB. |

**Not:** ChromaDB (unstable at scale), Pinecone (proprietary, expensive), FAISS (not a database).

---

## 9. Computer Vision

### Face Detection & Mesh
| Model | FPS | Why |
|-------|:---:|-----|
| MediaPipe Face Detection | 200 | BlazeFace, ultra-fast CPU |
| MediaPipe Face Mesh | 100 | 468 landmarks, iris tracking |

### Emotion Recognition
| Choice | Why | Alternatives Rejected |
|--------|-----|----------------------|
| **EmotiEffLib** | 1-2ms inference, 63% AffectNet accuracy, Apache 2.0 | DeepFace (200-500ms, too slow for real-time), FER (less accurate) |

### Gaze & Gesture
| Choice | Why |
|--------|-----|
| **MediaPipe iris landmarks** (geometric) | No ML needed, <5ms, reliable |
| **SolvePnP** (head pose) | Built into OpenCV, <3ms, detects nod/shake |

---

## 10. Memory & Cache

| Layer | Choice | Why |
|-------|--------|-----|
| **Short-term** | LiveKit AgentSession (in-prompt) | Last 10 turns auto-included |
| **Long-term** | Mem0 | Auto-summarization, entity extraction, importance scoring |
| **Session audit** | PostgreSQL | Immutable logs, compliance-ready |
| **TTS Cache** | Redis | Sub-millisecond reads, built-in TTL, perfect for caching repeated questions |
| **Rate limiting** | Redis | `INCR` + `EXPIRE` atomic, far better than PostgreSQL for this |
| **Pub/sub** | Redis | Required by LiveKit for multi-agent coordination |

---

## 11. RAG & LLM Orchestration

| Choice | Why |
|--------|-----|
| **LangChain** | RAG pipelines, chunking, document loaders, LangSmith tracing |
| **Direct function calls** | For tools — cleaner than LangChain agents when LiveKit handles the loop |

**Note:** LangChain is only for the RAG ingestion/retrieval pipeline. The agent loop itself runs in LiveKit Agents — we don't need LangChain agents or LangGraph for the conversation flow.

---

## 12. Frontend

| Layer | Choice | Why |
|-------|--------|-----|
| **Framework** | React 18 + TypeScript | Universal, LiveKit React SDK |
| **Build** | Vite | 10x faster than Webpack |
| **LiveKit SDK** | `@livekit/components-react` | Room connection, video tracks, participant state — 10 lines of code |
| **Styling** | TailwindCSS + shadcn/ui | Zero runtime, accessible components |

```tsx
// Full frontend for the agent:
function AdvisorRoom() {
  return (
    <RoomConnect serverUrl={LIVEKIT_URL} token={token}>
      <div className="h-screen bg-background">
        <CameraPreview />
        <TranscriptOverlay />
        <EmotionIndicator />
      </div>
    </RoomConnect>
  );
}
```

---

## 13. Infrastructure & DevOps

| Layer | Choice | Why |
|-------|--------|-----|
| **Container** | Docker + Compose | Reproducible, dev → prod parity |
| **CI/CD** | GitHub Actions | Free for public repos |
| **Monitoring** | Prometheus + Grafana | Industry standard, LiveKit exports metrics |
| **Logging** | structlog | Structured JSON, request IDs |
| **Secrets** | Environment variables | Simple, sufficient |

---

## 14. Testing

| Type | Tools |
|------|-------|
| **Unit** | pytest + pytest-asyncio |
| **Coverage** | pytest-cov (> 80%) |
| **Lint** | Ruff (replaces flake8 + isort + pyupgrade) |
| **Types** | mypy (strict mode) |
| **Load** | locust (50 concurrent sessions) |
| **E2E** | Playwright (frontend) |

---

## 15. Summary Decision Matrix

| Requirement | Chosen Solution | Open Source? | Local? | Production Ready? |
|-------------|----------------|:---:|:---:|:---:|
| Runtime | Python 3.12 | ✅ | ✅ | ✅ |
| **Agent Framework** | **LiveKit Agents** | ✅ | ✅ | ✅ |
| WebRTC Server | LiveKit Server | ✅ | ✅ | ✅ |
| STT | Deepgram Nova-3 / Whisper (LiveKit plugin) | ✅ (Whisper) | ✅ (Whisper) | ✅ |
| VAD | Silero (LiveKit plugin) | ✅ | ✅ | ✅ |
| TTS | Cartesia Sonic / Edge TTS (LiveKit plugin) | ✅ (Edge) | ❌ | ✅ |
| LLM | GPT-4o-mini / Llama 3.1 8B (LiveKit plugin) | ✅ (Llama) | ✅ (Llama) | ✅ |
| Embeddings | BGE-small-en-v1.5 | ✅ | ✅ | ✅ |
| Vector DB | Qdrant | ✅ | ✅ | ✅ |
| Face Tracking | MediaPipe | ✅ | ✅ | ✅ |
| Emotion | EmotiEffLib | ✅ | ✅ | ⚠️ Moderate |
| RAG | LangChain | ✅ | ✅ | ✅ |
| Memory | Mem0 + PostgreSQL | ✅ | ✅ | ✅ |
| Frontend | React + LiveKit SDK + Tailwind | ✅ | ✅ | ✅ |
| Monitoring | Prometheus + Grafana | ✅ | ✅ | ✅ |

### Changed Since Original Tech Stack

| Change | Was | Now | Why |
|--------|-----|-----|-----|
| **Audio pipeline** | Custom WebSocket + VAD + STT + TTS services | LiveKit Agents with plugins | 4-6 weeks saved, battle-tested WebRTC |
| **Emotion model** | DeepFace | EmotiEffLib | 100x faster (2ms vs 500ms per frame) |
| **Frontend transport** | Raw WebSocket | LiveKit React SDK | Zero WebRTC code, built-in room management |
| **Conversation loop** | Custom state machine | LiveKit AgentSession | Barge-in, interruptions, session lifecycle built-in |
| **Scaling** | Manual | LiveKit AgentServer dispatch | Built-in job scheduling + load balancing |

### Key ⚠️ Notes

| Warning | Reason |
|---------|--------|
| **Emotion accuracy is ~65%** | FER in real-world video is unreliable. Use as soft signal only. |
| **Local Whisper adds ~1-2s** | Use Deepgram API if latency matters. Reserve Whisper for dev/offline. |
| **Local Llama quality < GPT-4o-mini** | Llama 3.1 8B can hallucinate on finance. RAG helps but doesn't eliminate. Always add disclaimers. |
| **Cartesia/Deepgram are API-based** | Not fully offline. Budget ~$5-20/month for API costs at moderate usage. |
