# LangGraph Interview Agent - Quick Reference

## 🚀 5-Minute Setup

```bash
# 1. Install
pip install -r survey_taker/copilot_langgraph/langgraph_requirements.txt

# 2. Configure
export OPENAI_API_KEY="your-openai-key"
export LANGCHAIN_TRACING_V2="true"
export LANGCHAIN_API_KEY="your-langsmith-key"
export LANGCHAIN_PROJECT="interview-agent"

# 3. Update views.py (replace lines 97-112)
from .copilot_langgraph.langgraph_interview import django_interview_handler

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

# 4. Test
python manage.py runserver
# Make POST request to /survey/process_response/{survey_id}/

# 5. View traces
# Go to https://smith.langchain.com/
```

---

## 📁 Files Created

| File | Purpose | Size |
|------|---------|------|
| `copilot_langgraph/langgraph_interview.py` | Main implementation | ~500 lines |
| `copilot_langgraph/langgraph_requirements.txt` | Dependencies | 7 packages |
| `copilot_langgraph/views_integration_snippet.py` | Integration code | ~60 lines |
| `copilot_langgraph/SETUP_GUIDE.md` | Full documentation | Comprehensive |
| `copilot_langgraph/IMPLEMENTATION_SUMMARY.md` | Technical overview | Detailed |
| `copilot_langgraph/QUICK_REFERENCE.md` | This file | Quick ref |

---

## 🎯 Key Functions

### Main Entry Point
```python
process_interview_message(
    user_message: str,
    params_dict: dict,
    respondent_id: str,
    session_state: Optional[dict] = None
) -> dict
```
**Returns**: `{'message': str, 'session_state': dict, 'terminated': bool}`

### Django Wrapper
```python
django_interview_handler(
    user_message: str,
    params_dict: dict,
    respondent_id: str,
    request: HttpRequest
) -> dict
```
**Returns**: `{'message': str, 'terminated': bool}`
**Side Effect**: Stores state in `request.session`

---

## 🔍 LangGraph Nodes

| Node | Purpose | Traced |
|------|---------|--------|
| `check_termination` | Check if interview ended | ✅ |
| `moderate_answer` | Check answer appropriateness | ✅ |
| `add_user_message` | Add to history | ✅ |
| `probe_within_topic` | Generate probing Q | ✅ |
| `transition_topic` | Move to next topic + summarize | ✅ |
| `closing_question` | Get closing Q | ✅ |
| `moderate_question` | Check Q appropriateness | ✅ |
| `add_question_to_history` | Add Q to history | ✅ |

---

## 🔄 State Fields

```python
class InterviewState(TypedDict):
    # IDs
    session_id: str
    respondent_id: str
    
    # History
    messages: list  # Accumulated with operator.add
    
    # Progress
    topic_idx: int
    question_idx: int
    finish_idx: int
    flagged_messages: int
    terminated: bool
    
    # Context
    summary: str
    current_user_message: str
    parameters: dict
    
    # Output
    next_question: str
    should_moderate: bool
    moderation_passed: bool
```

---

## 📊 Message Format

```python
{
    'type': 'question' | 'answer',
    'content': str,
    'topic_idx': int,
    'question_idx': int,
    'timestamp': str
}
```

---

## 🎛️ Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `OPENAI_API_KEY` | ✅ Yes | OpenAI API access |
| `LANGCHAIN_TRACING_V2` | ⚠️ Recommended | Enable LangSmith |
| `LANGCHAIN_API_KEY` | ⚠️ Recommended | LangSmith API key |
| `LANGCHAIN_PROJECT` | ⚠️ Recommended | Project name |

---

## 🐛 Common Issues

| Problem | Solution |
|---------|----------|
| No traces in LangSmith | Check `LANGCHAIN_TRACING_V2="true"` |
| Repeating first question | Enable Django sessions |
| JSON serialization error | Use PickleSerializer |
| High latency | Check LangSmith traces, use Redis |
| Import errors | Install `langgraph_requirements.txt` |

---

## 📈 Performance Tips

```python
# 1. Use Redis for sessions (production)
# settings.py
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}

# 2. Set session timeout
SESSION_COOKIE_AGE = 3600  # 1 hour

# 3. Clean old sessions
python manage.py clearsessions  # Run weekly
```

---

## 🧪 Testing Commands

```bash
# Basic test
curl -X POST http://localhost:8000/survey/process_response/YOUR_ID/ \
  -H "Content-Type: application/json" \
  -d '{"user_message": "I dont trust stocks", "respondent_id": "test-001"}'

# Test continuation (same respondent_id)
curl -X POST http://localhost:8000/survey/process_response/YOUR_ID/ \
  -H "Content-Type: application/json" \
  -d '{"user_message": "They seem too risky", "respondent_id": "test-001"}'

# Test new interview (different respondent_id)
curl -X POST http://localhost:8000/survey/process_response/YOUR_ID/ \
  -H "Content-Type: application/json" \
  -d '{"user_message": "No experience", "respondent_id": "test-002"}'
```

---

## 📚 Quick Links

- **LangSmith Dashboard**: https://smith.langchain.com/
- **LangGraph Docs**: https://langchain-ai.github.io/langgraph/
- **LangChain Docs**: https://python.langchain.com/docs/
- **Setup Guide**: `SETUP_GUIDE.md`
- **Implementation Details**: `IMPLEMENTATION_SUMMARY.md`

---

## 🎓 Next Steps

1. ✅ Install dependencies
2. ✅ Set environment variables
3. ✅ Update views.py
4. ✅ Test locally
5. ✅ Enable LangSmith
6. 📊 Monitor traces
7. 🚀 Deploy to production

---

## ⚡ One-Liner Integration

Replace lines 97-112 in `views.py` with:

```python
from .copilot_langgraph.langgraph_interview import django_interview_handler
result = django_interview_handler(user_message, params_dict, respondent_id, request)
return JsonResponse({'message': result['message'], 'status': 'success', 'respondent_id': respondent_id, 'terminated': result['terminated']})
```

Done! 🎉

---

## 💡 Pro Tips

1. **Always check LangSmith first** when debugging
2. **Use Redis sessions** in production for better performance
3. **Set up alerts** in LangSmith for error rates
4. **Monitor token usage** to optimize costs
5. **Test with real users** before full deployment
6. **Keep backups** of session data
7. **Version your prompts** for A/B testing

---

## 📞 Support

- **Issues**: Check `SETUP_GUIDE.md` troubleshooting section
- **LangSmith**: https://docs.smith.langchain.com/
- **LangGraph**: https://github.com/langchain-ai/langgraph/discussions
- **Django Sessions**: https://docs.djangoproject.com/en/stable/topics/http/sessions/

---

**Version**: 1.0  
**Last Updated**: December 2025  
**Compatible with**: Django 3.x+, Python 3.8+, LangGraph 0.0.20+
