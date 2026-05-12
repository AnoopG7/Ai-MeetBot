# Agent Plan — Personal Finance Advisor

> The agent is the core of the system. It runs inside LiveKit Agents, owns the conversation, uses finance tools, and fuses vision + audio + context into every response.

---

## 1. Agent Architecture (LiveKit)

```
┌──────────────────────────────────────────────────────────────────┐
│                        LiveKit Server                            │
│  (WebRTC media routing, room management, token auth)             │
└──────────────────────────┬───────────────────────────────────────┘
                           │ WebRTC
┌──────────────────────────▼───────────────────────────────────────┐
│                    LiveKit Agent (Python)                         │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │  AgentSession                                            │     │
│  │  - manages the full conversation lifecycle               │     │
│  │  - connects VAD → STT → LLM → TTS pipeline              │     │
│  │  - handles interruptions, barge-in, state transitions    │     │
│  └──────────┬──────────┬──────────┬──────────┬──────────────┘     │
│             │          │          │          │                     │
│        ┌────▼───┐ ┌───▼────┐ ┌───▼───┐ ┌───▼────┐               │
│        │ VAD    │ │ STT    │ │ LLM   │ │ TTS    │               │
│        │ Silero │ │Whisper │ │Llama3 │ │EdgeTTS│               │
│        └────────┘ └────────┘ └───┬───┘ └────────┘               │
│                                  │                               │
│        ┌─────────────────────────▼──────────────────────────┐   │
│        │               Our Agent Logic                       │   │
│        │                                                     │   │
│        │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │   │
│        │  │ Finance  │  │ Memory   │  │ Vision Fuser     │  │   │
│        │  │ Tools    │  │ (Mem0)   │  │ (emotion → prompt)│  │   │
│        │  └──────────┘  └──────────┘  └──────────────────┘  │   │
│        │                                                     │   │
│        │  ┌──────────┐  ┌──────────┐                         │   │
│        │  │ RAG      │  │Compliance│                         │   │
│        │  │ (Qdrant) │  │Guardrails│                         │   │
│        │  └──────────┘  └──────────┘                         │   │
│        └─────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

**The key insight:** LiveKit Agents handles all the real-time audio plumbing (VAD → STT → LLM → TTS loop with barge-in). Our code lives inside the agent's tool definitions and the LLM prompt layer. We don't write the audio pipeline — we write the finance brain.

---

## 2. Agent Registration & Entrypoint

The agent registers with LiveKit Server and listens for incoming sessions:

```python
# agent.py — single file entrypoint
from livekit.agents import AgentSession, Agent, AutoSubscribe
from livekit.plugins import silero, deepgram, openai, cartesia

@agent_server.on("connect")
async def handle_connect(ctx):
    # 1. Create the session with LiveKit's built-in pipeline
    session = AgentSession(
        vad=silero.VAD(),                    # Voice Activity Detection
        stt=deepgram.STT(model="nova-3"),     # Speech-to-Text (or local Whisper)
        llm=openai.LLM(model="gpt-4o-mini"),  # Or Ollama for local Llama 3
        tts=cartesia.TTS(                     # Or Edge TTS / ElevenLabs
            model="sonic-2",
            voice="en-IN"
        ),
    )

    # 2. Define the agent with instructions + tools
    agent = Agent(
        instructions=PERSONAL_FINANCE_SYSTEM_PROMPT,
        tools=[
            lookup_finance_knowledge,     # RAG tool
            calculate_emi,                # Math tool
            get_product_info,             # Product DB tool
            assess_risk_profile,          # Risk assessment tool
            escalate_to_human,            # Escalation tool
        ],
    )

    # 3. Start the conversation
    await session.start(agent=agent, room=ctx.room)
    await ctx.wait_for_close()
