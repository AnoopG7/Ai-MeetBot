# Technology Stack — Personal Finance Advisor AI Agent

> Every library, model, service, and tool selected with rationale. All open-source by default, API services listed as alternatives where local isn't viable.

---

## 1. Runtime & Language

| Choice | Version | Why |
|--------|---------|-----|
| **Python** | 3.12+ | AI/ML ecosystem leader. PyTorch, HuggingFace, LangChain, FastAPI all native. |
| **Node.js** | 20 LTS | Frontend build tooling (Vite, pnpm). Only for the React frontend. |
| **TypeScript** | 5.x | Type safety in the frontend. Catch bugs at compile time. |

**Why not:** Go (no ML ecosystem), Rust (too slow to iterate), Bun (not production proven for our stack).

---

## 2. Backend Framework

| Choice | Why | Rejected Alternatives |
|--------|-----|----------------------|
| **FastAPI** | Async-first, auto OpenAPI docs, Pydantic v2 integration, WebSocket support, industry standard for Python AI backends | Django (too heavy, not async-first), Flask (sync, no built-in WebSocket), Starlette (too raw) |

---

## 3. Speech-to-Text (STT)

### Primary: faster-whisper (large-v3)

| Aspect | Detail |
|--------|--------|
| **Why this** | 2-3x faster than OpenAI Whisper. int8 quantization. CTranslate2 backend. Runs on MPS (Apple Silicon). |
| **Model** | `large-v3` — 99 language support including Hindi, Tamil, Telugu. Best WER in open-source. |
| **Size** | ~3GB in int8, ~6GB in fp16 |
| **Latency** | ~0.3x real-time on M1 Max (3s audio → 1s to transcribe) |
| **Alternative** | **Whisper.cpp** — even faster, CPU-friendly, but slightly lower accuracy. Good fallback. |
| **Paid Alt** | **Deepgram Nova-2** — 300ms latency, best in class. $0.0043/min. |

### Voice Activity Detection: Silero VAD

| Aspect | Detail |
|--------|--------|
| **Why this** | < 1ms per 30ms chunk on CPU. 0.5% false positive rate. Pre-trained, no training needed. |
| **Model** | `silero_vad_v5` — PyTorch, 1.8MB |
| **Alternative** | WebRTC VAD (lighter but worse accuracy), PyAnnote (heavier, speaker diarization included) |

**Audio Capture:**
- **Local:** PyAudio (cross-platform mic access)
- **Browser:** `navigator.mediaDevices.getUserMedia` → Web Audio API
- **Processing:** 16kHz, 16-bit PCM mono (Whisper native format)

---

## 4. Text-to-Speech (TTS)

### Tier 1 (Default): Edge TTS

| Aspect | Detail |
|--------|--------|
| **Why this** | Free. 100+ voices (en-IN, hi-IN). Microsoft-quality neural TTS. SSML support for prosody control. |
| **Quality** | 8/10 — natural, but slight robotic edge detectable |
| **Latency** | ~500ms first chunk, ~2s for full 50-word sentence |
| **Constraint** | Requires internet (hits Microsoft servers) |
| **Lib** | `edge-tts` Python package |

### Tier 2 (Local): Coqui TTS (XTTS-v2)

| Aspect | Detail |
|--------|--------|
| **Why this** | 100% offline. Voice cloning from 30s sample. 17 languages including Hindi. |
| **Quality** | 7/10 — good with fine-tuning, slightly less natural than Edge |
| **Size** | ~1.8GB |
| **Latency** | ~1-2s for first chunk (GPU), ~3-4s (CPU) |
| **Lib** | `TTS` from Coqui-AI |
| **Setup** | `pip install TTS` + download XTTS-v2 |

### Tier 3 (Premium): ElevenLabs API

| Aspect | Detail |
|--------|--------|
| **Why this** | Best quality (9.5/10), ultra-realistic. Streaming in < 200ms. Voice library. |
| **Cost** | $5/month (starter), $0.30/1K chars (professional) |
| **When to use** | Production with budget. Voice cloning for brand voice. |

**Fallback chain:** Edge TTS → Coqui TTS → ElevenLabs

---

## 5. Large Language Model

### Primary (Local): Llama 3.1 8B via Ollama

