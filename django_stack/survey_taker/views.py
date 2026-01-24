from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from home.models import SurveyParams, SurveyResponse
import json
import uuid
import ast
import time
import os
from pathlib import Path
from dotenv import load_dotenv
#from .testing_params import TEST_PARAMS
from .self_eng_langgraph.multi_agent import get_response, test_create_agent

import importlib
from langchain.messages import HumanMessage
import threading
import logging

logger = logging.getLogger(__name__)

# Toggle debug timing
DEBUG_TIMING = True

# Load .env file explicitly
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(os.path.join(BASE_DIR, '.env'))

# Dictionary mapping key names to actual API keys
llm_key_dict = {
    "openai_api_key": os.getenv('OPENAI_API_KEY'),
    "anthropic_api_key": os.getenv('ANTHROPIC_API_KEY'),
    "google_api_key": os.getenv('GOOGLE_API_KEY'),
    "azure_openai_api_key": os.getenv('AZURE_OPENAI_API_KEY'),
    "meta_api_key": os.getenv('META_API_KEY'),
    "mistral_api_key": os.getenv('MISTRAL_API_KEY'),
    "cohere_api_key": os.getenv('COHERE_API_KEY'),
    "groq_api_key": os.getenv('GROQ_API_KEY'),
    "together_api_key": os.getenv('TOGETHER_API_KEY'),
    "fireworks_api_key": os.getenv('FIREWORKS_API_KEY'),
}

# Azure OpenAI endpoint (separate from key)
azure_openai_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')

# Log environment setup
logger.debug(".env loaded from: %s", os.path.join(BASE_DIR, '.env'))
logger.debug("OPENAI_API_KEY exists: %s", llm_key_dict["openai_api_key"] is not None)
if llm_key_dict["openai_api_key"]:
    logger.debug("API key starts with: %s...", llm_key_dict["openai_api_key"][:10])


# Function for importing graphs dynamically

#Note that we need to hardcode this in
GRAPH_MODULES = {
    "base_graph": "survey_taker.graphs.base_graph",
    "gatekeeper_engagement": "survey_taker.graphs.gatekeeper_engagement",
    "y": "survey_taker.graphs.y",
    "gatekeeper_engagement_validation": "survey_taker.graphs.gatekeeper_engagement_validation",
}

def load_graph(graph_key: str):
    module_path = GRAPH_MODULES.get(graph_key)
    if not module_path:
        raise ValueError(f"Unknown graph_key: {graph_key}")

    mod = importlib.import_module(module_path)
    return mod.build_graph()  # or getattr(mod, "GRAPH")

def get_session_key(survey_id, key_name):
    """Generate a namespaced session key for survey-specific data."""
    return f'survey_{survey_id}_{key_name}'

# In-memory graph cache (module-level)
_GRAPH_CACHE = {}

def get_graph_cached(graph_key):
    """
    Cache graphs in-memory for the process lifetime.
    LangGraph compiled graphs cannot be pickled for Django cache.
    """
    if graph_key not in _GRAPH_CACHE:
        _GRAPH_CACHE[graph_key] = load_graph(graph_key)
    return _GRAPH_CACHE[graph_key]

def warm_graph_cache_if_available(graph_key, params_dict):
    """Warm LLM cache if the graph module provides a warming function."""
    try:
        module_path = GRAPH_MODULES.get(graph_key)
        mod = importlib.import_module(module_path)
        if hasattr(mod, 'warm_llm_cache'):
            logger.info("Starting LLM cache warming for graph_key=%s", graph_key)
            mod.warm_llm_cache(params_dict)
            logger.info("LLM cache warming completed for graph_key=%s", graph_key)
    except Exception as e:
        logger.exception("Cache warming failed for graph_key=%s", graph_key)

def get_survey_params_cached(survey_id):
    """
    Get survey parameters with caching to reduce database queries.
    Cache is stored for 1 hour. Returns params_dict only.
    """
    cache_key = f'survey_params_{survey_id}'
    cached_data = cache.get(cache_key)
    
    if not cached_data:
        survey_params_obj = get_object_or_404(SurveyParams, survey_id=survey_id)
        # Parse params once and cache just the params dict
        cached_data = ast.literal_eval(survey_params_obj.params) if isinstance(survey_params_obj.params, str) else survey_params_obj.params
        cache.set(cache_key, cached_data, timeout=3600)  # Cache for 1 hour
    
    return cached_data

def tester(request, survey_id):
    survey_params_obj = get_object_or_404(SurveyParams, survey_id=survey_id)
    params_dict = get_survey_params_cached(survey_id)
    
    # Debug information
    debug_info = {
        'payload': survey_params_obj,
        'payload_type': type(survey_params_obj).__name__,
        'payload_dir': dir(survey_params_obj),
        'survey_id': survey_params_obj.survey_id,
        'survey_name': survey_params_obj.survey_name,
        'params': params_dict,
        'params_type': type(params_dict).__name__,
        'user': survey_params_obj.user,
        'created_at': survey_params_obj.created_at,
    }
    
    return render(request, "survey_taker/tester.html", {"debug_info": debug_info})