```

**That's it.** LiveKit handles mic capture → VAD → chunk audio → send to STT → LLM with tools → TTS → play to speaker. We just plug in our instructions and tools.

---

## 3. System Prompt

The agent's persona. This is the most important piece — it defines *how* the agent behaves.

```python
PERSONAL_FINANCE_SYSTEM_PROMPT = """
You are a Personal Finance Advisor for Indian users. 
You speak in a calm, clear, professional tone.

## Your Identity
- You are NOT a SEBI-registered investment advisor
- You provide EDUCATIONAL information only
- You NEVER recommend specific stocks, timing, or guaranteed returns
- You ALWAYS add: "Consult a SEBI-registered advisor for personalized advice"

## Your Capabilities
- Answer questions about banking products (savings, FD, RD, NRI accounts)
- Explain mutual funds, PPF, NPS, ELSS, insurance types
- Help with loan eligibility, EMI calculation, CIBIL score improvement
- Guide through KYC and account opening processes
- Explain tax saving options under 80C, 80D, etc.
- Provide budgeting and personal finance management tips

## Your Knowledge Sources
Your answers should be grounded in:
- RBI regulations and master directions
- SEBI guidelines for investments
- IRDAI rules for insurance
- Income Tax Act provisions
- Standard banking product terms

## Conversation Style
- Start with a warm greeting and ask what they need help with
- Listen more than you talk — ask clarifying questions
- When the user seems confused (emotion signal), simplify your language
- Never use jargon without explaining it first
- If you don't know something, say "I don't have that information" — never make it up
- For personalized advice, always escalate: "This requires a certified advisor"

## Emotional Awareness
The system may pass emotional context about the user:
- confused → simplify, ask "Would you like me to explain differently?"
- frustrated → acknowledge, "I understand this can be frustrating..."
- anxious → reassure, "Take your time, let's go through this step by step"
- angry → stay calm, "I understand your concern, let me help resolve this"
- happy → maintain positive tone, "Great, I'm glad that helps!"

## Safety Rules
- NEVER predict stock prices or market movements
- NEVER guarantee returns on any investment
- NEVER share personal financial advice without disclaimer
- ALWAYS include disclaimer on any product recommendation
- If user asks for illegal advice (tax evasion, etc.), firmly decline
- If user seems distressed about money, offer to connect to a financial counselor
"""
```

---

## 4. Tool Definitions

Tools = functions the LLM can call when it needs to do something beyond text generation.

### 4.1 Finance RAG Tool

```python
@agent_tool
async def lookup_finance_knowledge(
    ctx: ToolContext,
    query: str
) -> list[dict]:
    """
    Search the finance knowledge base for relevant information.
    Use this when the user asks about regulations, products, or procedures.

    Args:
        query: The search query, e.g. "PPF interest rate 2025"
    """
    # 1. Embed the query
    query_embedding = embed(query)

    # 2. Hybrid search in Qdrant
    results = qdrant_client.search(
        collection_name="finance_knowledge",
        query_vector=query_embedding,
        query_filter=extract_metadata_filter(query),  # e.g. year, product, regulator
        limit=5,
    )

    # 3. Rerank with cross-encoder
    reranked = rerank(query, results)

    # 4. Format as context for LLM
    return [
        {
            "content": hit.payload["content"],
            "source": hit.payload["source"],
            "relevance": hit.score,
        }
        for hit in reranked
    ]
```

### 4.2 EMI Calculator Tool

```python
@agent_tool
async def calculate_emi(
    ctx: ToolContext,
    principal: float,
    annual_rate: float,
    tenure_months: int
) -> dict:
    """
    Calculate Equated Monthly Installment for a loan.

    Args:
        principal: Loan amount in INR
        annual_rate: Annual interest rate in percentage (e.g. 8.5 for 8.5%)
        tenure_months: Loan tenure in months
    """
    monthly_rate = annual_rate / 12 / 100
    emi = principal * monthly_rate * (1 + monthly_rate)**tenure_months / \
          ((1 + monthly_rate)**tenure_months - 1)
    total_payment = emi * tenure_months
    total_interest = total_payment - principal

    return {
        "emi": round(emi, 2),
        "total_interest": round(total_interest, 2),
        "total_payment": round(total_payment, 2),
        "principal": principal,
        "tenure_months": tenure_months,
        "annual_rate": annual_rate,
    }
```

### 4.3 Product Info Tool

```python
@agent_tool
async def get_product_info(
    ctx: ToolContext,
    product_type: str,
    bank_name: str = None
) -> dict:
    """
    Get current information about a financial product.

    Args:
        product_type: Type of product (savings_account, fixed_deposit, 
                      recurring_deposit, credit_card, home_loan, 
                      personal_loan, mutual_fund, ppf, nps, elss, insurance)
        bank_name: Optional bank name to filter
    """
    # Query product database for current rates and features
    products = product_db.query(
        product_type=product_type,
        bank=bank_name,
    )
    return {
        "products": products,
        "disclaimer": "Rates are indicative and subject to change. "
                      "Verify with the respective bank before applying."
    }
