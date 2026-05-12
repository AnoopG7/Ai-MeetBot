# Implementation Plan — Personal Finance Advisor AI Agent

> **Approach:** Production-grade from Phase 1. No MVPs, no throwaway prototypes. Every phase ships with tests, logging, error handling, observability, and deployment-ready infrastructure.

---

## Phase 1 — Foundation & Project Setup

**Goal:** A production-grade monorepo with CI/CD, containerization, config management, and shared abstractions. Nothing runs yet, but everything is ready to receive features.

### Tasks

**1.1 Repository Structure**
```
finance-advisor/
├── backend/
│   ├── src/
│   │   ├── advisor/           # Main package
│   │   │   ├── api/           # FastAPI routes
│   │   │   ├── core/          # Config, logging, exceptions
│   │   │   ├── audio/         # TTS, STT, VAD
│   │   │   ├── llm/           # LLM, RAG, prompts
│   │   │   ├── vision/        # Camera, face, emotion
│   │   │   └── models/        # Pydantic schemas
│   │   └── main.py
│   ├── tests/
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── .env.example
├── frontend/
│   ├── src/
│   ├── Dockerfile
│   ├── package.json
│   └── tsconfig.json
├── docker-compose.yml
├── Makefile
├── .github/workflows/
├── .gitignore
├── implementation-plan.md
└── tech-stack.md
```

**1.2 Backend Scaffolding**
- Python 3.12+, `pyproject.toml` with all dependency groups (dev, test, prod)
- FastAPI application factory pattern
- Pydantic v2 settings (`BaseSettings` from env vars)
- Structured logging via `structlog` (JSON output, request IDs)
- Global exception handlers (HTTP + internal)
- Health check endpoint (`GET /health`)
- Makefile targets: `install`, `test`, `lint`, `typecheck`, `run`, `docker-build`
- Ruff + mypy + pre-commit hooks

**1.3 Frontend Scaffolding**
- React 18 + TypeScript + Vite
- TailwindCSS + shadcn/ui for components
- WebSocket client utility
- API client (axios/fetch wrapper)
- Auth placeholder (JWT)
- Docker multi-stage build

**1.4 Infrastructure**
- Docker Compose: backend, frontend, Qdrant (vector DB), Redis (cache/queue)
- GitHub Actions: lint → test → build on PR, deploy on main
- `.env.example` with all required vars documented
- Docker health checks + restart policies

**1.5 Shared Foundation**
- `BaseService` abstract class with lifecycle hooks
- Unified error types (domain-specific exceptions)
- Async-first everywhere (`asyncio`, `asyncpg`, `httpx`)
- Telemetry stubs (OpenTelemetry ready, Prometheus metrics endpoint)

### Deliverables
- [ ] Monorepo with all scaffolding
- [ ] `make install && make test && make lint` passes
- [ ] `docker compose up` starts backend + frontend + infra
- [ ] `GET /health` returns `{"status": "ok"}`
- [ ] Frontend renders blank page with routing
- [ ] CI green on PR

---

## Phase 2 — Text-to-Speech (TTS)

**Goal:** A production-grade TTS service that converts text to speech with low latency, multiple voice options, caching, and streaming. This is the first real feature — simpler than STT, good to validate the audio pipeline.

### Tasks

**2.1 TTS Engine Abstraction**
```
TTSProvider (interface)
├── EdgeTTSProvider     # Free, 100+ voices, internet needed
├── CoquiTTSProvider    # Local, voice cloning, XTTSv2
└── ElevenLabsProvider  # Paid, best quality, streaming
```
- Strategy pattern: primary + fallback providers
- Auto-fallback on failure (e.g., EdgeTTS → Coqui → ElevenLabs)
- Voice configuration per use case (soothing for elderly, professional for wealth mgmt)

**2.2 Edge TTS Integration**
- `edge-tts` Python library
- Supported voices: English (US/UK/IN), Hindi, Hinglish
- SSML support for prosody (speed, pitch control)
- Audio format: 16-bit PCM WAV (interchange format), convert to MP3/Opus for streaming

