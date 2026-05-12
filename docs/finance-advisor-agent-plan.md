# Personal Finance Advisor AI Agent — Detailed Planning Document

> **Vision:** A multimodal conversational AI agent that joins video calls, understands speech + facial expressions + body language, and provides expert personal finance advice in real time.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Phase 1 — Local MVP](#2-phase-1--local-mvp)
3. [Tech Stack & Models](#3-tech-stack--models)
4. [Data Sources](#4-data-sources)
5. [Use Case Breakdown](#5-use-case-breakdown)
6. [Implementation Roadmap](#6-implementation-roadmap)
7. [Known Challenges & Risks](#7-known-challenges--risks)
8. [Ways to Make It Better](#8-ways-to-make-it-better)

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        INPUT LAYER                                  │
│  ┌────────────┐  ┌────────────┐  ┌──────────────────────────────┐  │
│  │ Webcam     │  │ Microphone │  │ Screen Share / Doc Upload    │  │
│  └─────┬──────┘  └─────┬──────┘  └──────────┬───────────────────┘  │
│        │               │                     │                      │
├────────┼───────────────┼─────────────────────┼──────────────────────┤
│        ▼               ▼                     ▼                      │
│  ┌────────────┐  ┌────────────┐  ┌──────────────────────────────┐  │
│  │ MediaPipe  │  │ Silero VAD │  │ OCR (PaddleOCR / Tesseract)  │  │
│  │ Face Mesh  │  │ (Voice     │  │ for docs/slides              │  │
│  │ Pose/Hands │  │  Activity) │  │                              │  │
│  │ DeepFace   │  │            │  │                              │  │
│  └─────┬──────┘  └─────┬──────┘  └──────────┬───────────────────┘  │
│        │               │                     │                      │
│        ▼               ▼                     ▼                      │
│  ┌────────────┐  ┌────────────┐                                   │
│  │ Emotion    │  │ Whisper    │                                   │
│  │ Vectors    │  │ (STT)      │                                   │
│  │ + Intent   │  │ → Text    │                                   │
│  └─────┬──────┘  └─────┬──────┘                                   │
│        │               │                                           │
├────────┼───────────────┼───────────────────────────────────────────┤
│        ▼               ▼                                           │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │                    FUSION LAYER                              │  │
│  │  Combine: text + emotion vectors + visual context           │  │
│  │  → Single enriched prompt for LLM                          │  │
│  └─────────────────────────┬───────────────────────────────────┘  │
│                            │                                       │
├────────────────────────────┼───────────────────────────────────────┤
│                            ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │                    REASONING LAYER                           │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │  │
│  │  │ LLM      │  │ RAG      │  │ Memory   │  │ Finance  │   │  │
│  │  │ (Llama 3 │  │ (Finance │  │ (Mem0 /  │  │ Graph    │   │  │
│  │  │  / GPT)  │  │  Docs)   │  │  Vector) │  │ (Neo4j)  │   │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │  │
│  └─────────────────────────┬───────────────────────────────────┘  │
│                            │                                       │
├────────────────────────────┼───────────────────────────────────────┤
│                            ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │                    OUTPUT LAYER                              │  │
│  │  ┌────────────┐  ┌────────────┐  ┌──────────────────────┐  │  │
│  │  │ Coqui/Edge │  │ Finance    │  │ Real-time            │  │  │
│  │  │ TTS        │  │ Dashboard  │  │ Recommendations      │  │  │
│  │  │ → Audio   │  │ Overlay   │  │ (visual cues)        │  │  │
│  │  └────────────┘  └────────────┘  └──────────────────────┘  │  │
│  └─────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Phase 1 — Local MVP

### What We Build First
A **local Python app** that:
- Opens webcam + microphone
- Detects face, emotion, basic gestures (nodding, shaking head, hand raises)
- Transcribes speech in near real-time
- Answers finance questions using a local LLM + RAG on finance PDFs
- Speaks back via TTS
- Maintains conversation memory

### High-Level Data Flow

```
[Webcam] ──► OpenCV ──► MediaPipe ──► Emotion + Posture
                                    │
[Mic] ──► PyAudio ──► Silero VAD ──► Whisper STT ──► Text
                                    │
                                    ▼
                          ┌─────────────────────┐
                          │ Fusion: Build Prompt │
                          │ "User looks confused │
                          │  and asks about SIP" │
                          └─────────┬───────────┘
                                    ▼
                          ┌─────────────────────┐
                          │ LLM + RAG           │
                          │ (Finance Knowledge) │
                          └─────────┬───────────┘
                                    ▼
                          ┌─────────────────────┐
                          │ TTS → Speaker       │
                          │ + UI Overlay        │
                          └─────────────────────┘
```

---

## 3. Tech Stack & Models

### 3.1 Speech-to-Text (STT)

| Library | Why | Caveat |
|---------|-----|--------|
| **faster-whisper** (`large-v3`) | Best accuracy, runs on MPS (Apple Silicon), ~2-3x real-time | Needs ~3GB VRAM |
| **Whisper.cpp** | Lower latency, CPU-friendly | Slightly lower accuracy |
| **Deepgram (API)** | Best latency (~300ms) | Paid, needs internet |

**Recommendation:** Start with `faster-whisper` with `large-v3` model. Quantize to int8 for speed.

```python
from faster_whisper import WhisperModel
model = WhisperModel("large-v3", device="mps", compute_type="int8_float16")
```

### 3.2 Voice Activity Detection (VAD)

| Library | Why |
|---------|-----|
| **Silero VAD** | Best open-source, low CPU, accurate |
| **WebRTC VAD** | Lighter but less accurate |

```python
import silero_vad
vad = silero_vad.load_silero_vad()
# Process 30ms audio chunks, flag speech segments
```

### 3.3 Text-to-Speech (TTS)

| Library | Why | Caveat |
|---------|-----|--------|
| **Coqui TTS** (XTTS-v2) | Voice cloning, 6 Indian lang support, local | Heavy (~2GB) |
| **Edge TTS** (edge-tts) | Free, 100+ voices, no GPU needed | Internet required |
| **Piper TTS** | Ultra-fast local, low resource | Robotic, English-only |
| **ElevenLabs (API)** | Best quality | Paid |

**Recommendation:** Edge TTS for Phase 1 (zero setup), Coqui XTTSv2 for Phase 2 (custom voice, offline).

### 3.4 LLM

| Model | Why | Caveat |
|-------|-----|--------|
| **Llama 3.1 8B** (via Ollama) | Best open-weight, runs on 8GB Mac | 4-bit quant needed |
| **Mistral 7B v0.3** | Fast, good reasoning, finance FT available | Slightly lower quality |
| **Qwen 2.5 7B** | Strong on math/finance, 32k ctx | Newer, less ecosystem |
| **GPT-4o-mini (API)** | Cheap, fast, multimodal | Paid, no local |
| **Gemini 1.5 Flash (API)** | 1M context, native video input | Paid, no local |

**Recommendation:**  
- **Local:** Llama 3.1 8B via Ollama + LangChain
- **API:** GPT-4o-mini as escape hatch for complex queries

```bash
ollama pull llama3.1:8b-instruct-q4_K_M
```

### 3.5 Finance RAG Pipeline

```
Finance PDFs / Docs
       │
       ▼
┌──────────────────────┐
│ Chunking (500-1000t) │
│ RecursiveTextSplitter│
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Embeddings           │
│ (BGE-small / ADA-002)│
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Vector DB            │
│ (ChromaDB / Qdrant)  │
└──────────┬───────────┘
           ▼
┌──────────────────────────────────┐
│ Retrieval:  "query → top-5 chunks │
│ → LLM prompt with context"       │
└──────────────────────────────────┘
```

**Embedding Models:**
- **BAAI/bge-small-en-v1.5** — local, 384 dim, fast
- **text-embedding-3-small** — best quality (API)

**Vector DB:**
- **ChromaDB** — easiest, file-based, good for Phase 1
- **Qdrant** — faster, better filtering, good for Phase 2

### 3.6 Computer Vision

| Task | Library | Model |
|------|---------|-------|
| Face Detection | MediaPipe | Face Detection (BlazeFace) |
| Face Mesh (468 landmarks) | MediaPipe | Face Mesh |
| Emotion Recognition | DeepFace / FER | VGG-Face, ResNet-50 |
| Pose Estimation | MediaPipe | BlazePose (33 landmarks) |
| Hand Tracking | MediaPipe | Hands (21 landmarks) |
| Gaze Detection | MediaPipe | Iris landmarks from Face Mesh |
| Head Pose | MediaPipe | SolvePnP from face landmarks |

```python
import mediapipe as mp
import cv2
from deepface import DeepFace

# Face mesh for expression/gaze
face_mesh = mp.solutions.face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,  # includes iris
    min_detection_confidence=0.5
)

# Emotion every N frames (skip for perf)
emotion = DeepFace.analyze(frame, actions=['emotion'], enforce_detection=False)
```

**What we detect:**
- **Emotions:** happy, sad, angry, surprised, fearful, disgusted, neutral
- **Engagement:** looking at camera vs away, nodding, head shaking
- **Confusion:** brow furrow, head tilt, prolonged neutral + no speech
- **Agreement:** nodding + smile
- **Frustration:** brow lower, lip tight, head shake

### 3.7 Memory System

| System | Why |
|--------|-----|
| **Mem0** | Purpose-built for AI agents, auto-manages short/long-term memory |
| **LangGraph + Custom** | More control, checkpointing |
| **Zep** | Open-source, built for conversations |

**Memory Store:**
- Short-term: In-memory dict of last N exchanges
- Long-term: Vector DB with summarization + entities
- Session: Conversation JSON log

Example memory schema:
```python
{
    "user_id": "u_123",
    "session_id": "s_456",
    "turn": 12,
    "query": "Should I invest in PPF?",
    "emotion": "curious",
    "financial_context": {
        "risk_profile": "moderate",
        "mentioned_products": ["PPF", "ELSS"],
        "age_group": "30-35",
        "goals": ["retirement", "tax_saving"]
    },
    "response": "PPF offers 7.1% with EEE status...",
    "follow_up_needed": False
}
```

---

## 4. Data Sources

### 4.1 Indian Financial Regulations & Knowledge

| Source | Content | Access |
|--------|---------|--------|
| **RBI Master Directions** | Banking, NBFC, KYC, UPI regulations | [rbi.org.in](https://rbi.org.in) |
| **SEBI Guidelines** | Mutual funds, stock market, investment advisors | [sebi.gov.in](https://sebi.gov.in) |
| **IRDAI Regulations** | Insurance products, claims | [irdai.gov.in](https://irdai.gov.in) |
| **Income Tax Act** | Tax slabs, deductions (80C, 80D, etc.) | [incometax.gov.in](https://incometax.gov.in) |
| **PFRDA** | NPS, pension rules | [pfrda.org.in](https://pfrda.org.in) |
| **BSE/NSE** | Listed products, index info | [bseindia.com](https://bseindia.com) |

**Scraping Strategy:**
- Use `Firecrawl` or `BeautifulSoup` to scrape PDFs + web pages
- Store as Markdown in a `data/knowledge/` directory
- Chunk and embed into ChromaDB

### 4.2 Financial Product Data

| Product | Source |
|---------|--------|
| Mutual Funds | AMFI, ValueResearch, Morningstar |
| Fixed Deposits | Bank websites, RBI |
| Insurance Plans | IRDAI, Policybazaar |
| Loans (Home, Personal, Education) | Bank websites, Paisabazaar |
| Credit Cards | Bank websites, Cardexpert |
| NPS | PFRDA, NSDL |

### 4.3 Training / Fine-Tuning Data

| Dataset | Use | Where |
|---------|-----|-------|
| **FinQA** | Financial QA (numerical reasoning) | Hugging Face |
| **FinanceBench** | Real-world finance questions | Hugging Face |
| **TAT-QA** | Table-based financial QA | Hugging Face |
| **ConvFinQA** | Conversational finance QA | Hugging Face |
| **BloombergGPT data** | 363B token finance corpus | Not public (inspiration) |
| **Investopedia** articles | Educational finance content | investopedia.com |
| **SEC Filings (EDGAR)** | Corporate finance data | sec.gov/edgar |

### 4.4 Customer Support Data

| Source | Content |
|--------|---------|
| **Bank call transcripts** (if available) | Real queries, intents |
| **Twitter/X banking complaints** | Common issues, language |
| **Reddit r/IndiaInvestments** | Real user questions |
| **Quora finance questions** | FAQ-style corpus |

### 4.5 Synthetic Data Generation

Use GPT-4o to generate synthetic QA pairs:
```
Prompt: "Generate 10 conversational question-answer pairs about 
home loan eligibility for a salaried individual in India. 
Include follow-up questions and edge cases."
```

---

## 5. Use Case Breakdown

### 5.1 Banking Onboarding
- Guides user through KYC process
- Explains account types (Savings, Current, NRI)
- Verifies documents via screen share
- Detects frustration if user is stuck
- Emotion-aware pacing (slows down if confused)

### 5.2 Personal Finance Consultation
- Income → Expense analysis from user description
- Budgeting recommendations
- Emergency fund calculation
- Insurance coverage check
- **Detects**: anxiety about money → reassures, asks deeper questions

### 5.3 Loan Advisory
- Eligibility check (income, CIBIL score bracket)
- Loan type recommendation (personal vs gold vs PL vs home)
- EMI calculation with visualization
- **Detects**: stress when discussing debt → adjusts tone, offers alternatives

### 5.4 Wealth Management
- Portfolio review (user describes holdings)
- Asset allocation suggestions
- Rebalancing recommendations
- Risk profile assessment
- **Detects**: overconfidence → cautions, fear → educates

### 5.5 Customer Support Replacement
- Lost card → immediate block + reissue
- Transaction dispute → guided process
- Account statement request
- **Detects**: anger → empathy first, then resolve

### 5.6 Insurance Advisory
- Need analysis (life vs health vs term vs ULIP)
- Premium calculation
- Claim assistance
- **Detects**: confusion about terms → explains in simple language

### 5.7 Elder-Friendly Finance Assistant
- Large text, slower speech
- Hindi/English mix (Hinglish) support
- Pension/retirement focused
- **Detects**: hearing difficulty → repeats louder/slower

---

## 6. Implementation Roadmap

### Phase 1 (Weeks 1-4) — Local MVP

**Week 1 — Skeleton + Video Capture**
```
- Set up Python project, virtual env, pyproject.toml
- OpenCV webcam capture loop
- MediaPipe face mesh + pose tracking (display landmarks)
- Basic emotion detection with DeepFace (every 30 frames)
- Debug overlay: bounding box, emotion label, FPS
```

**Week 2 — Audio Pipeline**
```
- PyAudio loopback/mic capture
- Silero VAD integration (speech segments)
- faster-whisper integration (transcribe on speech end)
- Queue system: audio chunks → VAD → transcription
- Test: speak → see text on screen
```

**Week 3 — LLM + RAG**
```
- Ollama + Llama 3.1 8B setup
- LangChain RAG pipeline
- Scrape 10-20 RBI/SEBI PDFs → chunk → embed → ChromaDB
- Basic Q&A: user asks finance question → bot answers
- Conversation memory (last 10 exchanges)
```

**Week 4 — TTS + Integration**
```
- Edge TTS integration
- Fusion module: combine text + emotion into prompts
- Full pipeline: mic → STT → LLM+RAG+Emotion → TTS → speaker
- Streamlit or Tkinter UI (video feed + transcript + emotion)
- Test with 5-10 real finance questions
```

### Phase 2 (Weeks 5-8) — Polish + Features

```
- Gesture detection (nodding, shaking head, hand raise)
- Gaze tracking (looking at screen/camera vs away)
- Better emotion detection (custom classifier on MediaPipe landmarks)
- Mute/Interruption handling (user cuts off → adjust)
- Multi-language support (Hindi + Hinglish)
- Coqui XTTSv2 for custom synthesized voice
- Finance-specific prompt templates per use case
- Confidence scoring on retrieved chunks
```

### Phase 3 (Weeks 9-12) — Production Hardening

```
- Async architecture (FastAPI + WebSockets)
- Real-time with low-latency streaming
- User identification + persistent memory (Mem0/Zep)
- Session recording + audit logs (regulatory)
- A/B testing framework for responses
- Cost optimization (cache frequent questions, batch embeddings)
- Compliance guardrails (can't give stock tips, must disclaim)
- Fallback: "I'm not sure, consult a SEBI-registered advisor"
```

### Phase 4 (Future) — WebRTC / Video Call Integration

```
- Daily.co / LiveKit / Agora SDK for video calls
- WebRTC for browser-based client
- Live transcript overlay for human agent assist
- Meeting scheduling + calendar integration
- Screen share analysis (user shows Excel sheet → OCR → analyze)
- Multiple users in frame (detect who's speaking via lip movement)
```

---

## 7. Known Challenges & Risks

### Technical Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Latency > 3 seconds** | Unnatural conversation | Use streaming TTS + speculative decoding, quantize models |
| **Whisper hallucination** | Wrong transcription → wrong answer | Use VAD to segment properly, confidence thresholds |
| **Emotion false positives** | Awkward responses | Smooth emotions over window, don't react to single frames |
| **MacBook thermal throttling** | Dropped frames, audio glitches | Run models sequentially, use MPS, monitor temps |
| **Finance advice liability** | Legal risk | Hardcoded disclaimers, never guarantee returns |
| **Hindi/English code-switching** | Mixed-language queries | Use multilingual models (Whisper large-v3, Llama 3 supports Hinglish) |
| **"I don't know" vs hallucination** | Wrong financial advice | RAG confidence threshold, "I'm not sure" fallback |
| **Audio echo** | Bot hears itself | Echo cancellation (WebRTC AEC or RNNoise) |

### Emotion Detection Limitations

- **FER accuracy is ~60-65%** on real-world video (lab datasets are staged)
- **Don't rely on emotion alone** — use it as a signal, not a command
- **Combine signals:** emotion + tone (prosody) + speech rate + content
- **Cultural differences:** Indian expressions ≠ Western datasets. Indian head wobble, for example, means agreement but models may misclassify
- **Solution:** Collect your own dataset or fine-tune on Indian faces

### Regulatory Risks (India-specific)

- **SEBI (Investment Advisers) Regulations, 2013** — giving personalized advice without registration is illegal
- **RBI KYC guidelines** — cannot onboard users without proper verification
- **Data protection** — facial data is biometric, falls under DPDP Act 2023
- **Mitigations:**
  - Never give specific stock/timing recommendations
  - Use disclaimers: "This is for educational purposes only"
  - Display "Talk to a SEBI-registered advisor" for personalized advice
  - Don't store video, store only emotion vectors (no raw biometrics)

---

## 8. Ways to Make It Better

### 8.1 Hybrid Voice Pipeline
Use **Streaming TTS** (play while generating) instead of block-based.  
`elevenlabs` streaming or `coqui` with `stream_chunks` for sub-second time-to-first-audio.

### 8.2 Finance-Specific Fine-Tuning
Fine-tune Llama 3 8B on a curated dataset of:
- 10k Indian finance QA pairs
- 5k bank product explanations
- 2k regulatory FAQ entries
- Use LoRA for efficient fine-tuning (~$50 on RunPod)

### 8.3 Graph-Based Knowledge
Instead of flat RAG, build a **Finance Knowledge Graph** in Neo4j:
```
(User) ──[HAS_GOAL]──► (Goal: Retirement)
   │                       │
   ├──[HAS_PRODUCT]──► (PPF) ◄──[BELONGS_TO]── (Category: Debt)
   │                       │
   └──[ASKED_ABOUT]──► (Question) ──[ANSWERED_BY]──► (Response)
```
Enables multi-hop reasoning: "What debt products are good for retirement with tax benefits?"

### 8.4 Real-Time Dashboard Overlay
Overlay on the user's screen during video calls:
- Current emotion (subtle indicator)
- Key financial numbers mentioned
- Product recommendations
- Risk score
- Conversation summary

### 8.5 Proactive Suggestions
Don't just answer — anticipate:
- User mentions "30 years old" → proactively ask about retirement
- User seems confused (emotion + long pause) → "Would you like me to explain that differently?"
- User mentions "loan" → check eligibility, suggest pre-approved offers

### 8.6 Human Handoff
When the AI can't handle it (regulatory, complex, or user frustrated):
```
Bot: "This involves personalized advice. I'll connect you with 
a certified advisor. One moment please..."
→ Routes to human agent with full conversation + emotion history
```

### 8.7 Multilingual from Day 1
- Whisper supports 99 languages
- Llama 3 has decent Hindi/Hinglish
- Prioritize: English → Hindi → Tamil → Telugu → Bengali → Marathi
- Use language detection + route to appropriate RAG docs

### 8.8 Voice Cloning for Brand Voice
- Record a 30-second sample of an advisor's voice
- Use Coqui XTTSv2 to clone it
- The bot sounds like a real person from the bank/fintech

---

## Appendix A: Project Structure (Phase 1)

```
finance-advisor/
├── main.py                 # Entry point
├── pyproject.toml          # Dependencies
├── config.yaml             # Model paths, API keys
│
├── src/
│   ├── __init__.py
│   ├── video/
│   │   ├── capture.py      # OpenCV webcam
│   │   ├── face.py         # MediaPipe face mesh
│   │   ├── emotion.py      # DeepFace emotion
│   │   ├── pose.py         # MediaPipe pose/hands
│   │   └── gaze.py         # Gaze estimation
│   │
│   ├── audio/
│   │   ├── capture.py      # PyAudio mic input
│   │   ├── vad.py          # Silero VAD
│   │   ├── stt.py          # faster-whisper
│   │   └── tts.py          # Edge TTS / Coqui
│   │
│   ├── llm/
│   │   ├── engine.py       # Ollama / LangChain wrapper
│   │   ├── rag.py          # RAG retrieval pipeline
│   │   └── prompts.py      # Finance prompt templates
│   │
│   ├── memory/
│   │   ├── short_term.py   # In-memory conversation
│   │   ├── long_term.py    # Vector store (ChromaDB)
│   │   └── session.py      # Session management
│   │
│   ├── fusion/
│   │   └── fusion.py       # Combine text + emotion → prompt
│   │
│   └── ui/
│       └── streamlit_app.py # or  tkinter_app.py
│
├── data/
│   ├── knowledge/          # Finance PDFs, markdown docs
│   ├── chroma_db/          # Vector store (auto-created)
│   └── sessions/           # Session logs
│
├── models/                 # Downloaded model weights
│   └── .gitkeep
│
└── tests/
    ├── test_stt.py
    ├── test_emotion.py
    └── test_rag.py
```

## Appendix B: Quick Start Dependencies

```toml
# pyproject.toml
[project]
name = "finance-advisor"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    # Video
    "opencv-python>=4.9",
    "mediapipe>=0.10",
    "deepface>=0.0.79",
    
    # Audio
    "pyaudio>=0.2",
    "silero-vad>=0.2",
    "faster-whisper>=1.0",
    "edge-tts>=6.0",
    
    # LLM
    "langchain>=0.2",
    "langchain-community>=0.2",
    "chromadb>=0.5",
    "sentence-transformers>=2.2",
    
    # Memory
    "mem0>=0.1",
    
    # Utils
    "numpy>=1.26",
    "firecrawl-py>=0.0",
    "rich>=13.0",  # better logging
]
```

## Appendix C: Why These Model Choices

| Decision | Chosen | Alternatives Considered | Why This Won |
|----------|--------|------------------------|--------------|
| STT | faster-whisper large-v3 | Whisper.cpp, Deepgram API | Best accuracy/speed on M-series Mac, free local |
| TTS | Edge TTS → Coqui XTTSv2 | ElevenLabs, Piper, Bark | Free, good quality, 100+ voices, no GPU needed initially |
| LLM | Llama 3.1 8B via Ollama | Mistral 7B, Qwen 2.5, Phi-3 | Best general knowledge, strong instruction following, Indian finance knowledge |
| Embeddings | BGE-small-en-v1.5 | ADA-002, Instructor-XL | 384 dim = fast + cheap, runs locally, good retrieval |
| Vector DB | ChromaDB → Qdrant | Pinecone, Weaviate, FAISS | Zero setup, file-based, migrate when scaling |
| Face | MediaPipe | OpenCV Haar, Dlib, retinaface | Cross-platform, fast, 468 landmarks, includes iris |
| Emotion | DeepFace | FER, custom CNN | 6 models ensembled, 7 emotions, zero-shot |
| VAD | Silero VAD | WebRTC VAD, PyAnnote | Best open-source, < 1% false positive |
| Memory | Mem0 → LangGraph | Zep, custom SQL | Purpose-built for agents, auto-summarization |

---

> **Bottom Line:** Phase 1 is totally doable in 3-4 weeks with open-source tools on a MacBook. The hardest parts are (1) keeping latency under 2-3s end-to-end, (2) getting emotion detection accurate enough to be useful, and (3) ensuring financial advice is accurate + legally safe. Start with text-only Q&A (voice in/voice out), add vision after that pipeline is solid.