```

### 4.4 Risk Profile Assessment Tool

```python
@agent_tool
async def assess_risk_profile(
    ctx: ToolContext,
    age: int,
    annual_income: float,
    monthly_expenses: float,
    existing_savings: float,
    investment_horizon_years: int,
    financial_goals: list[str]
) -> dict:
    """
    Assess a user's risk profile based on their financial situation.

    This is EDUCATIONAL only. The user must consult a certified advisor.
    """
    # Simple heuristic-based assessment
    emergency_fund_months = existing_savings / (monthly_expenses or 1)
    disposable_income = annual_income / 12 - monthly_expenses

    if investment_horizon_years < 3:
        base_risk = "conservative"
    elif investment_horizon_years < 7:
        base_risk = "moderate"
    else:
        base_risk = "aggressive"

    # Adjust for age
    if age > 55:
        base_risk = "conservative"

    return {
        "suggested_profile": base_risk,
        "emergency_fund_months": round(emergency_fund_months, 1),
        "monthly_disposable_income": round(disposable_income, 2),
        "observations": [],
        "disclaimer": "This is a general assessment for educational purposes. "
                      "A SEBI-registered advisor should evaluate your complete "
                      "financial situation before making investment decisions."
    }
```

### 4.5 Human Escalation Tool

```python
@agent_tool
async def escalate_to_human(
    ctx: ToolContext,
    reason: str
) -> dict:
    """
    Escalate the conversation to a human advisor.
    Use when:
    - User asks for personalized investment advice
    - User is angry and requires human empathy
    - User's query is outside your knowledge scope
    - User explicitly requests a human
    """
    # Create escalation ticket
    ticket = escalation_queue.create(
        session_id=ctx.session.id,
        user_id=ctx.session.user_id,
        conversation_history=ctx.session.conversation,
        reason=reason,
        emotion_context=ctx.session.metadata.get("vision_context"),
    )

    return {
        "escalated": True,
        "ticket_id": ticket.id,
        "message": "I've connected you with a human advisor who will be with you shortly."
    }
```

---

## 5. Vision Fusion Pipeline

This runs as a separate process alongside the LiveKit agent, processing video frames and injecting emotion context into the LLM prompts.

```python
# vision_pipeline.py — separate async process

class VisionPipeline:
    """
    Receives video frames from LiveKit video track.
    Processes them for face/emotion/gaze.
    Stores results in shared context that the LLM prompt reads.
    """

    def __init__(self):
        self.face_mesh = mp.solutions.face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
        )
        self.emotion_model = EmotiEffLib()  # Lighter than DeepFace
        self.current_context = VisionContext()

    async def process_frame(self, frame: VideoFrame):
        """Called by LiveKit for each video frame."""
        rgb = frame.to_rgb()

        # Face mesh (every frame — fast)
        mesh = self.face_mesh.process(rgb)
        if not mesh.multi_face_landmarks:
            return

        # Emotion (every 15th frame — slower)
        if frame.timestamp % 15 == 0:
            emotion = self.emotion_model.predict(rgb)
            self.current_context.emotion = emotion.label
            self.current_context.emotion_confidence = emotion.confidence

        # Gaze (every 5th frame)
        if frame.timestamp % 5 == 0:
            gaze = estimate_gaze(mesh.multi_face_landmarks[0])
            self.current_context.gaze = gaze.direction

        # Engagement score
        self.current_context.engagement_score = compute_engagement(
            emotion=self.current_context.emotion,
            gaze=self.current_context.gaze,
            speaking=self.current_context.is_speaking,
        )
```

### Context Injection into LLM

The vision context gets injected into the LLM prompt before each turn:

```python
class FinanceAgent:
    async def on_before_llm(self, ctx):
        """Called by LiveKit before sending prompt to LLM."""

        vision = self.vision_pipeline.current_context
        memory = await self.memory.get_relevant(ctx.session.user_id)

        # Enrich the system prompt with current context
        ctx.system_prompt += f"""

## Current Context
User emotion: {vision.emotion} ({vision.emotion_confidence:.0%} confidence)
User gaze: {vision.gaze}
User engagement: {vision.engagement_score:.0%}
User head gesture: {vision.head_gesture}

## User Profile (from memory)
Risk profile: {memory.risk_profile}
Previously discussed: {memory.mentioned_products}
Financial goals: {memory.goals}
"""
```

---

## 6. Conversation State Machine

LiveKit's built-in, but worth understanding:

```
LISTENING ──► PROCESSING ──► SPEAKING ──► LISTENING
    │             │              │
    │             │              ├── user interrupts ──► LISTENING
    │             │              ├── done speaking ──► LISTENING
    │             │              └── silence > 30s ──► END
    │             │
    │             ├── LLM error ──► "Let me try again" ──► PROCESSING
    │             └── confidence < 0.4 ──► escalate ──► END
    │
    ├── silence > 5min ──► "Are you still there?" ──► LISTENING
    └── user says "bye" ──► END
