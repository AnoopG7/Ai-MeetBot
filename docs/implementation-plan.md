# Implementation Plan — Personal Finance Advisor AI Agent

> **Approach:** Production-grade from Phase 1. Built on **LiveKit Agents** for real-time audio/WebRTC infrastructure. Every phase ships with tests, logging, error handling, observability.

---

## Phase 1 — Foundation & LiveKit Setup

**Goal:** Monorepo with Docker Compose running LiveKit Server + Qdrant + Redis + PostgreSQL. Agent scaffold registers and connects.

### Tasks

**1.1 Repository Structure**
```
finance-advisor/
├── backend/
│   ├── src/
│   │   └── advisor/
│   │       ├── agent/          # LiveKit Agent (entrypoint, tools, prompts)
│   │       ├── rag/            # RAG pipeline, ingestion, retrieval
│   │       ├── vision/         # CV pipeline (face, emotion, gaze)
│   │       ├── memory/         # Mem0 + PostgreSQL storage
│   │       ├── api/            # FastAPI (health, config, admin)
│   │       └── core/           # Config, logging, exceptions
│   ├── tests/
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── .env.example
├── frontend/
│   ├── src/
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── Makefile
├── .github/workflows/
├── .gitignore
└── docs/
```

**1.2 Core Dependencies**
```toml
# pyproject.toml
dependencies = [
    "livekit-agents>=1.5",
    "livekit-plugins-silero",
    "livekit-plugins-deepgram",   # or livekit-plugins-whisper
    "livekit-plugins-openai",     # or livekit-plugins-ollama
    "livekit-plugins-cartesia",   # or livekit-plugins-edge-tts
    "fastapi>=0.115",
    "structlog>=24",
    "qdrant-client>=1.12",
    "sentence-transformers>=3",
    "mem0>=0.1",
    "pydantic-settings>=2",
]
```

**1.3 Docker Compose Services (Dev)**
```yaml
services:
  livekit-server:
    image: livekit/livekit-server:latest
    command: --config /etc/livekit.yaml
    ports: ["7880:7880", "7881:7881"]

  qdrant:
    image: qdrant/qdrant:latest
    ports: ["6333:6333"]
    volumes: ["qdrant_data:/qdrant/storage"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  postgres:
    image: postgres:16-alpine
    ports: ["5432:5432"]
    environment:
      POSTGRES_DB: advisor
    volumes: ["pg_data:/var/lib/postgresql/data"]

  agent:
    build: ./backend
    command: python -m advisor.agent.main
    environment:
      LIVEKIT_URL: ws://livekit-server:7880
      LIVEKIT_API_KEY: devkey
      LIVEKIT_API_SECRET: secret
      REDIS_URL: redis://redis:6379
    depends_on: [livekit-server, qdrant, redis, postgres]
    volumes:
      - ./backend/src:/app/src
```

**1.4 Agent Scaffold (connects but does nothing yet)**
```python
# advisor/agent/main.py
from livekit.agents import AgentServer

server = AgentServer()

@server.on("connect")
async def on_connect(ctx):
    # Phase 2-5 will fill this in
    await ctx.wait_for_close()

if __name__ == "__main__":
    server.run()
```

**1.5 Frontend Scaffold**
- React 18 + TypeScript + Vite
- LiveKit RoomConnect for WebRTC (replaces raw WebSocket)
- shadcn/ui for components
- TailwindCSS

```tsx
// App.tsx — ~20 lines to connect to LiveKit room
import { RoomConnect } from "@livekit/components-react";

function App() {
  return (
    <RoomConnect
      serverUrl={import.meta.env.VITE_LIVEKIT_URL}
      token={token}
    >
      {/* Agent handles everything else */}
    </RoomConnect>
  );
}
```

### Deliverables
- [ ] `docker compose up` starts all 5 services
- [ ] Agent connects to LiveKit Server (check logs)
- [ ] Frontend connects to LiveKit room
- [ ] `make lint && make test` passes
- [ ] CI green on PR

---

## Phase 2 — Text-to-Speech (Configure via LiveKit)

**Goal:** Agent speaks. Zero custom TTS code — just a LiveKit plugin config change.

### Tasks