**2.3 Streaming TTS API**
- `POST /tts` — request text + voice config → returns audio file
- `GET /tts/stream` — WebSocket or SSE for chunked playback
  - Client sends `{"text": "...", "voice": "..."}`
  - Server streams audio chunks as they're generated
  - First audio chunk in < 500ms
- `GET /tts/voices` — list available voices

**2.4 Caching**
- Redis cache: `sha256(text + voice)` → audio bytes
- TTL: 24h for common responses, 0h for dynamic content
- Cache hit rate monitoring (prometheus metric)

**2.5 Production Concerns**
- Audio normalization (volume leveling)
- Rate limiting (100 req/min per user)
- Request validation (max 2000 chars, profanity filter)
- Metrics: TTS latency (p50/p95/p99), cache hit rate, error rate
- Logging: every TTS request logged with duration, cache status

**2.6 Testing**
- Unit: each provider with mocked HTTP
- Integration: Edge TTS actually generates audio
- Property: audio output is valid WAV/MP3
- Load: 50 concurrent requests

### Deliverables
- [ ] `curl localhost:8000/tts -d '{"text":"Hello"}'` returns audio file
- [ ] WebSocket streaming works (< 500ms to first chunk)
- [ ] Fallback provider kicks in if primary fails
- [ ] Redis cache avoids repeated API calls
- [ ] All metrics exposed on `/metrics`

---

## Phase 3 — Speech-to-Text (STT)

**Goal:** Real-time speech transcription with voice activity detection, language detection, and confidence scoring. The agent can now hear and understand.

### Tasks

**3.1 Voice Activity Detection (VAD)**
- Silero VAD model (PyTorch, runs on CPU/MPS)
- Process microphone audio in 30ms chunks
- State machine: SILENCE → SPEAKING → SILENCE
  - `min_speech_duration_ms`: 500ms (ignore clicks/coughs)
  - `min_silence_duration_ms`: 600ms (end of utterance)
  - `threshold`: 0.5 (sensitivity)
- Echo cancellation preprocessing via WebRTC AEC

**3.2 Audio Capture**
- PyAudio for local microphone
- WebSocket-based streaming from frontend browser
- Sample rate: 16kHz (Whisper native format)
- Format: 16-bit PCM mono
- Ring buffer for real-time processing without drops

**3.3 Whisper STT Service**
- `faster-whisper` with large-v3 model
- Quantization: `int8_float16` on MPS (Apple Silicon)
- Two modes:
  - **Realtime:** Process when VAD detects speech end (higher latency, perfect)
  - **Streaming:** Process every 2s of audio (lower latency, slightly worse)
- Language detection per utterance (auto-detect English/Hindi/Hinglish)
- Confidence threshold: discard transcriptions below 0.6 confidence
- Hotword/phrase boosting for finance terms (SIP, PPF, NPS, ELSS, CIBIL)

**3.4 STT API**
- `WS /stt/stream` — WebSocket: client streams raw audio, server returns transcripts
  ```
  Client → Server: [binary audio chunk, 16kHz PCM]
  Server → Client: {"text": "I want to invest in mutual funds", "confidence": 0.92, "is_final": true, "language": "en"}
  ```
- `POST /stt/transcribe` — one-shot file transcription (for recorded meetings)
- `GET /stt/status` — model loaded status, language, uptime

**3.5 Production Concerns**
- Background noise reduction via `noisereduce` library
- Silence trimming before sending to Whisper (speed up, reduce cost)
- Transcription timeout (if user talks > 30s, force finalize)
- Metrics: STT latency, word error rate, VAD false positive rate
- Graceful model reload (handle OOM)

**3.6 Testing**
- Unit: VAD state machine transitions
- Integration: pre-recorded audio files with known transcripts
- Performance: measure real-time factor (< 0.5x real-time on M-series)
- Accuracy: WER on finance-specific test set

