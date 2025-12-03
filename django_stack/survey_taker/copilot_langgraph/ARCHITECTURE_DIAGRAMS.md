# LangGraph Interview Agent - Architecture Diagrams

## 📊 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Django View Layer                        │
│  process_response() in views.py (lines 97-112 replaced)     │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│            django_interview_handler()                        │
│  • Retrieves session state from Django session              │
│  • Calls process_interview_message()                        │
│  • Stores updated state back to session                     │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│         process_interview_message()                          │
│  • Initializes or resumes InterviewState                    │
│  • Invokes LangGraph workflow                               │
│  • Returns response + updated state                         │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                  LangGraph State Graph                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  [check_termination] ─→ If terminated → END         │   │
│  │         ↓                                            │   │
│  │  [moderate_answer] ─→ If flagged → warning/END      │   │
│  │         ↓                                            │   │
│  │  [add_user_message]                                  │   │
│  │         ↓                                            │   │
│  │  Decision Point:                                     │   │
│  │    ├─→ [probe_within_topic]                         │   │
│  │    ├─→ [transition_topic] + summary                 │   │
│  │    └─→ [closing_question]                           │   │
│  │         ↓                                            │   │
│  │  [moderate_question]                                 │   │
│  │         ↓                                            │   │
│  │  [add_question_to_history]                          │   │
│  │         ↓                                            │   │
│  │       END                                            │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                 LangSmith Tracing                            │
│  • Traces all node executions                               │
│  • Captures LLM prompts & responses                         │
│  • Records token usage & latency                            │
│  • Available at https://smith.langchain.com/                │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 State Flow Diagram

```
User sends message
    │
    ▼
┌───────────────────────────┐
│  Django receives POST     │
│  /process_response/       │
└───────────┬───────────────┘
            │
            ▼
┌───────────────────────────┐
│  Get session_state from   │
│  request.session          │
│  (None if first message)  │
└───────────┬───────────────┘
            │
            ▼
┌───────────────────────────┐
│  Initialize/Resume        │
│  InterviewState           │
│  • session_id             │
│  • messages history       │
│  • topic/question indices │
│  • summary                │
│  • parameters             │
└───────────┬───────────────┘
            │
            ▼
┌───────────────────────────┐
│  Execute Graph Nodes      │
│  (see detailed flow below)│
└───────────┬───────────────┘
            │
            ▼
┌───────────────────────────┐
│  Extract results:         │
│  • next_question          │
│  • updated state          │
│  • terminated flag        │
└───────────┬───────────────┘
            │
            ▼
┌───────────────────────────┐
│  Save updated state to    │
│  request.session          │
└───────────┬───────────────┘
            │
            ▼
┌───────────────────────────┐
│  Return JSON response     │
│  to frontend              │
└───────────────────────────┘
```

---

## 🎯 Detailed Node Flow

```
START (User message received)
  │
  ▼
┌─────────────────────────┐
│  [check_termination]    │  ← Traceable
│  Is interview already   │
│  terminated?            │
└──────┬──────────┬───────┘
       │          │
    YES│          │NO
       │          │
       ▼          ▼
      END   ┌─────────────────────────┐
            │  [moderate_answer]      │  ← Traceable (LLM call)
            │  Check if user message  │
            │  is appropriate         │
            └──────┬─────────┬────────┘
                   │         │
             FLAGGED│         │PASSED
                   │         │
                   ▼         ▼
            ┌──────────┐  ┌─────────────────────────┐
            │Too many? │  │ [add_user_message]      │  ← Traceable
            └────┬───┬─┘  │ Add to messages history │
                 │   │    └──────────┬──────────────┘
              YES│   │NO             │
                 │   │               │
                 ▼   ▼               ▼
                END  Return      ┌─────────────────────────┐
                    warning      │  Decision: What next?   │
                                 │  Based on topic_idx &   │
                                 │  question_idx           │
                                 └──┬──────┬──────┬────────┘
                                    │      │      │
                    ┌───────────────┘      │      └─────────────┐
                    │                      │                    │
                    ▼                      ▼                    ▼
       ┌─────────────────────┐  ┌──────────────────┐  ┌─────────────────┐
       │[probe_within_topic] │  │[transition_topic]│  │[closing_question]│
       │Generate probe Q     │  │Move to next topic│  │Get closing Q    │
       │for current topic    │  │+ generate summary│  │or end interview │
       └──────────┬──────────┘  └────────┬─────────┘  └────────┬────────┘
                  │                      │                     │
                  │  ← Traceable        │  ← Traceable        │  ← Traceable
                  │     (LLM call)       │     (2 LLM calls)   │     (no LLM)
                  │                      │                     │
                  └──────────┬───────────┴─────────────────────┘
                             │
                             ▼
                  ┌─────────────────────────┐
                  │ [moderate_question]     │  ← Traceable
                  │ Check if generated Q    │     (API call)
                  │ passes moderation       │
                  └──────────┬──────────────┘
                             │
                             ▼
                  ┌─────────────────────────┐
                  │[add_question_to_history]│  ← Traceable
                  │ Add Q to messages       │
                  └──────────┬──────────────┘
                             │
                             ▼
                            END
                             │
                             ▼
                   Return to Django view
```