**2.1 Choose TTS Provider**
| Provider | Quality | Latency | Cost | Local? |
|----------|:-------:|:-------:|:----:|:------:|
| Edge TTS (plugin) | 8/10 | ~500ms | Free | No (hits MS servers) |
| Cartesia Sonic | 9/10 | ~200ms | $0.03/min | No |
| ElevenLabs | 9.5/10 | ~300ms | $5/mo+ | No |
| Pipper | 6/10 | ~50ms | Free | Yes (CPU) |

**2.2 Wire TTS Plugin**
```python
# Adding TTS = ONE config change
session = AgentSession(
    tts=cartesia.TTS(
        model="sonic-2-english",
        voice="6f6a6c6c-6b6a-4e6f-8e6a-6c6c6b6a4e6f",  # Indian English voice
    ),
    # ... rest of config
)
```

**2.3 Voice Configuration**
- English (India) — default
- Hindi — secondary (upcoming)
- Hinglish — fallback
- Speed control: 1.0x default, 0.85x for elderly users
- SSML for emphasis: slower on disclaimers, faster on greetings

**2.4 Testing**
- `curl` the token endpoint, open frontend, hear agent speak a test phrase
- Latency < 500ms first chunk
- Fallback: if Cartesia fails → Edge TTS

### Deliverables
- [ ] Agent speaks when user joins the room
- [ ] Voice is Indian English
- [ ] Disclaimers are spoken clearly (slower speed)
- [ ] TTS failure → auto fallback

---

## Phase 3 — Speech-to-Text (Configure via LiveKit)

**Goal:** Agent hears and understands. Zero custom STT code — LiveKit plugin.

### Tasks

**3.1 Choose STT Provider**
| Provider | Model | Accuracy | Latency | Local? |
|----------|-------|:--------:|:-------:|:------:|
| Whisper (livekit-plugins-whisper) | large-v3 | 95% | ~1-2s | Yes (MPS) |
| Deepgram (livekit-plugins-deepgram) | Nova-3 | 97% | ~300ms | No |
| AssemblyAI | Best | 96% | ~500ms | No |

**3.2 Wire STT Plugin**
```python
session = AgentSession(
    stt=deepgram.STT(model="nova-3"),  # or whisper.STT(model="large-v3")
    # ...
)
```

**3.3 VAD (Voice Activity Detection)**
Already included — Silero VAD via LiveKit:
```python
session = AgentSession(
    vad=silero.VAD(
        threshold=0.5,
        min_speech_duration_ms=500,
        min_silence_duration_ms=600,
    ),
)
```

**3.4 Language Support**
- English (auto-detect)
- Hindi (auto-detect)
- Hinglish — Whisper handles code-switching naturally
- Hotword boosting: SIP, PPF, NPS, ELSS, CIBIL, KYC

### Deliverables
- [ ] Speak → agent transcribes correctly
- [ ] VAD segments speech without clipping
- [ ] Hinglish sentences transcribe correctly
- [ ] Finance terms (SIP, PPF) recognized reliably

---

## Phase 4 — Finance RAG Pipeline

**Goal:** The brain. Knowledge ingestion, vector search, hybrid retrieval, and LLM integration.

### Tasks

**4.1 Knowledge Ingestion**
- Scrape RBI/SEBI/IRDAI/PFRDA PDFs → `data/knowledge/`
- PyMuPDF for PDF extraction
- Chunk: 500 chars, 50 overlap (RecursiveCharacterTextSplitter)
- Embed: BAAI/bge-small-en-v1.5 (384d)
- Store in Qdrant with metadata (source, section, year, product)

**4.2 Qdrant Collection Schema**
```python
{
    "collection": "finance_knowledge",
    "vectors": {"size": 384, "distance": "Cosine"},
    "sparse_vectors": {"bm25": {}},  # For hybrid search
    "payload_schema": {
        "source": "keyword",
        "section": "keyword",
        "year": "integer",
        "regulator": "keyword",
        "product_type": "keyword",
    }
}
```

**4.3 Hybrid Search**
```python
# Dense + Sparse fusion
results = client.search_batch([
    SearchRequest(
        vector=query_embedding,           # Dense
        limit=20,
    ),
    SearchRequest(
        vector=sparse_embedding,          # Sparse (BM25)
        limit=20,
    ),
])
reranked = cross_encoder(query, merge(results))
```

