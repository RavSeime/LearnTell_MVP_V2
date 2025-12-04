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
from .testing_params import TEST_PARAMS
from .self_eng_langgraph.multi_agent import get_response, test_create_agent

# Toggle debug timing
DEBUG_TIMING = True

# Load .env file explicitly
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(os.path.join(BASE_DIR, '.env'))

# Get api key
api_key = os.getenv('OPENAI_API_KEY')

# === DEBUG START ===
print(f"[DEBUG] .env loaded from: {os.path.join(BASE_DIR, '.env')}")
print(f"[DEBUG] OPENAI_API_KEY exists: {api_key is not None}")
if api_key:
    print(f"[DEBUG] API key starts with: {api_key[:10]}...")
# === DEBUG END ===



def get_survey_params_cached(survey_id):
    """
    Get survey parameters with caching to reduce database queries.
    Cache is stored for 1 hour. Returns tuple: (survey_params, params_dict)
    """
    cache_key = f'survey_params_{survey_id}'
    cached_data = cache.get(cache_key)
    
    if not cached_data:
        survey_params = get_object_or_404(SurveyParams, survey_id=survey_id)
        # Parse params once and cache the result
        params_dict = ast.literal_eval(survey_params.params) if isinstance(survey_params.params, str) else survey_params.params
        cached_data = (survey_params, params_dict)
        cache.set(cache_key, cached_data, timeout=3600)  # Cache for 1 hour
    
    return cached_data

def tester(request, survey_id):
    payload, _ = get_survey_params_cached(survey_id)  # Unpack tuple, ignore params_dict
    
    # Debug information
    debug_info = {
        'payload': payload,
        'payload_type': type(payload).__name__,
        'payload_dir': dir(payload),
        'survey_id': payload.survey_id if hasattr(payload, 'survey_id') else 'N/A',
        'survey_name': payload.survey_name if hasattr(payload, 'survey_name') else 'N/A',
        'params': payload.params if hasattr(payload, 'params') else 'N/A',
        'params_type': type(payload.params).__name__ if hasattr(payload, 'params') else 'N/A',
        'user': payload.user if hasattr(payload, 'user') else 'N/A',
        'created_at': payload.created_at if hasattr(payload, 'created_at') else 'N/A',
    }
    
    return render(request, "survey_taker/tester.html", {"debug_info": debug_info})


def survey_view(request, survey_id):
    """
    Renders the Survey.js interface for a specific survey.
    URL parameter: survey_id (UUID) - the primary key from SurveyParams table
    """
    # Get the survey parameters from the database (with caching)
    survey_params, _ = get_survey_params_cached(survey_id)  # Unpack tuple, ignore params_dict
    
    # Render the survey template with the survey data
    context = {
        'survey_id': str(survey_id),
        'survey_name': survey_params.survey_name,
        'survey_params': json.dumps(survey_params.params),  # Pass params as JSON string
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
    survey_params, params_dict = get_survey_params_cached(survey_id)
    params_dict = TEST_PARAMS #Overwrite with these params for, well you know, testing
    try:
        # === DEBUG START ===
        print("[DEBUG] Starting process_response")
        # === DEBUG END ===

        # Parse the incoming JSON data
        data = json.loads(request.body)
        user_message = data.get('user_message', '')
        respondent_id = data.get('respondent_id', str(uuid.uuid4()))

        # === DEBUG START ===
        print(f"[DEBUG] user_message: {user_message}, respondent_id: {respondent_id}")
        # === DEBUG END ===

        # Initialize or retrieve conversation log from session
        conversation_log = request.session.get('conversation_log', [])

        # === DEBUG START ===
        print(f"[DEBUG] conversation_log length: {len(conversation_log)}")
        # === DEBUG END ===

        # Append user's answer if they provided one
        if user_message:
            conversation_log.append({
                'is_question': 0,
                'content': user_message
            })
            # === DEBUG START ===
            print(f"[DEBUG] Added user message to log")
            # === DEBUG END ===
        
        # === DEBUG START ===
        print(f"[DEBUG] About to call get_response")
        print(f"[DEBUG] params_dict keys: {list(params_dict.keys())}")
        print(f"[DEBUG] api_key exists: {api_key is not None}")
        t_before_get_response = time.time()
        # === DEBUG END ===
        
        # Call LangGraph architecture
        next_question = get_response(params_dict, conversation_log, api_key)
        
        # === DEBUG START ===
        t_after_get_response = time.time()
        print(f"[TIMING] get_response total: {(t_after_get_response - t_before_get_response) * 1000:.2f}ms")
        print(f"[DEBUG] get_response returned: {next_question[:50] if isinstance(next_question, str) else next_question}...")
        # === DEBUG END ===
        
        # Append AI's question to conversation log
        t_before_session = time.time()
        conversation_log.append({
            'is_question': 1,
            'content': next_question
        })
        
        # Save updated conversation log to session
        request.session['conversation_log'] = conversation_log
        t_after_session = time.time()

        # === DEBUG START ===
        print(f"[TIMING] Session save: {(t_after_session - t_before_session) * 1000:.2f}ms")
        print(f"[DEBUG] Conversation log updated, length: {len(conversation_log)}")
        # === DEBUG END ===
        
        # Calculate processing time
        t_before_json = time.time()
        response_data = {
            'message': next_question,
            'status': 'success',
            'respondent_id': respondent_id
        }
        
        if DEBUG_TIMING:
            processing_time_ms = round((time.time() - start_time) * 1000, 2)
            response_data['processing_time_ms'] = processing_time_ms
            print(f"[DEBUG] Request processed in {processing_time_ms}ms")
        
        return JsonResponse(response_data)
        
    except json.JSONDecodeError as e:
        # === DEBUG START ===
        print(f"[DEBUG ERROR] JSON decode error: {e}")
        # === DEBUG END ===
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        # === DEBUG START ===
        print(f"[DEBUG ERROR] Exception in process_response: {str(e)}")
        print(f"[DEBUG ERROR] Exception type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        # === DEBUG END ===
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
    
    survey_params, _ = get_survey_params_cached(survey_id)
    
    try:
        data = json.loads(request.body)
        respondent_id = data.get('respondent_id')
        conversation = data.get('conversation', [])
        
        # Save entire conversation as single database entry
        response_obj, created = SurveyResponse.objects.update_or_create(
            survey=survey_params,
            respondent_id=respondent_id,
            defaults={'responses': {'conversation': conversation}}
        )
        
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