| Aspect | Detail |
|--------|--------|
| **Why this** | Best open-weight model for its size. Strong instruction following. Good Indian context (trained on diverse data). |
| **Quantization** | Q4_K_M → 4.7GB RAM, fast on 8GB MacBook |
| **Serving** | Ollama — one-command setup, OpenAI-compatible API, model management |
| **Context** | 128K tokens |
| **Alternative** | **Mistral 7B v0.3** (faster, less knowledge), **Qwen 2.5 7B** (better math), **Phi-3 Medium** (strong for size, less finance knowledge) |

### Secondary (API): GPT-4o-mini

| Aspect | Detail |
|--------|--------|
| **Why this** | Cheap ($0.15/1M input), fast, strong reasoning. Escape hatch for complex queries. |
| **When** | When local LLM confidence < 0.6, route to GPT-4o-mini for second opinion |

**Never:** Use GPT-4 or Claude for primary (too expensive at scale). Keep for fallback/hard questions.

---

## 6. Embeddings

| Choice | Why | Details |
|--------|-----|---------|
| **BAAI/bge-small-en-v1.5** | Best size/quality tradeoff. 384 dim → fast retrieval, cheap storage. MTEB score: 59.3. | 33MB, 1024 max tokens |
| **BAAI/bge-reranker-v2-m3** | Cross-encoder reranker. Finances the top-20 results. | ~500ms per query, but significantly improves precision |
| **Alternative** | `text-embedding-3-small` (OpenAI API, 512 dim, best quality) — paid, 384 dim model is good enough |

---

## 7. Vector Database

| Choice | Why | Rejected Alternatives |
|--------|-----|----------------------|
| **Qdrant** | Best open-source vector DB. Native sparse vectors (hybrid search out of box). Built-in filtering, quantization, payload indexing. Fast. | ChromaDB (good for prototyping, unstable at scale), Pinecone (proprietary, expensive), Weaviate (heavy, needs k8s), FAISS (not a DB, no filtering) |

**Setup:** Docker container, REST + gRPC API, binary quantization for 4x memory reduction.

---

## 8. Computer Vision

### Face Detection & Tracking

| Choice | Why |
|--------|-----|
| **MediaPipe Face Detection** | BlazeFace — 200 FPS on CPU. 6 keypoints. 95% accuracy on frontal faces. |
| **MediaPipe Face Mesh** | 468 3D landmarks. Iris tracking. Head pose estimation. 100 FPS on GPU. |

### Emotion Recognition

| Choice | Why | Alternatives Rejected |
|--------|-----|----------------------|
| **DeepFace** | Wraps 6 models (VGG-Face, GoogleNet, etc.). Best accuracy for zero-shot. 7 emotions. Single API call. | FER (less accurate, limited models), Custom CNN (needs training data), Microsoft Face API (paid, cloud) |

**Optimization:** DeepFace only runs every 15 frames (~2x/sec). MediaPipe runs every frame.

### Gesture & Pose

| Choice | Why |
|--------|-----|
| **MediaPipe Pose** | 33 landmarks. Full upper body. Nod/shake detection via head rotation. |
| **MediaPipe Hands** | 21 landmarks per hand. Gesture recognition (pointing, stop, thumbs up). |

---

## 9. RAG & LLM Orchestration

| Choice | Why | Alternatives Rejected |
|--------|-----|----------------------|
| **LangChain** | Industry standard. RAG pipelines, chains, tool use, callbacks. Huge ecosystem. | LlamaIndex (too opinionated, more for document indexing than agents), Haystack (less flexible) |
| **LangGraph** | State machine for multi-step agent workflows. Better than LangChain's AgentExecutor. | Custom asyncio (more work) |

**Note:** Use LangChain for RAG + LLM calls. Use LangGraph for complex multi-step reasoning. Don't use LangChain for everything — keep audio/vision pipelines separate.

---

## 10. Memory

| Choice | Why | Alternatives Rejected |
|--------|-----|----------------------|
| **Mem0** | Purpose-built for AI agent memory. Auto-summarization, entity extraction, importance scoring. Open-source. | Zep (heavier, less transparent), Custom SQL (more work, no auto-summarization) |
| **Redis** | Short-term session cache, TTL-based expiry, pub/sub for events. | In-memory dict (no persistence, no TTL) |
| **PostgreSQL** | Long-term storage. Session logs, audit trail, user profiles. JSONB for flexible schemas. | SQLite (no concurrent access, no networking) |