---

## 🔍 Conditional Routing Logic

```
┌─────────────────────────────────────────────────────────┐
│              determine_next_action()                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  current_topic_idx = state['topic_idx']                 │
│  current_question_idx = state['question_idx']           │
│  num_topics = len(interview_plan)                       │
│  num_questions = interview_plan[topic_idx]['length']    │
│                                                          │
│  ┌─────────────────────────────────────────┐            │
│  │ IF on_last_topic AND on_last_question:  │            │
│  │    → "closing"                           │            │
│  └─────────────────────────────────────────┘            │
│                                                          │
│  ┌─────────────────────────────────────────┐            │
│  │ ELIF on_last_question (but not topic):  │            │
│  │    → "transition"                        │            │
│  └─────────────────────────────────────────┘            │
│                                                          │
│  ┌─────────────────────────────────────────┐            │
│  │ ELSE:                                    │            │
│  │    → "probe"                             │            │
│  └─────────────────────────────────────────┘            │
│                                                          │
│  Special case:                                           │
│  ┌─────────────────────────────────────────┐            │
│  │ IF finish_idx > len(closing_questions): │            │
│  │    → "end"                               │            │
│  └─────────────────────────────────────────┘            │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 📦 State Structure

```
InterviewState (TypedDict)
├── session_id: str
├── respondent_id: str
├── messages: List[Dict]  ← Annotated with operator.add
│   ├── message_1
│   │   ├── type: "question" | "answer"
│   │   ├── content: str
│   │   ├── topic_idx: int
│   │   ├── question_idx: int
│   │   └── timestamp: str
│   ├── message_2
│   └── ...
├── topic_idx: int  ← Current topic (1-indexed)
├── question_idx: int  ← Current question within topic
├── finish_idx: int  ← Index in closing_questions
├── flagged_messages: int  ← Count of moderation flags
├── terminated: bool  ← Interview ended?
├── summary: str  ← Running summary of prior topics
├── current_user_message: str  ← Latest user input
├── parameters: dict  ← From TEST_PARAMS
│   ├── first_question: str
│   ├── interview_plan: List[Dict]
│   ├── closing_questions: List[str]
│   ├── moderate_answers: bool
│   ├── moderate_questions: bool
│   ├── summarize: bool
│   ├── max_flags_allowed: int
│   ├── summary: {prompt, model, max_tokens}
│   ├── transition: {prompt, model, temperature, max_tokens}
│   ├── probe: {prompt, model, temperature, max_tokens}
│   └── moderator: {prompt, model, max_tokens}
├── next_question: str  ← Generated question to return
├── should_moderate: bool  ← Flag for moderation
└── moderation_passed: bool  ← Result of moderation
```

---

## 🔗 Django Session Integration

```
┌──────────────────────────────────────────────────────┐
│                  Django Request                       │
│  Contains: request.session (SessionStore)            │
└──────────────────┬───────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────┐
│  Session Key: f"interview_state_{respondent_id}"     │
├──────────────────────────────────────────────────────┤
│  Value: InterviewState dict (pickled)                │
│  ┌────────────────────────────────────────────┐     │
│  │ {                                           │     │
│  │   "session_id": "resp-123",                │     │
│  │   "messages": [...],                       │     │
│  │   "topic_idx": 2,                          │     │
│  │   "question_idx": 3,                       │     │
│  │   ...                                      │     │
│  │ }                                           │     │
│  └────────────────────────────────────────────┘     │
└──────────────────┬───────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────┐
│  Storage Backend (configurable)                      │
│  ├─ Database (default): django_session table         │
│  ├─ Cache: Redis/Memcached                           │
│  ├─ File: Session files on disk                      │
│  └─ Cookie: Encrypted cookie (not recommended)       │
└──────────────────────────────────────────────────────┘
```

---

## 🎨 LangSmith Trace View

```
Trace: process_interview_message
├── Input: {user_message, params_dict, respondent_id}
├── Duration: 1.8s
├── Tokens: 1,250
├── Cost: $0.015
│
├─┬─ [check_termination]
│ ├── Input: InterviewState
│ ├── Output: InterviewState (unchanged)
│ └── Duration: 0.001s
│
├─┬─ [moderate_answer]
│ ├── Input: InterviewState
│ ├─┬─ ChatOpenAI (gpt-4o-mini)
│ │ ├── Prompt: "You are monitoring..."
│ │ ├── Response: "yes"
│ │ ├── Tokens: 120
│ │ └── Duration: 0.3s
│ ├── Output: InterviewState (moderation_passed=True)
│ └── Duration: 0.32s
│
├─┬─ [add_user_message]
│ ├── Input: InterviewState
│ ├── Output: InterviewState (messages + 1)
│ └── Duration: 0.001s
│
├─┬─ [probe_within_topic]
│ ├── Input: InterviewState
│ ├─┬─ ChatOpenAI (gpt-4o)
│ │ ├── Prompt: "You're an AI proficient..."
│ │ ├── Response: "Can you tell me more about..."
│ │ ├── Tokens: 850
│ │ └── Duration: 1.2s
│ ├── Output: InterviewState (next_question set)
│ └── Duration: 1.25s
│
├─┬─ [moderate_question]
│ ├── Input: InterviewState
│ ├─┬─ OpenAI Moderation API
│ │ ├── Input: "Can you tell me more..."
│ │ ├── Result: {flagged: false}
│ │ └── Duration: 0.15s
│ ├── Output: InterviewState (unchanged)
│ └── Duration: 0.16s
│
├─┬─ [add_question_to_history]
│ ├── Input: InterviewState
│ ├── Output: InterviewState (messages + 1)
│ └── Duration: 0.001s
│
└── Final Output: {message, session_state, terminated}
```

---

## 🆚 Comparison: Before vs After

### Before (Flask + Procedural)
```
logic.py (162 lines)
├── next_question()
│   ├── resume_interview_session()
│   │   └── InterviewManager.resume_session()
│   │       └── DynamoDB.load_remote_session()  ← DB read
│   ├── LLMAgent.review_answer()  ← LLM call
│   ├── InterviewManager.add_chat_to_session()
│   │   └── DynamoDB.update_remote_session()  ← DB write
│   ├── if/elif/else logic for routing
│   ├── LLMAgent.probe_within_topic()  ← LLM call
│   ├── LLMAgent.transition_topic()  ← 2 LLM calls
│   ├── LLMAgent.review_question()  ← API call
│   ├── InterviewManager.add_chat_to_session()
│   │   └── DynamoDB.update_remote_session()  ← DB write
│   └── return response