### Deliverables
- [ ] WebSocket STT: speak → transcribed text appears in < 2s
- [ ] VAD correctly segments speech from silence
- [ ] Works with Hindi, Hinglish, English
- [ ] Confidence < 0.6 transcripts are discarded
- [ ] `/metrics` shows STT latency histogram

---

## Phase 4 — LLM Orchestration & RAG

**Goal:** The agent's brain. A finance-knowledgeable LLM that answers accurately using a RAG pipeline with retrieved documents, conversation context, and compliance guardrails.

### Tasks

**4.1 LLM Abstraction**
```
LLMProvider (interface)
├── OllamaProvider      # Local Llama 3.1 8B, free
├── OpenAIMockProver    # GPT-4o-mini, API-based
└── MockProvider        # For testing
```
- Provider selection via config (local dev → Ollama, prod → API)
- Structured output via `instructor` library (typed JSON responses)
- Token tracking per request (cost monitoring)
- Retry with exponential backoff

**4.2 Prompt Engineering**
- System prompt template per use case:
  - `personal_finance`: "You are a personal finance advisor..."
  - `loan_advisory`: "You are a loan specialist..."
  - `insurance`: "You are an insurance advisor..."
- Dynamic injection: conversation history, retrieved docs, emotion context
- Compliance footer appended to every response:
  ```
  [DISCLAIMER: This is for educational purposes only. 
  Consult a SEBI-registered advisor for personalized advice.]
  ```

**4.3 RAG Pipeline**
```
Document Ingestion:
  PDFs/MDs → Chunk (500t, 50t overlap) → Embed → Store in Qdrant

Retrieval:
  User Query → Embed → Hybrid Search (dense + sparse) → Rerank → Top-5 chunks

Generation:
  System Prompt + Context Chunks + History → LLM → Response with citations
```

**4.4 Data Ingestion Pipeline**
- Batch pipeline (`python -m advisor.ingest`) that:
  - Reads PDFs from `data/knowledge/`
  - Extracts text (PyMuPDF for PDFs, markdown for .md)
  - Chunks with `RecursiveCharacterTextSplitter` (500 chars, 50 overlap)
  - Generates embeddings via `BAAI/bge-small-en-v1.5` (384d)
  - Stores in Qdrant with metadata (source, section, page)
- Incremental updates (re-embed only changed files)
- Versioned snapshots for rollback

**4.5 Hybrid Search**
- Dense: embedding similarity (cosine)
- Sparse: BM25 via `Qdrant` sparse vectors
- Fusion: `alpha * dense_score + (1-alpha) * sparse_score`
- Reranking: cross-encoder (`BAAI/bge-reranker-v2-m3`) on top-20 results
- Finance-specific boost: prioritize RBI/SEBI docs over generic web content

**4.6 Conversation Memory**
- Short-term: last 10 turns in prompt context
- Long-term: Mem0 or custom vector store
  - Summarize conversations nightly
  - Extract user profile (risk tolerance, goals, products mentioned)
  - Store in Qdrant with user_id for retrieval
- Session persistence: every turn saved to PostgreSQL (audit trail)

**4.7 Compliance & Safety**
- Blocklist: cannot recommend specific stocks, cannot predict returns
- PII redaction: PAN, Aadhaar, bank account numbers masked in logs
- Audit logging: every Q&A pair stored with timestamp, user_id, emotion context
- Response validation: regex checks for guarantees/promises
- Human escalation: confidence < 0.4 → "Let me connect you to an advisor"

**4.8 API**
- `POST /chat` — query + optional context → response
  ```json
  {
    "query": "Should I invest in PPF?",
    "user_id": "u_123",
    "session_id": "s_456",
    "use_case": "personal_finance",
    "emotion": "curious"
  }
  ```
  Response:
  ```json
  {
    "response": "PPF offers 7.1% interest...",
    "citations": ["RBI Master Circular 2024 §4.2"],
    "confidence": 0.89,
    "disclaimer": true
  }
  ```
- `POST /chat/stream` — SSE streaming of token-by-token response
- `POST /ingest` — trigger document re-indexing