**4.4 Document Types to Ingest**
| Regulator | Docs |
|-----------|------|
| RBI | Master Circulars (Savings, FD, KYC, UPI, NRI), Interest rate notifications |
| SEBI | Mutual fund regulations, Investment advisor rules, Disclosure norms |
| IRDAI | Insurance product guidelines, Claim settlement rules |
| Income Tax | 80C, 80D, 80TTA, Capital gains, TDS rules |
| PFRDA | NPS guidelines, Withdrawal rules |
| Bank Products | Savings, FD, RD, Credit Card, Home Loan, Personal Loan terms |
| Investopedia | Educational finance articles (benchmarking) |

**4.5 LLM Integration**
```python
session = AgentSession(
    llm=openai.LLM(model="gpt-4o-mini"),  # Or Ollama for local
    # ...
)

agent = Agent(
    instructions=PERSONAL_FINANCE_PROMPT,
    tools=[lookup_finance_knowledge, calculate_emi, ...],
)
```

**4.6 Prompt Engineering**
- System prompt defines finance advisor persona (see agent-plan.md)
- RAG results injected as context before user query
- Compliance footer appended to every response
- Use case detection: first query routes to banking/loan/insurance/etc prompt

### Deliverables
- [ ] Ingestion pipeline processes 50+ finance docs
- [ ] `lookup_finance_knowledge("PPF rate")` returns relevant chunks
- [ ] LLM answers with citations
- [ ] Hybrid search beats pure vector search (measure precision@5)

---

## Phase 5 — Agent & Conversation Loop

**Goal:** Full voice conversation with finance knowledge, tools, memory, and compliance.

### Tasks

**5.1 Agent Implementation**
```python
# advisor/agent/main.py — complete agent
@server.on("connect")
async def on_connect(ctx):
    session = AgentSession(
        vad=silero.VAD(),
        stt=deepgram.STT(model="nova-3"),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=cartesia.TTS(model="sonic-2-english", voice="indian"),
    )

    agent = Agent(
        instructions=PROMPTS["personal_finance"],
        tools=[
            lookup_finance_knowledge,
            calculate_emi,
            get_product_info,
            assess_risk_profile,
            escalate_to_human,
        ],
    )

    await session.start(agent=agent, room=ctx.room)
    await ctx.wait_for_close()
```

**5.2 Memory Integration**
```python
# Before each LLM call, load user memory
@session.on("before_llm")
async def on_before_llm(ctx):
    profile = await mem0.get(f"profile:{ctx.session.user_id}")
    ctx.system_prompt += f"""
User profile:
- Risk profile: {profile.risk_profile}
- Goals: {profile.goals}
- Mentioned products: {profile.mentioned_products}
"""

# After each turn, save to memory
@session.on("after_llm")
async def on_after_llm(ctx):
    await mem0.remember(ctx.session.user_id, {
        "query": ctx.user_message,
        "response": ctx.llm_response,
        "emotion": vision_context.emotion,
        "timestamp": time.now(),
    })
```

**5.3 Compliance Layer**
```python
@session.on("before_tts")
async def on_before_tts(ctx):
    response = ctx.llm_response

    # Check: no stock tips, no guarantees
    if compliance.has_violation(response):
        ctx.llm_response = compliance.sanitize(response)

    # Ensure disclaimer present
    if "SEBI-registered" not in response:
        ctx.llm_response += DISCLAIMER
```

**5.4 Use Case Detection**
```python
# On first user message, detect use case
@session.on("first_user_message")
async def on_first_message(ctx):
    use_case = classifier.predict(ctx.user_message)
    ctx.agent.instructions = PROMPTS[use_case]
```

**5.5 Human Escalation**
```python
@agent_tool
async def escalate_to_human(ctx, reason: str):
    """Transfer to human advisor."""
    ticket = create_ticket(ctx.session, reason)
    ctx.session.say("Connecting you to a human advisor...")
    await ctx.session.transfer_to_human(ticket.id)
```

**5.6 Session Audit Logging**
- Every turn logged to PostgreSQL: `(user_id, session_id, query, response, emotion, latency_ms)`
- Used for compliance audits and quality monitoring