def survey_view(request, survey_id):
    """
    Renders the Survey.js interface for a specific survey.
    URL parameter: survey_id (UUID) - the primary key from SurveyParams table
    """
    # Get the survey parameters from the database (with caching)
    survey_params_obj = get_object_or_404(SurveyParams, survey_id=survey_id)
    
    # Render the survey template with the survey data
    context = {
        'survey_id': str(survey_id),
        'survey_name': survey_params_obj.survey_name,
    }
    return render(request, 'survey_taker/survey.html', context)



@csrf_exempt
def process_response(request, survey_id):
    """
    POST endpoint to process each participant response.
    This allows integration with custom LangGraph architecture.
    
    NOTE: No database writes happen here - conversation is stored in frontend
    and only saved when user completes the survey.
    
    Expected POST data:
    {
        "user_message": "participant's response",
        "respondent_id": "unique identifier for the respondent"
    }
    
    Returns:
    {
        "message": "AI's next question or response",
        "status": "success",
        "processing_time_ms": 123  # (if DEBUG_TIMING is True)
    }
    """
    # Start timing
    start_time = time.time() if DEBUG_TIMING else None

    
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    # Get the survey parameters (with caching) - params_dict is already parsed
    params_dict = get_survey_params_cached(survey_id)

    graph_key = params_dict.get("graph_config", "base_graph")

    graph = get_graph_cached(graph_key)

    try:
        logger.debug("Starting process_response for survey_id=%s", survey_id)

        # Parse the incoming JSON data
        data = json.loads(request.body)
        user_message = data.get('user_message', '')
        respondent_id = data.get('respondent_id', str(uuid.uuid4()))
        
        logger.debug("Respondent ID: %s", respondent_id)
        
        # Select API key based on params_dict configuration
        key_name = params_dict.get("api_key", "openai_api_key")  # Default to OpenAI
        selected_api_key = llm_key_dict.get(key_name)
        
        # Add selected API key to params_dict for graph nodes
        params_dict_with_key = params_dict.copy()
        params_dict_with_key["api_key"] = selected_api_key
        
        # Add Azure endpoint if using Azure OpenAI
        if key_name == "azure_openai_api_key":
            params_dict_with_key["azure_openai_endpoint"] = azure_openai_endpoint

        # After getting graph and params_dict
        cache_key = f'warmed_{graph_key}_{survey_id}'
        if not cache.get(cache_key):
            threading.Thread(
                target=warm_graph_cache_if_available,
                args=(graph_key, params_dict_with_key),
                daemon=True
            ).start()
            cache.set(cache_key, True, timeout=3600)

        logger.debug("Using thread_id (respondent_id): %s", respondent_id)
        graph_config = {"configurable": {"thread_id": respondent_id}}
        input_message = [HumanMessage(content = user_message)]
        result = graph.invoke({"messages": input_message, "params" : params_dict_with_key}, config=graph_config)
        
        next_question = result["messages"][-1].content
        
        # Extract progress bar from interview_meta if available
        progress_bar = result.get("interview_meta", {}).get("progress_bar_percent", 0)

        response_data = {
            'message': next_question,
            'status': 'success',
            'respondent_id': respondent_id,
            'progress_bar': progress_bar
        }
        
        if DEBUG_TIMING:
            processing_time_ms = round((time.time() - start_time) * 1000, 2)
            response_data['processing_time_ms'] = processing_time_ms
            logger.info("Request processed in %.2fms for respondent=%s", processing_time_ms, respondent_id)
        
        return JsonResponse(response_data)
        
    except json.JSONDecodeError as e:
        logger.error("JSON decode error in process_response: %s", e)
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.exception("Exception in process_response for survey_id=%s", survey_id)
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def complete_survey(request, survey_id):
    """
    POST endpoint to save the entire conversation when survey is completed.
    
    Expected POST data:
    {
        "respondent_id": "unique identifier for the respondent",
        "conversation": [
            {"order": 1, "message": "What's your name?", "is_question": true},
            {"order": 2, "message": "John", "is_question": false},
            ...
        ]
    }
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    survey_params_obj = get_object_or_404(SurveyParams, survey_id=survey_id)
    
    try:
        data = json.loads(request.body)
        respondent_id = data.get('respondent_id')
        conversation = data.get('conversation', [])
        
        # Save entire conversation as single database entry
        response_obj, created = SurveyResponse.objects.update_or_create(
            survey=survey_params_obj,
            respondent_id=respondent_id,
            defaults={'responses': {'conversation': conversation}}
        )
        
        # Clear survey-specific session data after successful save
        for key in ['conversation_log', 'current_topic_index', 'nr_questions_asked_current_topic', 
                    'closing_question_index', 'pre_generated_transition']:
            session_key = get_session_key(survey_id, key)
            request.session.pop(session_key, None)
        
        return JsonResponse({
            'status': 'success',
            'message': 'Conversation saved successfully',
            'respondent_id': respondent_id,
            'message_count': len(conversation)
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