**4.9 Testing**
- Unit: RAG retrieval relevance, chunking correctness
- Integration: end-to-end QA on a curated 50-question finance test set
- Accuracy: manually annotated answers, track correct %, hallucination %
- Adversarial: prompt injection attempts, jailbreak attempts

### Deliverables
- [ ] `POST /chat` answers finance questions with citations
- [ ] RAG pipeline retrieves relevant docs for test queries
- [ ] Conversation memory persists across turns
- [ ] Compliance guardrails prevent banned responses
- [ ] Metrics: retrieval precision@5, response accuracy, latency

---

## Phase 5 — Conversation Loop Integration

**Goal:** Wire TTS + STT + LLM into a real-time conversational loop. The agent can now have a full voice conversation.

### Tasks

**5.1 Orchestrator Service**
- Asynchronous pipeline manager:
  ```
  Mic Audio → VAD → STT → [Fusion: text + emotion + context] → LLM + RAG → TTS → Speaker
  ```
- State machine for conversation flow:
  - `LISTENING` — VAD active, collecting audio
  - `PROCESSING` — STT + LLM running
  - `SPEAKING` — TTS playing, VAD paused (to avoid hearing itself)
  - `INTERRUPTED` — user cuts in, stop TTS, re-enter LISTENING

**5.2 Interruption Handling**
- While TTS is speaking, continue running VAD
- If user speaks with confidence > 0.7:
  - Stop current TTS playback
  - Log "User interrupted: {partial_stt}"
  - Enter LISTENING mode
- Barge-in timeout: resume from where interrupted if pause > 2s

**5.3 WebSocket Session API**
- `WS /session` — full-duplex session
  ```
  Client → Server: [binary audio chunks]
  Server → Client: {"type": "transcript", "text": "..."}
  Server → Client: {"type": "response", "text": "..."}
  Server → Client: {"type": "audio", "data": "<base64>"}
  Server → Client: {"type": "state", "state": "listening|processing|speaking"}
  Server → Client: {"type": "emotion", "emotion": "confused"}
  ```

**5.4 Session Management**
- Session lifecycle: create → active → pause → resume → end
- Rate limiting: per-session (max 100 messages/min)
- Timeout: auto-end after 5min of silence
- Persistence: full session log to PostgreSQL (audit compliance)

**5.5 Testing**
- E2E: pre-recorded conversation plays through full pipeline
- Latency budget: full turn < 3s (VAD + STT + LLM + RAG + TTS)
- Interruption: mid-TTS interruption resumes correctly
- Stress: 10 concurrent sessions

### Deliverables
- [ ] Full conversation loop works end-to-end
- [ ] Interruption handling (user can cut off the bot)
- [ ] Session persists and can be resumed
- [ ] End-to-end latency < 3s per turn

---

## Phase 6 — Camera Integration

**Goal:** Access webcam, stream frames to backend, detect faces, and establish the vision pipeline. No analysis yet — just getting frames from camera to server efficiently.

### Tasks

**6.1 Camera Access (Frontend)**
- `getUserMedia` API for webcam access
- Frame capture at configurable FPS (default: 10, max: 30)
- Canvas-based frame extraction → JPEG base64 or binary blob
- WebSocket stream: `WS /vision/stream`
  ```
  Client → Server: [binary JPEG frame, ~50KB each]
  ```
- Bandwidth optimization:
  - 10 FPS initially, adapt based on network
  - JPEG quality 70 (good enough for face detection)
  - Skip frames if WebSocket buffer is full

**6.2 Frame Processing Pipeline (Backend)**
- WebSocket receives frames → async queue → processor
- Frame rate limiting: max 10 FPS processed (drop excess)
- Resolution: 640x480 (balance speed vs accuracy)
- Frame metadata: timestamp, frame_id, resolution

**6.3 Face Detection**
- MediaPipe Face Detection (BlazeFace) — ultra-fast, works on CPU
- Returns: bounding box, 6 keypoints (eyes, ears, nose, mouth)
- Confidence > 0.5 to consider a valid face
- Track multiple faces (future: multi-party meetings)