### Deliverables
- [ ] End-to-end conversation: speak → hear response
- [ ] Barge-in works (interrupt mid-response)
- [ ] Memory persists across sessions
- [ ] Compliance blocks banned responses
- [ ] Audit logs in PostgreSQL
- [ ] Human escalation works

---

## Phase 6 — Camera & Video Pipeline

**Goal:** Webcam streams via LiveKit video tracks. Face detection with MediaPipe.

### Tasks

**6.1 Frontend: Webcam via LiveKit**
```tsx
// LiveKit handles WebRTC video track automatically
import { useLocalParticipant } from "@livekit/components-react";

function VideoRoom() {
  const { cameraTrack } = useLocalParticipant();

  return (
    <div>
      <video ref={cameraTrack} />
    </div>
  );
}
```

No custom WebSocket or frame capture code. LiveKit video tracks handle everything.

**6.2 Backend: Video Track Processing**
```python
# LiveKit delivers video frames to the agent
@session.on("video_track")
async def on_video_frame(ctx, frame: VideoFrame):
    """Process each frame from the user's webcam."""
    await vision_pipeline.process_frame(frame)
```

**6.3 Face Detection**
```python
class VisionPipeline:
    def __init__(self):
        self.face_detection = mp.solutions.face_detection.FaceDetection(
            model_selection=1,  # distance model
            min_detection_confidence=0.5,
        )

    async def process_frame(self, frame: VideoFrame):
        rgb = frame.to_rgb()
        results = self.face_detection.process(rgb)
        if not results.detections:
            return None

        # Track face presence, bounding box
        self.face_present = True
        self.bbox = results.detections[0].bounding_box
```

**6.4 Privacy**
- Frames processed in memory, never written to disk
- No recording without explicit consent
- User sees camera preview (transparency)
- Device selection: front camera for self-view

### Deliverables
- [ ] Webcam streams to LiveKit room
- [ ] Backend receives video frames
- [ ] Face detection works (bounding box)
- [ ] Privacy: no frames persisted

---

## Phase 7 — CV & Emotion Analysis

**Goal:** Full multimodal understanding — emotion, gaze, head pose, gestures. Feed into LLM.

### Tasks

**7.1 Face Mesh**
```python
self.face_mesh = mp.solutions.face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,  # iris tracking enabled
)
```

**7.2 Emotion Recognition (EmotiEffLib)**
```python
self.emotion = EmotiEffLib()  # 1-2ms, vs DeepFace 200-500ms

async def process_frame(self, frame):
    if frame.timestamp % 15 != 0:
        return  # Every 15th frame only

    emotion = self.emotion.predict(frame.to_rgb())
    self.ctx.emotion = emotion.label
    self.ctx.emotion_confidence = emotion.confidence

    # Smooth over sliding window
    self.emotion_history.append(emotion)
    if len(self.emotion_history) > 5:
        self.emotion_history.pop(0)
```

**7.3 Gaze Estimation**
```python
def estimate_gaze(landmarks) -> str:
    # Iris landmarks 468-473
    left_iris = landmarks[468]
    right_iris = landmarks[473]

    # Compare iris to eye corners
    if both_eyes_centered(left_iris, right_iris, landmarks):
        return "looking_at_camera"
    elif both_eyes_left(left_iris, right_iris):
        return "looking_away"
    else:
        return "looking_down"
```

**7.4 Head Pose (Nod/Shake)**
```python
def detect_head_gesture(pose_history: deque) -> str:
    if len(pose_history) < 10:
        return "still"

    yaws = [p.yaw for p in pose_history]
    pitches = [p.pitch for p in pose_history]

    if max(pitches) - min(pitches) > 0.3:  # rapid up-down
        return "nodding"
    elif max(yaws) - min(yaws) > 0.3:      # rapid left-right
        return "shaking"
    else:
        return "still"
```

