# Third-Party Projects & Open-Source Leverage

> Everything we can steal—sorry, *strategically adopt*—so we don't build from scratch.

---

## 0. The Two You Asked About

### LivePortrait (KlingAI) — `github.com/KlingAIResearch/LivePortrait`

**What it is:** Portrait animation model. Takes a static photo + driving video → animates the photo to match the driving video's expressions and head movements. 18.3k stars.

| Aspect | Detail |
|--------|--------|
| Stars | 18.3k |
| License | Custom (check LICENSE) |
| Compute | RTX 4090 recommended, ~20x slower on Mac |
| Latency | Not real-time (~seconds per inference) |
| Use Case | Generating a talking avatar face for the BOT, not analyzing the user |

**Verdict for our use case:**

| Would we use it? | Why/Why Not |
|-----------------|-------------|
| ❌ Phase 1-7 | We're analyzing the *user's* face, not generating a face for the bot. The bot doesn't need a visual avatar in our architecture — it's a voice agent with CV capabilities for understanding the user, not a talking head. |
| 🤷 Phase 8+ | If we ever want a "digital advisor face" that lip-syncs to TTS output, LivePortrait or its TensorRT derivatives (FasterLivePortrait) could work. But that's a UI nicety, not core. |

**Skip it for now.** It solves a different problem (avatar generation, not user analysis). If you want a digital human face later, look at **SoulX-FlashHead** or **IMTalker** instead (better real-time performance).

---

### Roboflow — `roboflow.com`

**What it is:** End-to-end computer vision platform. Dataset management, annotation (AI-assisted), model training (AutoML), deployment API. 90k+ public datasets. 1M+ developers.

| Aspect | Detail |
|--------|--------|
| Pricing | Free (public), $79/mo (Core), Custom (Enterprise) |
| Models | Object detection, classification, segmentation (YOLO, RF-DETR) |
| Deployment | Cloud API, edge, on-prem |
| Training | AutoML on their GPUs, or export to PyTorch/TF |

**Verdict for our use case:**

| Would we use it? | Why/Why Not |
|-----------------|-------------|
| ✅ For custom training | If we want to train a *custom* emotion/gesture detector on Indian faces (since DeepFace was trained on Western datasets), Roboflow is great for annotating a dataset of Indian facial expressions. |
| ❌ For inference | Their inference API is for object detection / classification, not real-time face mesh or emotion. We'd still use MediaPipe + DeepFace locally. |
| ✅ For dataset creation | Label faces with specific expressions (confused, frustrated, etc.) → export to YOLO format → train a lightweight custom model. |

**Use it only if:** We find DeepFace's accuracy unacceptable for Indian faces and decide to train our own emotion classifier. Otherwise, skip.

---

## 1. Full Agent Frameworks (Biggest Leverage)

These are the most important finds. They solve 60% of our architecture — the real-time audio pipeline, STT/TTS/LLM orchestration, VAD, and WebRTC transport. **We should absolutely build on one of these.**

### 1.1 LiveKit Agents — `github.com/livekit/agents`

| Stats | Detail |
|-------|--------|
| Stars | 10.4k |
| License | Apache 2.0 |
| Language | Python (primary), Rust core |
| Maintainer | LiveKit (backed by YC, $10M funding) |
| Status | Mature, 351 releases, 370 contributors |

**What it gives us:**
- Agent framework: define instructions, tools, and the framework handles VAD → STT → LLM → TTS pipeline
- WebRTC transport built-in (no reinventing media streaming)
- Plugin ecosystem: Deepgram, Whisper, OpenAI, ElevenLabs, Cartesia, Azure, Google, etc.
- Job scheduling: automatically connect users to agent instances
- Built-in VAD (Silero), turn detection, barge-in (interruption handling)
- MCP support for tool integration
- Video support: can process incoming video frames (for our CV)
- AgentSession: manages full conversation lifecycle

**Why this is huge for us:**
```
Without LiveKit:          With LiveKit:
- Write WebRTC server    - Use their WebRTC
- Build VAD + pipeline   - Built-in VAD + pipeline
- Manage audio buffers   - Automatic buffering
- Handle interruptions   - Built-in barge-in
- Scale sessions         - Built-in job scheduling
- Wire STT/TTS/LLM       - 30+ plugins ready
```
**Estimated time saved: 4-6 weeks** of plumbing.

**Limitations:**
- LiveKit Server is another dependency to run (but Docker-friendly)
- Emotion/vision is our code on top — they don't do this yet
- Some plugins (Deepgram Nova, Cartesia Sonic) are API-based, not local