**6.4 API**
- `WS /vision/stream` — receive frames, return detections
  ```
  Server → Client: {
    "type": "face_detection",
    "faces": [{"bbox": [x,y,w,h], "confidence": 0.95, "landmarks": [...]}],
    "frame_id": 42,
    "timestamp": 1712345678.123
  }
  ```
- `GET /vision/status` — camera connected, FPS, frame count

**6.5 Production Concerns**
- Privacy: frames processed in memory, never written to disk
- No recording without explicit consent
- `/metrics`: frames processed, FPS, face detection latency
- Backpressure: if backend can't keep up, frontend drops frames
- Graceful degradation: no camera → text-only mode

**6.6 Testing**
- Unit: frame preprocessing, face detection on sample images
- Integration: real webcam feed with known faces
- Performance: max sustainable FPS on M-series Mac

### Deliverables
- [ ] Frontend captures webcam → streams to backend
- [ ] Backend detects faces with MediaPipe
- [ ] Face bounding boxes display on frontend overlay
- [ ] Privacy: no frames persisted
- [ ] Metrics: processing FPS, face detection rate

---

## Phase 7 — Computer Vision & Emotion Analysis

**Goal:** Full multimodal understanding — facial expressions, emotions, gaze, head pose, gestures. The agent now sees and interprets the user's state.

### Tasks

**7.1 Face Mesh**
- MediaPipe Face Mesh (468 landmarks, 3D)
- Iris landmarks for gaze direction
- Model selection:
  - `max_num_faces`: 1 (single user focus)
  - `refine_landmarks`: True (enables iris tracking)
  - `min_detection_confidence`: 0.5

**7.2 Emotion Recognition**
- DeepFace with `VGG-Face` model (fastest, 7 emotions)
- Every N=15 frames (skip for performance)
- Emotion smoothing over sliding window of 5 frames
- Mapped emotions for agent responses:
  | Detected | Agent Action |
  |----------|-------------|
  | Confused | "Would you like me to explain differently?" |
  | Frustrated | "I understand this can be confusing..." |
  | Happy/Agreeing | Continue, note positive reaction |
  | Surprised | "Does that sound good to you?" |
  | Fearful/Anxious | Reassure, simplify language |
  | Sad | Empathetic tone, slower speech |
  | Angry | Apologetic, offer human escalation |

**7.3 Gaze Estimation**
- From iris landmarks: left/right/center relative to camera
- States: LOOKING_AT_CAMERA, LOOKING_AWAY, LOOKING_DOWN (reading?)
- If user looks away > 5s → "Are you still there?" or pause
- If user looks down repeatedly → checking documents, wait patiently

**7.4 Head Pose & Gestures**
- SolvePnP from face landmarks to get head rotation (yaw, pitch, roll)
- Nod detection: yaw/0.5s → "User nodded" (agreement signal)
- Head shake: pitch oscillation → "User disagreed"
- Hand gesture (future): MediaPipe Hands for "stop" or "raise hand"
- Lean tracking: face bounding box size change → leaning in/out

**7.5 Multimodal Fusion**
- Combine vision signals into a structured context:
  ```python
  class VisionContext(BaseModel):
      emotion: str  # "confused" | "happy" | "neutral" | ...
      emotion_confidence: float
      gaze: str  # "looking_at_camera" | "looking_away"
      head_gesture: str  # "nodding" | "shaking" | "still"
      engagement_score: float  # 0.0 - 1.0
      confusion_score: float  # 0.0 - 1.0
  ```
- Inject into LLM prompt:
  ```
  System: The user appears CONFUSED (engagement: 0.4). 
  Adjust your response — simplify, ask clarifying questions.
  ```
- Store vision context in session history (for later analysis)

**7.6 Performance Optimization**
- Run vision processing on a separate async task (non-blocking to audio/LLM)
- Frame skipping: detect face every frame, emotion every 15 frames, gaze every 5
- MPS acceleration for PyTorch models (DeepFace)
- If FPS drops below 5, reduce resolution to 320x240