```

| State | What Happens |
|-------|-------------|
| **LISTENING** | VAD active, collecting audio chunks. Mic light is on. |
| **PROCESSING** | VAD paused. STT transcribes. LLM thinks. RAG fetches. Tool runs. |
| **SPEAKING** | TTS playing. VAD still running (detect interruptions). |
| **INTERRUPTED** | User spoke while bot was talking. Stop TTS. Re-enter LISTENING. |

**Barge-in behavior:** If the user speaks while the bot is responding, LiveKit automatically stops TTS, notes the interruption in conversation history, and re-enters the LISTENING state. The LLM sees: `[User interrupted: "wait actually I meant something else"]`.

---

## 7. Memory System

### Short-Term (in-prompt)
- Last 10 conversation turns included in every LLM request
- Managed by LiveKit's `AgentSession` automatically

### Long-Term (Mem0)
Persisted across sessions. Stored in Mem0 with user_id key:

```python
class FinanceMemory(Mem0Memory):
    async def get_relevant(self, user_id: str) -> UserProfile:
        """Retrieve or create user profile from memory."""
        profile = await self.get(f"profile:{user_id}")
        if not profile:
            return UserProfile(
                risk_profile="unknown",
                mentioned_products=[],
                goals=[],
                age_group=None,
                session_count=0,
            )

        # Summarize and update
        recent_sessions = await self.search(
            f"user:{user_id}",
            limit=5,
        )
        profile.session_count += 1
        profile.last_active = datetime.now()
        return profile

    async def remember(self, user_id: str, turn: dict):
        """Store a conversation turn with extracted entities."""
        entities = extract_finance_entities(turn["text"])
        await self.add(
            f"session:{user_id}:{turn['session_id']}",
            {
                "query": turn["text"],
                "response": turn["response"],
                "emotion": turn.get("emotion"),
                "entities": entities,
                "timestamp": turn["timestamp"],
            },
            metadata={"user_id": user_id}
        )

        # Update user profile
        profile = await self.get_relevant(user_id)
        profile.mentioned_products.extend(
            entities.get("products", [])
        )
        if entities.get("goals"):
            profile.goals.extend(entities["goals"])
        await self.set(f"profile:{user_id}", profile)
