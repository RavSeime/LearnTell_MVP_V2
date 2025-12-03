# LangGraph Interview Agent - Setup & Configuration Guide

## Overview
This implementation converts the Flask-based interview agent to LangGraph with LangSmith tracking for use in Django.

## Key Changes from Original Implementation

### 1. **Architecture**
- **Before**: Procedural logic with manual state management
- **After**: Graph-based state machine with LangGraph

### 2. **State Management**
- **Before**: InterviewManager class with database writes after each interaction
- **After**: Immutable state graph with Django session storage

### 3. **Observability**
- **Before**: Basic logging
- **After**: LangSmith tracing for all LLM calls and agent decisions

### 4. **Modularity**
- **Before**: Monolithic functions
- **After**: Individual nodes for each agent action (probe, transition, moderate, etc.)

---

## Installation

### 1. Install Dependencies
```bash
cd survey_taker
pip install -r copilot_langgraph/langgraph_requirements.txt
```

### 2. Set Environment Variables
Add to your Django settings or `.env` file:

```bash
# Required
export OPENAI_API_KEY="your-openai-api-key"

# Optional: Enable LangSmith tracking
export LANGCHAIN_TRACING_V2="true"
export LANGCHAIN_API_KEY="your-langsmith-api-key"
export LANGCHAIN_PROJECT="interview-agent"
```

**LangSmith Setup:**
1. Sign up at https://smith.langchain.com/
2. Create a new project called "interview-agent"
3. Get your API key from Settings
4. Set the environment variables above

---

## Integration with Django

### Update views.py (Lines 97-112)

Replace the existing code with:

```python
from .copilot_langgraph.langgraph_interview import django_interview_handler

# Inside process_response function, replace lines 97-112:
result = django_interview_handler(
    user_message=user_message,
    params_dict=params_dict,
    respondent_id=respondent_id,
    request=request
)

return JsonResponse({
    'message': result['message'],
    'status': 'success',
    'respondent_id': respondent_id,
    'terminated': result.get('terminated', False)
})
```

See `views_integration_snippet.py` for the complete function.

---

## Parameter Changes in testing_params.py

### NO CHANGES REQUIRED to existing parameters!

The LangGraph implementation is fully compatible with your existing `TEST_PARAMS` structure. All fields work as-is:

- ✅ `first_question` - Used to initialize interviews
- ✅ `interview_plan` - Defines topic structure and question counts
- ✅ `closing_questions` - Closing questions array
- ✅ `moderate_answers` - Enables answer moderation
- ✅ `moderate_questions` - Enables question moderation
- ✅ `summarize` - Enables topic summarization
- ✅ `max_flags_allowed` - Flag threshold before termination
- ✅ All agent prompts (probe, transition, summary, moderator)
- ✅ All messages (termination, flagged, off_topic, end_of_interview)

### Optional: Add LangSmith Metadata (Recommended)

You can optionally add metadata for better LangSmith tracking:

```python
TEST_PARAMS = {
    "STOCK_MARKET": {
        # Existing parameters...
        
        # NEW: Optional LangSmith metadata
        "_langsmith": {
            "project": "interview-agent",
            "tags": ["stock-market", "qualitative-research"],
            "metadata": {
                "version": "1.0",
                "researcher": "your-name"
            }
        }
    }
}
```

---

## How It Works

### State Flow

```
User Message Input
    ↓
[check_termination] ─→ If terminated → END
    ↓
[moderate_answer] ─→ If flagged too often → END
    ↓               ─→ If flagged once → Return warning
    ↓
[add_user_message] ─→ Add to history
    ↓
Decision Point:
    ├─→ [probe_within_topic] (continue current topic)
    ├─→ [transition_topic] (move to next topic + summarize)
    ├─→ [closing_question] (interview ending)
    └─→ END (interview complete)
    ↓
[moderate_question] ─→ Check if generated Q is appropriate
    ↓
[add_question_to_history]
    ↓
END (return response)
```

### Session Management

- **Storage**: Django session framework (request.session)
- **Key**: `interview_state_{respondent_id}`
- **Contents**: Full InterviewState TypedDict including:
  - Conversation history
  - Topic/question indices
  - Summary
  - Moderation flags
  - Parameters

### LangSmith Tracking

Every function decorated with `@traceable` appears in LangSmith:

1. **process_interview_message** - Main entry point (run_type: "chain")
2. **check_termination** - Checks if already terminated
3. **moderate_answer** - LLM call to check answer appropriateness
4. **add_user_message** - Adds message to history
5. **probe_within_topic** - LLM call to generate probing question
6. **transition_topic** - LLM calls for transition + summary
7. **closing_question** - Gets closing questions
8. **moderate_question** - Moderation API call
9. **add_question_to_history** - Adds Q to history