**7.7 API**
- `WS /vision/stream` — updated to return:
  ```json
  {
    "type": "vision_context",
    "emotion": "confused",
    "gaze": "looking_at_camera",
    "head_gesture": "still",
    "engagement": 0.6,
    "confusion": 0.8,
    "frame_id": 142
  }
  ```

**7.8 Privacy & Compliance**
- **No raw frames stored or logged** — only feature vectors (emotion scores, gaze direction, head pose)
- Session logs contain: timestamps + vision_context (feature vectors only)
- User consent dialog before camera access
- Optional: on-device processing for all face data

**7.9 Testing**
- Unit: emotion classifier on labeled face dataset
- Integration: real webcam with acted expressions (sad, happy, confused)
- Accuracy: > 70% on test set (realistic target for emotion)
- Performance: vision pipeline < 50ms per frame

### Deliverables
- [ ] Emotion detection: 7 emotions, smoothed, injected into conversation
- [ ] Gaze tracking: looking at camera vs away
- [ ] Gesture detection: nod/shake
- [ ] Engagement score fed into LLM prompt
- [ ] Privacy: no raw frames persisted, only feature vectors
- [ ] Full multimodal conversation: audio + video → enriched responses

---

## Phase 8 — Production Hardening & Observability

**Goal:** Ship-ready. Monitoring, alerting, performance tuning, security audit, documentation, deployment.

### Tasks

**8.1 Monitoring & Alerting**
- Prometheus metrics on every endpoint
- Grafana dashboards:
  - Latency (VAD, STT, LLM, TTS, Vision) — p50/p95/p99
  - Error rates per service
  - Active sessions, queue depths
  - RAG retrieval precision
  - API usage per user
- Alert rules: >5% error rate, latency >5s p99, model not loaded

**8.2 Performance Tuning**
- Profile with py-spy / cProfile
- Optimize bottlenecks:
  - LLM speculative decoding (reduce TTFT)
  - STT model quantization (int8)
  - Vision frame pipeline (asyncio batching)
- Load testing: `locust` with 100 concurrent sessions
- Memory profiling: watch for leaks in long sessions

**8.3 Security**
- Rate limiting per IP, per user, per endpoint
- API key authentication (Bearer tokens)
- Input sanitization (prompt injection protection)
- CORS configuration for frontend origin
- Secrets management (HashiCorp Vault or env vars)
- Audit log: all requests with user_id, timestamp, action

**8.4 Documentation**
- API reference (OpenAPI/Swagger)
- Architecture diagram (updated)
- Runbook: how to start, debug, recover
- On-call guide: common issues and solutions

**8.5 Deployment Checklist**
- Docker images pushed to registry (GHCR / Docker Hub)
- docker-compose.prod.yml (no dev volumes, resource limits)
- Database migrations (Alembic for PostgreSQL)
- Backup strategy for Qdrant snapshots + PostgreSQL
- Zero-downtime deployment (rolling update)
- SSL termination (Caddy / nginx)

**8.6 Compliance Finalization**
- Consent flow for camera + audio
- Data retention policy (delete logs > 90 days)
- GDPR / DPDP Act compliance review
- Vulnerability scan (Trivy on Docker images)

### Deliverables
- [ ] Grafana dashboards for all services
- [ ] Load test passes 100 concurrent sessions
- [ ] Security scan passes
- [ ] API docs published
- [ ] Deployment runbook written
- [ ] All compliance requirements met

---

## Summary Timeline

| Phase | What | Estimated Effort |
|-------|------|-----------------|
| 1 | Foundation & Setup | 3-4 days |
| 2 | TTS | 3-4 days |
| 3 | STT | 5-7 days |
| 4 | LLM + RAG | 7-10 days |
| 5 | Conversation Loop | 4-5 days |
| 6 | Camera Integration | 3-4 days |
| 7 | CV & Emotion Analysis | 7-10 days |
| 8 | Production Hardening | 5-7 days |
| **Total** | | **~6-8 weeks** |