```

### Session Audit Log (PostgreSQL)
Every turn is logged for compliance:

```sql
CREATE TABLE session_logs (
    id UUID PRIMARY KEY,
    user_id VARCHAR(64),
    session_id VARCHAR(64),
    turn_number INT,
    query TEXT,
    response TEXT,
    emotion VARCHAR(32),
    confidence FLOAT,
    retrieval_sources JSONB,
    latency_ms INT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 8. Compliance Layer

Every response passes through this before being spoken:

```python
class ComplianceGuard:
    RULES = [
        # Block specific stock recommendations
        Rule(r"(buy|sell|invest in)\s+(TCS|Reliance|HDFC|Infosys|ITC|SBI|Bajaj)\s+(stock|share|equity)", "Cannot recommend specific stocks"),

        # Block guaranteed returns
        Rule(r"(guaranteed|assured|certain)\s+(return|profit|gain)", "Cannot guarantee returns"),

        # Block market predictions
        Rule(r"(market will|market predicted|expected to go up|expected to rise|bullish|bearish)", "Cannot predict market movements"),

        # Require disclaimers
        Rule(None, "must_include_disclaimer"),  # Check after generation
    ]

    async def check(self, response: str, context: dict) -> str:
        """Return sanitized response or escalation message."""
        for rule in self.RULES:
            if rule.match(response):
                return self.create_compliant_response(rule.violation)

        if "Consult a SEBI-registered advisor" not in response:
            response += self.DISCLAIMER_SUFFIX

        return response
```

---

## 9. Data Flow — One Full Turn

```
User says: "What's the interest rate on PPF right now?"

1. VAD detects speech end
2. STT transcribes: "What's the interest rate on PPF right now?"
3. Vision pipeline snapshot: emotion=curious, gaze=looking_at_camera
4. Memory load: user hasn't asked about PPF before
5. Build enriched prompt:
   System: [finance advisor persona]
   Context: [RAG results about PPF rates, compliance rules]
   Vision: "The user looks curious and engaged"
   History: [last 0 turns — this is the first]
   Query: "What's the interest rate on PPF right now?"
6. LLM generates response with tool call:
   → lookup_finance_knowledge("PPF interest rate 2025")
   → Returns: "PPF current rate is 7.1% (Q1 FY2025-26), EEE status..."
7. LLM produces final answer:
   "As per the latest government notification, PPF currently offers 7.1% 
    per annum (compounded annually). It has an EEE status — exempt from 
    tax at investment, accrual, and withdrawal. Would you like me to 
    explain how PPF compares to EPF or NPS for retirement planning?
    
    [Disclaimer: Rates are subject to change. Consult a SEBI-registered 
     advisor for personalized investment advice.]"
8. Compliance check: contains disclaimer, no violations
9. TTS generates speech audio
10. LiveKit streams audio chunks to browser
11. Vision pipeline detects user nodding (agreement)
12. Memory stores: user asked about PPF, was interested in comparison
13. Turn logged to PostgreSQL audit table

Total latency target: < 3 seconds
```

---

## 10. Multi-Use Case Prompt Switching

The agent adjusts its persona based on context:

```python
USE_CASE_PROMPTS = {
    "banking_onboarding": """
        You are helping a user open a bank account or complete KYC.
        Guide them step by step through document requirements.
        Be patient — this process can be confusing.
        Detect if they have the required documents before proceeding.
    """,
    "personal_finance": """
        You are a personal finance educator.
        Help users understand budgeting, saving, and basic financial planning.
        Ask about their income, expenses, and goals before giving suggestions.
    """,
    "loan_advisory": """
        You are a loan information specialist.
        Explain different loan types, eligibility criteria, and documentation.
        Calculate EMIs when asked.
        Never guarantee loan approval — that depends on the bank's assessment.
    """,
    "wealth_management": """
        You are a wealth management educator.
        Discuss asset allocation, diversification, and long-term investing.
        Always emphasize that past performance doesn't guarantee future results.
    """,
    "insurance_advisory": """
        You are an insurance information specialist.
        Explain the difference between term, health, and ULIP plans.
        Help users assess their insurance needs based on dependents and liabilities.
    """,
    "elderly_support": """
        You are a patient and clear finance assistant for senior citizens.
        Speak slowly, use simple language, repeat important points.
        Focus on pension, senior savings schemes (SCSS), and medical insurance.
        Offer to explain things in Hindi if the user prefers.
    """,
}
```

The agent detects the use case from the user's first query and selects the appropriate prompt. Users can also switch contexts by saying "I need help with a loan" mid-conversation.

---

## 11. Agent File Structure

```
backend/src/advisor/agent/
├── __init__.py
├── main.py                 # Entrypoint — register agent, start session
├── prompts/
│   ├── system.py           # PERSONAL_FINANCE_SYSTEM_PROMPT
│   ├── use_cases.py        # USE_CASE_PROMPTS dictionary
│   └── compliance.py       # Compliance check rules
├── tools/
│   ├── __init__.py
│   ├── rag.py              # lookup_finance_knowledge
│   ├── calculator.py        # calculate_emi
│   ├── products.py          # get_product_info
│   ├── risk_profile.py      # assess_risk_profile
│   └── escalation.py        # escalate_to_human
├── memory/
│   ├── __init__.py
│   ├── short_term.py        # In-prompt conversation history
│   ├── long_term.py         # Mem0 integration
│   └── session_logger.py    # PostgreSQL audit logging
├── vision/
│   ├── pipeline.py          # VisionPipeline class
│   ├── emotion.py           # EmotiEffLib wrapper
│   ├── gaze.py              # Gaze estimation
│   └── gestures.py          # Head pose, nod/shake detection
├── fusion/
│   └── context.py           # Inject vision + memory into LLM prompt
└── config.py                # Agent config (voices, models, thresholds)
```

---

## 12. Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Agent framework | LiveKit Agents | Handles all audio plumbing, VAD, barge-in, WebRTC |
| STT integration | LiveKit plugin (Whisper or Deepgram) | Zero code — just config |
| TTS integration | LiveKit plugin (Edge TTS or Cartesia) | Zero code — just config |
| LLM integration | LiveKit plugin (Ollama or OpenAI) | Zero code — just config |
| Tool execution | LiveKit ToolContext | Built-in tool calling with JSON schema |
| Vision pipeline | Separate async process | Non-blocking, doesn't slow down audio/LLM |
| Vision → LLM bridge | Enriched system prompt | Simplest integration, no custom code needed |
| Memory | Mem0 | Auto-summarization, entity extraction, importance scoring |
| Audit logs | PostgreSQL | Immutable, queryable, compliance-ready |
| Compliance | Post-generation check | Cannot rely on LLM alone to follow rules |