View traces at: https://smith.langchain.com/

---

## Testing

### 1. Basic Test (No LangSmith)
```bash
# First install dependencies:
pip install -r copilot_langgraph/langgraph_requirements.txt

export OPENAI_API_KEY="your-key"
python manage.py runserver
```

Make POST request:
```bash
curl -X POST http://localhost:8000/survey/process_response/YOUR_SURVEY_ID/ \
  -H "Content-Type: application/json" \
  -d '{"user_message": "I dont trust the stock market", "respondent_id": "test-001"}'
```

### 2. Test with LangSmith Tracing
```bash
export OPENAI_API_KEY="your-key"
export LANGCHAIN_TRACING_V2="true"
export LANGCHAIN_API_KEY="your-langsmith-key"
export LANGCHAIN_PROJECT="interview-agent"
python manage.py runserver
```

Then check https://smith.langchain.com/ for traces.

---

## Debugging

### View LangSmith Traces
1. Go to https://smith.langchain.com/
2. Select "interview-agent" project
3. Click on any trace to see:
   - Input/output of each node
   - LLM prompts and responses
   - Execution time
   - Token usage
   - Error traces

### Common Issues

**Q: "ModuleNotFoundError: No module named 'langgraph'"**
A: Run `pip install -r langgraph_requirements.txt`

**Q: "Interview keeps returning first question"**
A: Check that Django sessions are enabled and working. Session state might not be persisting.

**Q: "LangSmith traces not appearing"**
A: Ensure all environment variables are set and you've created a project in LangSmith.

**Q: "OpenAI API errors"**
A: Check your API key and account has credits/quota remaining.

---

## Performance Considerations

### Compared to Original Implementation

**Advantages:**
- ✅ Better observability (LangSmith tracing)
- ✅ More maintainable (graph-based structure)
- ✅ Easier to extend (add new nodes)
- ✅ Type-safe state management (TypedDict)
- ✅ No database writes during conversation (uses Django session)

**Trade-offs:**
- ⚠️ Slightly higher memory usage (state stored in session)
- ⚠️ Session cleanup required for long-running servers
- ⚠️ Additional dependencies (LangChain, LangGraph)

### Optimization Tips

1. **Enable Redis for Django sessions** (recommended for production):
```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
```

2. **Set session timeouts**:
```python
# settings.py
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_SAVE_EVERY_REQUEST = False
```

3. **Clean up old sessions**:
```bash
python manage.py clearsessions
```

---

## Migration Path

### From Flask App to Django

If you're migrating conversations from the old Flask app:

1. **Export existing conversations** from DynamoDB/file storage
2. **Convert to new state format**:
```python
def convert_old_state_to_new(old_history, old_state):
    return InterviewState(
        session_id=old_state['session_id'],
        respondent_id=old_state['session_id'],
        messages=old_history,
        topic_idx=old_state['topic_idx'],
        question_idx=old_state['question_idx'],
        finish_idx=old_state['finish_idx'],
        flagged_messages=old_state['flagged_messages'],
        terminated=old_state['terminated'],
        summary=old_state['summary'],
        current_user_message="",
        parameters=PARAMS,
        next_question="",
        should_moderate=True,
        moderation_passed=True
    )
```

3. **Store in Django session or database**

---

## Next Steps

1. ✅ Install dependencies
2. ✅ Set environment variables
3. ✅ Update views.py with integration code
4. ✅ Test locally
5. ✅ Enable LangSmith tracking
6. ✅ Deploy to production
7. 📊 Monitor traces in LangSmith
8. 🎯 Optimize based on token usage and latency data

---

## Support & Resources

- **LangGraph Docs**: https://langchain-ai.github.io/langgraph/
- **LangSmith Docs**: https://docs.smith.langchain.com/
- **LangChain Docs**: https://python.langchain.com/docs/
- **Original Paper**: (reference your research paper)

---

## File Structure

```
survey_taker/
├── copilot_langgraph/
│   ├── langgraph_interview.py          # Main LangGraph implementation
│   ├── langgraph_requirements.txt      # New dependencies
│   ├── views_integration_snippet.py    # Integration code for views.py
│   ├── SETUP_GUIDE.md                  # This file
│   ├── IMPLEMENTATION_SUMMARY.md
│   ├── QUICK_REFERENCE.md
│   └── ARCHITECTURE_DIAGRAMS.md
└── testing_params.py               # No changes needed!
```