**Verdict: STRONG YES — build on top of this.**

---

### 1.2 Pipecat — `github.com/pipecat-ai/pipecat`

| Stats | Detail |
|-------|--------|
| Stars | 11.4k |
| License | BSD-2 |
| Language | Python |
| Maintainer | Daily.co (WebRTC infrastructure company) |
| Status | v1.0 released (April 2026), 108 releases |

**What it gives us:**
- Same category as LiveKit Agents — real-time voice/multimodal agent framework
- Massive service integrations (50+):
  - STT: Deepgram, AssemblyAI, Azure, Google, Whisper, Groq, etc.
  - LLM: OpenAI, Anthropic, Gemini, Ollama, DeepSeek, Mistral, etc.
  - TTS: ElevenLabs, Cartesia, Deepgram, Google, OpenAI, Kokoro, etc.
  - Transport: Daily (WebRTC), FastAPI WebSocket, LiveKit, Twilio
  - Vision: HeyGen, Tavus
- Silero VAD, RNNoise for echo cancellation
- Mem0 integrated for memory
- OpenTelemetry for observability
- Pipeline-based architecture (very composable)

**What it's missing vs LiveKit:**
- No built-in video frame processing (we'd need to add CV separately)
- Own transport layer, less battle-tested than LiveKit's WebRTC
- Smaller community (230 contributors vs 370)
- Requires Daily WebRTC or WebSocket — less flexible than LiveKit

**Verdict: STRONG YES — slightly behind LiveKit for our use case since we need video frame access.**

---

### 1.3 TEN Framework — `github.com/ten-framework/ten-framework`

| Stats | Detail |
|-------|--------|
| Stars | 10.4k |
| License | Custom (Agora-backed) |
| Language | Python + C++ + Rust core |
| Maintainer | Agora (publicly traded WebRTC company, $2B+ mkt cap) |
| Status | 0.11.x, rapid development |

**What it gives us:**
- Real-time multimodal framework (voice + vision + avatar)
- Extension-based architecture (swap components easily)
- Built-in VAD + Turn Detection modules (separate repos, high quality)
- TMAN Designer: low-code UI for designing voice agents
- Already supports Gemini Live vision, avatar integration, MCP
- Enterprise backing (Agora)

**Concerns:**
- License is custom (not Apache/MIT) — need to verify commercial terms
- Heavier dependency (C++ extensions, Rust core)
- Less Pythonic than Pipecat or LiveKit Agents
- Documentation is Chinese-first, English translations catching up

**Verdict: YES — but run it in Docker and verify license terms first.**

---

### 1.4 LLMRTC — `github.com/llmrtc/llmrtc`

| Stats | Detail |
|-------|--------|
| Stars | 8 |
| License | Apache 2.0 |
| Language | TypeScript |
| Status | Very new |

**Verdict: SKIP.** Too early, TypeScript-only, tiny community. Monitor for future.

---

### Framework Comparison Summary

| Feature | LiveKit Agents | Pipecat | TEN Framework |
|---------|:---:|:---:|:---:|
| WebRTC transport | ✅ Native | ✅ Via Daily | ✅ Native |
| STT plugins | 10+ | 15+ | 10+ |
| LLM plugins | 15+ | 20+ | 15+ |
| TTS plugins | 10+ | 25+ | 10+ |
| VAD (local) | ✅ Silero | ✅ Silero | ✅ Custom |
| Barge-in / Interrupt | ✅ | ✅ | ✅ |
| Video frame access | ✅ | ⚠️ Limited | ✅ |
| Memory (Mem0) | Manual | ✅ Built-in | Manual |
| MCP support | ✅ | Manual | ✅ |
| CV integration | We build on top | We build on top | We build on top |
| License | Apache 2.0 | BSD-2 | Custom (verify) |
| Maturity | Most mature | Very mature | Rapidly growing |

**Our recommendation: Start with LiveKit Agents.** Best WebRTC, most mature, built for video, Apache 2.0.

---

## 2. Talking Head / Digital Avatar (Phase 8+)

If we want the bot to have a *face* on screen. **Not needed for Phase 1-7.**

| Project | What | FPS | GPU | Why Interesting |
|---------|------|:---:|:---:|-----------------|
| **SoulX-FlashHead** | 1.3B streaming talking head, 96 FPS lite, 25+ FPS on single RTX 4090 | 96 | RTX 4090 | Real-time streaming, Apache 2.0, HuggingFace demo live |
| **IMTalker** | Audio-driven talking face, 42 FPS at 512×512 | 42 | RTX 4090 | Fast, open, supports head-pose and eye-gaze control |
| **ARTalk** | 3D head animation from audio, autoregressive | Real-time | RTX 4090 | 3D FLAME model, supports expression/pose style transfer |
| **LiveTalk** | Multimodal interactive video diffusion, 24.82 FPS | 24.8 | 20GB VRAM | End-to-end diffusion, KV-cache streaming |
| **LiteAvatar** | CPU-only 30 FPS avatar | 30 | CPU! | Runs on phones, MIT license |
| **OpenAvatarChat** | Full digital human system, modular ASR/LLM/TTS/Avatar | Varies | Varies | Already integrates FlashHead, MuseTalk, LiteAvatar. Pre-built! |

**Key insight:** If we want a face, **OpenAvatarChat** (3.3k stars, Apache 2.0) is closest to our architecture already built. It has:
- ASR + LLM + TTS + Avatar pipeline
- Multiple avatar backends (LiteAvatar, MuseTalk, FlashHead)
- VAD + turn detection
- Pre-built configs for different use cases
- Agent mode with tool calling

---

## 3. Emotion & Facial Analysis

Better/alternative options to DeepFace for Phase 7.

| Project | What | Accuracy | Why Consider |
|---------|------|:--------:|--------------|
| **OpenFace 3.0** (CMU) | Face landmarks, Action Units, emotion, gaze - all in one | Research-grade | Built by CMU. Action Units (AU) are more granular than 7 emotions. Gaze + emotion + AU in one model. |
| **EmotiEffLib** (sb-ai-lab) | Lightweight emotion + engagement recognition, 1k stars | 63% on AffectNet | 1.1ms inference on Android. ONNX export. Apache 2.0. Actively maintained. |
| **LibreFace** (ihp-lab) | ResNet-18 based, real-time facial expression analysis | SOTA | WACV 2024 paper. Real-time on CPU + GPU. ONNX export. |
| **EmoNet** (face-analysis) | Valence + arousal (continuous emotions, not categorical) | Nature MI paper | Predicts valence/arousal (1 to -1) instead of 7 categories. More nuanced. |
| **MediaPipe + Custom RF** | 468 landmarks → Random Forest for 7 emotions | ~65% | Simple, fast, works with what we already have |

**Our recommendation:**

| Layer | Choice | Why |
|-------|--------|-----|
| Face mesh | **MediaPipe** (Phase 6-7) | Already in our stack, 468 landmarks, 100+ FPS, cross-platform |
| Emotion | **EmotiEffLib** or **LibreFace** → replace DeepFace in Phase 7 | 2-5x faster than DeepFace, better real-time perf |
| Gaze + Action Units | **OpenFace 3.0** (add in Phase 7) | Gaze + AU + emotion = single model, more expressive than 7 emotions |
| Custom training | **Roboflow** (only if needed) | If accuracy on Indian faces is too low, annotate + train custom |

**Why replace DeepFace:** DeepFace loads 6 models behind the scenes, takes 200-500ms per frame, and isn't optimized for real-time. EmotiEffLib does the same job in 1-2ms.

---

## 4. Finance-Specific NLP & RAG

These save us months of data collection and fine-tuning.

| Project | What | Stars | Why It Matters |
|---------|------|:-----:|----------------|
| **FinGPT** | Open-source financial LLM (fine-tuned on finance data) | 19.9k | Pre-trained financial models. MIT license. Sentiment analysis, forecasting, QA. Can fine-tune for Indian finance. |
| **FinSage** | Multi-aspect RAG for financial filings | Paper | 92.5% recall on FinanceBench. Multi-path hybrid retrieval. Deployed as QA agent serving 1200+ users in meetings. |
| **FinAgent-RAG** | Agentic RAG with contrastive retriever + PoT reasoning | New | 76.81% on FinQA (+9% over baseline). Program-of-Thought for math. Adaptive router saves 41% API costs. |
| **rLLM FinQA-4B** | 4B financial agent trained with RL | New | 59.7% accuracy on Snorkel Finance. Beats 235B models. RL-trained for tool use (SQL, calculator). |
| **FinBERT-QA** | BERT-based financial QA (FiQA dataset) | 130 | Lighter than LLMs. Good fallback for simple FAQ. |
| **Arthyx** | Autonomous quant analyst with Neo4j knowledge graph | New | Indian-specific! RBI regulations, Basel III, Hindi/Tamil OCR. Built for Indian finance documents. |
| **SMARTFinRAG** | Modular financial RAG evaluation framework | New | Swap components, ablation studies, LLM-as-judge eval. Good for testing our RAG pipeline. |

**Our recommendations for finance layer:**

| Component | Use | Project |
|-----------|-----|---------|
| Base LLM | Finance-tuned starting point | **FinGPT** — use their fine-tuned weights or fine-tuning recipe |
| RAG pipeline | Document QA over RBI/SEBI docs | **FinSage** architecture — hybrid retrieval + reranking + HyDE |
| Math/Calc | Numerical reasoning (EMI, returns, etc.) | **FinAgent-RAG** Program-of-Thought approach — generates Python, not mental math |
| Tool-agent | Multi-step financial analysis | **rLLM FinQA-4B** pattern — small model + tools > large model alone |
| Indian regulations | RBI/SEBI-specific knowledge | **Arthyx** — borrow their regulatory encoding approach |
| A/B testing | Evaluate RAG quality | **SMARTFinRAG** — swap components, measure precision/faithfulness |

---

## 5. Memory & Agent Orchestration

| Project | What | Why |
|---------|------|-----|
| **Mem0** (`mem0.ai`) | Agent memory with auto-summarization, entity extraction, importance scoring | Already in our stack. 22k+ stars. |
| **LangGraph** (`langchain-ai/langgraph`) | State machines for agent workflows | Multi-step reasoning, branching, tool loops. Pairs with LangChain. |
| **CrewAI** (`crewai.com`) | Multi-agent orchestration | If we split advisor into sub-agents (risk analyst, product specialist, compliance checker). |

---

## 6. Audio Processing

| Project | What | Why |
|---------|------|-----|
| **RNNoise** | Real-time noise suppression | Mozilla project. C library, Python bindings. Removes background noise before STT. |
| **Krisp VAD** | AI echo cancellation + noise reduction | Via Pipecat plugin. Commercial-grade, free tier. |
| **FunASR** (Alibaba) | ASR with speaker diarization, language ID | Better than Whisper for Chinese/Asian languages. Might improve Hindi accuracy. |

---

## 7. Summary: What We Actually Use

| Category | What We Take | Why |
|----------|-------------|-----|
| **Agent Framework** | **LiveKit Agents** (or Pipecat) | 4-6 weeks of plumbing saved. WebRTC, VAD, barge-in, plugin ecosystem. |
| **Finance LLM** | **FinGPT** weights/fine-tuning recipe | Finance-tuned from day 1, MIT license |
| **RAG Architecture** | **FinSage** patterns | Hybrid retrieval, reranking, metadata filtering |
| **Math Reasoning** | **FinAgent-RAG** PoT approach | Generate Python code for EMI/ROI calculations |
| **Emotion CV** | **MediaPipe** + **EmotiEffLib** (replace DeepFace) | 100x faster than DeepFace, same accuracy |
| **Memory** | **Mem0** (already planned) | Auto-summarization, entity extraction |
| **Digital Avatar** | **OpenAvatarChat** (Phase 8+, if at all) | Pre-built full pipeline, modular avatar backends |
| **Indian Regulations** | **Arthyx** approach to RBI/SEBI encoding | Borrow their regulatory knowledge encoding strategy |

### What We Still Build Ourselves

| Component | Why We Build |
|-----------|-------------|
| Finance knowledge base ingestion (RBI/SEBI PDFs → Qdrant) | Domain-specific, no project does Indian finance comprehensively |
| Multimodal fusion (emotion + text → enriched prompts) | Novel integration, no framework does this |
| Compliance guardrails (SEBI disclaimers, stock tip blocking) | Regulatory requirement, must be custom |
| Session audit logging | Regulatory requirement (DPDP Act) |
| Emotion → Agent response mapping | Our specific UX design |
| Frontend React app | Custom UI, not something to steal |

### Projects to Skip (For Now)

| Project | Why Skip |
|---------|----------|
| **LivePortrait** | Avatar generation, not user analysis. Wrong problem. |
| **SoulX-FlashHead / FlashTalk** | Need 40GB VRAM + RTX 4090/5090. Heavy. Phase 8 maybe. |
| **LLMRTC** | Too new, TypeScript-only, 8 stars. |
| **Linly-Talker-Stream** | Interesting but Chinese-first docs, complex setup. |
| **EmoNet** | Valence/arousal is nice but EmotiEffLib gives both categorical + VA. |
