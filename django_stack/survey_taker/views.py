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
from .testing_params import TEST_PARAMS, TEST_PARAMS_VERBOSE
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


def get_session_key(survey_id, key_name):
    """Generate a namespaced session key for survey-specific data."""
    return f'survey_{survey_id}_{key_name}'


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
        cached_data = (survey_params, params_dict) # TODO(ravse): Refactor cache to store only survey_params, parse params on demand
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
    #params_dict = TEST_PARAMS_VERBOSE #Overwrite with these params for, well you know, testing
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
        conversation_log = request.session.get(get_session_key(survey_id, 'conversation_log'), [])

        #Initialize or retrive index of current topic
        current_topic_index = request.session.get(get_session_key(survey_id, 'current_topic_index'), 0)
        nr_questions_asked_current_topic = request.session.get(get_session_key(survey_id, 'nr_questions_asked_current_topic'), 0)

        # === DEBUG START ===
        print(f"[DEBUG] conversation_log length: {len(conversation_log)}")
        print(f"current_topic_index Pre Stack {current_topic_index}")
        print(f"nr_questions_asked_current_topic Pre Stack {nr_questions_asked_current_topic}")
        # === DEBUG END ===

        # Append user's answer if they provided one
        if user_message:
            conversation_log.append({
                'order': len(conversation_log),
                'is_question': 0,
                'content': user_message,
                'topic': current_topic_index
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
        
        # Check if this is the first question (conversation_log is empty or only has 1 item - the user's first message)
        if len(conversation_log) <= 1 and 'first_question' in params_dict:
            # Return pre-set first question immediately
            next_question = params_dict['first_question']
            
            # Warm OpenAI cache in background for first topic
            try:
                import threading
                def warm_cache():
                    from .self_eng_langgraph.multi_agent import warm_openai_cache
                    # Warm cache with empty conversation (just system prompt)
                    warm_openai_cache(params_dict, current_topic_index, [], api_key)
                
                # Start cache warming in background (non-blocking)
                warm_thread = threading.Thread(target=warm_cache, daemon=True)
                warm_thread.start()
                print(f"[DEBUG] Warming OpenAI cache for first topic in background")
            except Exception as e:
                print(f"[DEBUG] Cache warming failed (non-critical): {e}")
        
        # Check if all topics are done and we should show closing questions
        elif current_topic_index >= len(params_dict.get("interview_plan", [])) and 'closing_questions' in params_dict:
            closing_question_index = request.session.get(get_session_key(survey_id, 'closing_question_index'), 0)
            
            if closing_question_index < len(params_dict['closing_questions']):
                next_question = params_dict['closing_questions'][closing_question_index]
                print(f"[DEBUG] Closing question {closing_question_index + 1}/{len(params_dict['closing_questions'])}")
            else:
                next_question = params_dict["end_of_interview_message"]
                print(f"[DEBUG] All closing questions complete")
        
        # Check if we have a pre-generated transition question (first question of new topic)
        elif nr_questions_asked_current_topic == 0 and current_topic_index > 0 and current_topic_index < len(params_dict["interview_plan"]):
            print(f"[DEBUG] Transition elif triggered")
            # Try session first, then cache as fallback
            next_question = request.session.get(get_session_key(survey_id, 'pre_generated_transition'), None)
            
            #Commented out transition code for now. HACK
            
            if not next_question:
                # Check cache (background thread may have stored it here)
                next_question = cache.get(f'transition_{respondent_id}_{current_topic_index}')
                if next_question:
                    print(f"[DEBUG] Using pre-generated transition from cache (0ms latency)")
                    cache.delete(f'transition_{respondent_id}_{current_topic_index}')
                else:
                    # Fallback: generate transition now (will add latency)
                    print(f"[DEBUG] No pre-generated transition found, generating now (fallback)")
                    from .self_eng_langgraph.multi_agent import get_transition_question
                    next_question = get_transition_question(params_dict, current_topic_index, conversation_log, api_key)
            else:
                print(f"[DEBUG] Using pre-generated transition from session (0ms latency)")
                # Clear the pre-generated transition
                request.session.pop(get_session_key(survey_id, 'pre_generated_transition'), None)
            
            
            """
            # HACK: Override with raw topic text
            next_question = params_dict["interview_plan"][current_topic_index]["topic"]
            print(f"[DEBUG HACK] Overriding transition with raw topic text")
            """
        
        else:
            # Call LangGraph architecture for subsequent questions
            next_question = get_response(params_dict, current_topic_index,  conversation_log, api_key)
        
        # === DEBUG START ===
        t_after_get_response = time.time()
        print(f"[TIMING] get_response total: {(t_after_get_response - t_before_get_response) * 1000:.2f}ms")
        print(f"[DEBUG] get_response returned: {next_question[:50] if isinstance(next_question, str) else next_question}...")
        # === DEBUG END ===
        
        # Append AI's question to conversation log
        t_before_session = time.time()
        conversation_log.append({
            'order': len(conversation_log),
            'is_question': 1,
            'content': next_question,
            'topic': current_topic_index,
        })
        
        # Save updated conversation log to session
        request.session[get_session_key(survey_id, 'conversation_log')] = conversation_log
        
        # Track progress based on where we are
        if current_topic_index >= len(params_dict.get("interview_plan", [])):
            # In closing questions phase
            closing_question_index = request.session.get(get_session_key(survey_id, 'closing_question_index'), 0)
            request.session[get_session_key(survey_id, 'closing_question_index')] = closing_question_index + 1
        elif current_topic_index < len(params_dict["interview_plan"]):
            # Normal topic progression
            nr_questions_asked_current_topic += 1
            
            topic_length = params_dict["interview_plan"][current_topic_index]["length"]
            
            # Pre-generate transition and warm cache if this is the last question of current topic
            if nr_questions_asked_current_topic == topic_length and current_topic_index + 1 < len(params_dict["interview_plan"]) and params_dict["pre_gen_transitions"]:
                # Generate transition and warm cache for next topic in background
                next_topic_idx = current_topic_index + 1  # Capture value before thread
                try:
                    import threading
                    def pregenerate_and_warm():
                        from .self_eng_langgraph.multi_agent import get_transition_question, warm_openai_cache
                        # Generate transition question
                        transition = get_transition_question(params_dict, next_topic_idx, conversation_log, api_key)
                        # Store in cache instead of session (thread-safe)
                        cache.set(f'transition_{respondent_id}_{next_topic_idx}', transition, timeout=300)
                        print(f"[DEBUG] Pre-generated transition stored with key: transition_{respondent_id}_{next_topic_idx}")
                        # Warm OpenAI cache for next topic
                        warm_openai_cache(params_dict, next_topic_idx, conversation_log, api_key)
                    
                    thread = threading.Thread(target=pregenerate_and_warm, daemon=True)
                    thread.start()
                except Exception as e:
                    print(f"[DEBUG] Transition pre-generation/warming failed (non-critical): {e}")
            
            if nr_questions_asked_current_topic >= topic_length:
                current_topic_index += 1
                nr_questions_asked_current_topic = 0
                
                # Check for pre-generated transition in cache
                transition = cache.get(f'transition_{respondent_id}_{current_topic_index}')
                if transition:
                    request.session[get_session_key(survey_id, 'pre_generated_transition')] = transition
                    cache.delete(f'transition_{respondent_id}_{current_topic_index}')
            
            print(f"[DEBUG]current_topic_index Post Stack {current_topic_index}")
            print(f"[DEBUG] nr_questions_asked_current_topic Post Stack {nr_questions_asked_current_topic}")
            
            # Save topic tracking to session
            request.session[get_session_key(survey_id, 'current_topic_index')] = current_topic_index
            request.session[get_session_key(survey_id, 'nr_questions_asked_current_topic')] = nr_questions_asked_current_topic
        
        t_after_session = time.time()

        # === DEBUG START ===
        print(f"[TIMING] Session save: {(t_after_session - t_before_session) * 1000:.2f}ms")
        print(f"[DEBUG] Conversation log updated, length: {len(conversation_log)}")
        print(f"[DEBUG] Topic: {current_topic_index}, Question {nr_questions_asked_current_topic}/{topic_length if current_topic_index < len(params_dict['interview_plan']) else 'done'}")
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