Total DB calls: 3 per message
Total LLM calls: 2-4 depending on path
Observability: logger.info() statements
Testing: Mock database, complex setup
```

### After (LangGraph)
```
langgraph_interview.py (500 lines)
├── django_interview_handler()
│   ├── request.session.get()  ← Session read (in-memory/Redis)
│   ├── process_interview_message()
│   │   ├── build_interview_graph()
│   │   └── graph.invoke(state)
│   │       ├── check_termination  [traced]
│   │       ├── moderate_answer  [traced, LLM]
│   │       ├── add_user_message  [traced]
│   │       ├── probe/transition/closing  [traced, LLM]
│   │       ├── moderate_question  [traced, API]
│   │       └── add_question_to_history  [traced]
│   └── request.session[key] = state  ← Session write
│   └── return response

Total DB calls: 0 per message (session in cache)
Total LLM calls: 2-4 depending on path (same)
Observability: Full LangSmith trace tree
Testing: Test individual nodes, visual debugging
```

---

## 📊 Data Flow

```
HTTP Request
    ↓
Django View
    ↓
Session Store (read)
    ↓
LangGraph State Machine
    ↓ ← ← ← ← ← ← ← ← ←
    ↓                 ↑
    ↓              OpenAI
    ↓              API Calls
    ↓                 ↑
    ↓ → → → → → → → → ↑
    ↓
Session Store (write)
    ↓
HTTP Response (JSON)
    ↓
Frontend
```

---

## 🎯 Integration Points

```
Your Django App
├── views.py
│   └── process_response()
│       └── django_interview_handler()  ← Integration point
│           ├── From: copilot_langgraph/langgraph_interview.py
│           ├── Input: user_message, params_dict, respondent_id, request
│           └── Output: {message, terminated}
│
├── copilot_langgraph/
│   └── langgraph_interview.py  ← Uses TEST_PARAMS
├── testing_params.py
│   └── TEST_PARAMS  ← Used by langgraph_interview.py
│       └── No changes needed!
│
└── settings.py
    ├── SESSION_ENGINE  ← Configure session backend
    ├── SESSION_SERIALIZER  ← Use PickleSerializer
    └── Environment variables
        ├── OPENAI_API_KEY
        ├── LANGCHAIN_TRACING_V2
        ├── LANGCHAIN_API_KEY
        └── LANGCHAIN_PROJECT
```

---

**That's the complete architecture! 🎉**

For detailed setup instructions, see `SETUP_GUIDE.md`  
For implementation details, see `IMPLEMENTATION_SUMMARY.md`  
For quick reference, see `QUICK_REFERENCE.md`