---

## 11. Frontend

| Layer | Choice | Why |
|-------|--------|-----|
| **Framework** | React 18 + TypeScript | Universal, huge ecosystem, shadcn/ui compatible |
| **Build** | Vite | 10x faster than Webpack. HMR in milliseconds. |
| **Styling** | TailwindCSS | Utility-first. Zero runtime. Easy theming. |
| **Components** | shadcn/ui | Copy-paste components, fully customizable, Radix-based accessibility |
| **State** | Zustand | Simple, TypeScript-native. No boilerplate like Redux. |
| **WebSocket** | Native WebSocket API | No library needed. STT + Vision streams. |
| **Audio** | Web Audio API | Browser-native. Stream mic → encode → send. |

**Why not:** Next.js (SSR not needed for a real-time video app), SPA is simpler and sufficient.

---

## 12. Infrastructure & DevOps

| Layer | Choice | Why |
|-------|--------|-----|
| **Container** | Docker + Compose | Reproducible dev environment. Dev → prod parity. |
| **CI/CD** | GitHub Actions | Free for public repos, tight GitHub integration. |
| **Reverse Proxy** | Caddy | Auto HTTPS. Zero config. Serves static files + proxies APIs. |
| **Monitoring** | Prometheus + Grafana | Industry standard. FastAPI has prometheus client. Grafana dashboards. |
| **Logging** | structlog | Structured JSON logs. Request IDs. Easy to ship to Loki/Datadog. |
| **Process Mgr** | Supervisord / systemd | Keep processes alive in production. |

---

## 13. Testing

| Type | Tools |
|------|-------|
| **Unit** | pytest + pytest-asyncio |
| **Coverage** | pytest-cov (target: > 80%) |
| **Lint** | Ruff (replaces flake8 + isort + pyupgrade) |
| **Types** | mypy (strict mode) |
| **API** | httpx (async test client for FastAPI) |
| **Load** | locust (100 concurrent sessions) |
| **E2E** | Playwright (frontend tests) |
| **Pre-commit** | pre-commit hooks (ruff, mypy, pytest) |

---

## 14. Summary Decision Matrix

| Requirement | Chosen Solution | Open Source? | Local? | Production Ready? |
|-------------|----------------|:---:|:---:|:---:|
| Runtime | Python 3.12 | ✅ | ✅ | ✅ |
| API Framework | FastAPI | ✅ | ✅ | ✅ |
| STT | faster-whisper large-v3 | ✅ | ✅ | ✅ |
| VAD | Silero VAD | ✅ | ✅ | ✅ |
| TTS | Edge TTS → Coqui XTTSv2 | ✅ | Partial (Coqui) | ✅ |
| LLM | Llama 3.1 8B (Ollama) | ✅ | ✅ | ✅ |
| Embeddings | BGE-small-en-v1.5 | ✅ | ✅ | ✅ |
| Vector DB | Qdrant | ✅ | ✅ | ✅ |
| Face Tracking | MediaPipe | ✅ | ✅ | ✅ |
| Emotion | DeepFace | ✅ | ✅ | ⚠️ Moderate |
| RAG | LangChain + LangGraph | ✅ | ✅ | ✅ |
| Memory | Mem0 + Redis + PostgreSQL | ✅ (Mem0) | ✅ | ✅ |
| Frontend | React + Vite + Tailwind | ✅ | ✅ | ✅ |
| Monitoring | Prometheus + Grafana | ✅ | ✅ | ✅ |
| Container | Docker | ✅ | ✅ | ✅ |

### Key ⚠️ Notes

| Warning | Reason |
|---------|--------|
| **Emotion accuracy is ~65%** | FER in real-world video is unreliable. Never make critical decisions based on it. Use as soft signal only. |
| **Whisper latency adds ~1-2s** | Real-time factor is ~0.3x, but VAD segmentation + network adds overhead. Budget 2s for STT alone. |
| **Local LLM quality < GPT-4** | Llama 3.1 8B is good but hallucinates. RAG helps but doesn't eliminate. Always add disclaimers. |
| **Memory leaks in long sessions** | Python + ML models can leak. Watch GPU memory. Restart worker periodically. |