**7.5 Multimodal Fusion into LLM**
```python
@session.on("before_llm")
async def inject_vision_context(ctx):
    vision = vision_pipeline.current_context

    ctx.system_prompt += f"""
## Live User Context
- Emotion: {vision.emotion} ({vision.emotion_confidence:.0%})
- Gaze: {vision.gaze}
- Gesture: {vision.head_gesture}
- Engagement: {vision.engagement_score:.0%}

Adjust your response accordingly:
- If confused: simplify, offer alternative explanation
- If frustrated: acknowledge, stay patient
- If looking away > 5s: they may be checking documents, wait
- If nodding: they agree, continue
- If shaking head: they disagree, re-explain
"""
```

**7.6 Performance Budget**
| Operation | Frequency | Budget | Model |
|-----------|-----------|--------|-------|
| Face detection | Every frame | < 5ms | MediaPipe |
| Face mesh | Every frame | < 10ms | MediaPipe |
| Emotion | Every 15 frames (2Hz) | < 50ms | EmotiEffLib |
| Gaze | Every 5 frames (6Hz) | < 5ms | Geometric |
| Head pose | Every 3 frames (10Hz) | < 3ms | SolvePnP |

**7.7 Privacy**
- No raw frames stored or logged
- Only feature vectors persisted: `(emotion, confidence, gaze, gesture, timestamp)`
- User consent dialog before camera access

### Deliverables
- [ ] 7 emotions detected with smoothing
- [ ] Gaze tracking: looking at camera vs away
- [ ] Nod/shake detection
- [ ] Vision context injected into LLM prompts
- [ ] Vision pipeline < 50ms per frame
- [ ] No raw frames persisted

---

## Phase 8 — Production Hardening

**Goal:** Ship-ready. Observability, scaling, security, compliance, documentation.

### Tasks

**8.1 Monitoring**
- Prometheus metrics from LiveKit Agent and our services
- Grafana dashboards:
  - Turn latency (VAD → STT → LLM → TTS): p50/p95/p99
  - Tool call frequency (which tools, how often)
  - Emotion distribution over sessions
  - RAG retrieval precision@5
  - Active sessions, concurrent agents
- Alerts: latency > 5s p99, error rate > 5%, model not loaded

**8.2 Performance Tuning**
```python
# Profile bottlenecks
# - LLM speculative decoding for faster first token
# - Whisper int8 quantization for faster STT
# - Vision frame skipping when GPU > 80%
# - RAG caching for frequent queries
```

**8.3 Scaling**
```yaml
# docker-compose.prod.yml
services:
  agent:
    deploy:
      replicas: 3  # Multiple agent instances
    environment:
      LIVEKIT_URL: wss://livekit.example.com
```

**8.4 Security**
- JWT token authentication for room access
- API rate limiting per token
- Input sanitization (prompt injection protection)
- Secrets via environment variables (not in code)
- CORS for frontend origin only

**8.5 Security Audit**
| Check | Tool |
|-------|------|
| Docker vuln scan | Trivy |
| Deps check | `pip audit` |
| Secret scanning | GitLeaks |
| SAST | Ruff + mypy (strict) |

**8.6 Compliance Finalization**
- Consent dialog for camera + audio recording
- Data retention policy: session logs deleted after 90 days
- DPDP Act compliance: user data export/delete on request
- Disclaimers on every response (audited quarterly)

**8.7 Documentation**
- API reference (OpenAPI)
- Architecture diagram (updated)
- Runbook: start → debug → scale → recover
- On-call guide

### Deliverables
- [ ] Grafana dashboards for all services
- [ ] Load test: 50 concurrent sessions
- [ ] Security vulnerabilities = 0
- [ ] Docs published
- [ ] Compliance requirements met

---

## Summary Timeline

| Phase | What | Effort |
|-------|------|--------|
| 1 | Foundation + LiveKit Setup | 3-4 days |
| 2 | TTS (LiveKit plugin config) | 1 day |
| 3 | STT (LiveKit plugin config) | 1 day |
| 4 | Finance RAG Pipeline | 7-10 days |
| 5 | Agent + Conversation Loop | 4-5 days |
| 6 | Camera + Video Pipeline | 3-4 days |
| 7 | CV & Emotion Analysis | 7-10 days |
| 8 | Production Hardening | 5-7 days |
| **Total** | | **~5-7 weeks** |

**Saved vs original plan:** ~2 weeks saved because Phase 2 (TTS), Phase 3 (STT), and half of Phase 5 (conversation loop) went from custom-build to configuration-only.
