# Copilot LangGraph Interview Agent

This folder contains a complete LangGraph implementation of the interview agent with LangSmith tracking capabilities.

## 📁 Files

- **langgraph_interview.py** - Main LangGraph implementation (~500 lines)
- **langgraph_requirements.txt** - Required dependencies
- **views_integration_snippet.py** - Code to replace lines 97-112 in views.py
- **SETUP_GUIDE.md** - Complete setup and installation guide
- **IMPLEMENTATION_SUMMARY.md** - Technical deep dive and architecture details
- **QUICK_REFERENCE.md** - Quick reference card with common commands
- **ARCHITECTURE_DIAGRAMS.md** - Visual flow diagrams and architecture
- **README.md** - This file

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r copilot_langgraph/langgraph_requirements.txt
```

### 2. Set Environment Variables
```bash
export OPENAI_API_KEY="your-openai-key"
export LANGCHAIN_TRACING_V2="true"
export LANGCHAIN_API_KEY="your-langsmith-key"
export LANGCHAIN_PROJECT="interview-agent"
```

### 3. Update views.py (Lines 97-112)
```python
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
```

## 📚 Documentation

- Start with **SETUP_GUIDE.md** for installation
- Read **QUICK_REFERENCE.md** for common commands
- Check **ARCHITECTURE_DIAGRAMS.md** for visual flow
- Dive into **IMPLEMENTATION_SUMMARY.md** for technical details

## ✅ No Parameter Changes Required

Your existing `testing_params.py` works as-is. No modifications needed!

## 🎯 Key Features

- ✅ LangGraph state machine architecture
- ✅ Full LangSmith tracing
- ✅ Django session integration
- ✅ Type-safe with TypedDict
- ✅ Modular node-based design
- ✅ 100% compatible with existing parameters

## 📞 Support

- **Issues**: Check SETUP_GUIDE.md troubleshooting section
- **LangSmith**: https://smith.langchain.com/
- **LangGraph Docs**: https://langchain-ai.github.io/langgraph/
