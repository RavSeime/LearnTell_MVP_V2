"""
UPDATED views.py with LangGraph Integration

Replace lines 97-112 in your existing views.py with this implementation.
"""

# ============= UPDATED process_response VIEW =============
# Replace lines 97-112 with this code:

@csrf_exempt
def process_response(request, survey_id):
    """
    POST endpoint to process each participant response.
    Now uses LangGraph architecture with LangSmith tracking.
    
    Expected POST data:
    {
        "user_message": "participant's response",
        "respondent_id": "unique identifier for the respondent"
    }
    
    Returns:
    {
        "message": "AI's next question or response",
        "status": "success",
        "terminated": false
    }
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    # Get the survey parameters (with caching) - params_dict is already parsed
    survey_params, params_dict = get_survey_params_cached(survey_id)
    params_dict = TEST_PARAMS['STOCK_MARKET']  # Overwrite with test params for testing
    
    try:
        # Parse the incoming JSON data
        data = json.loads(request.body)
        user_message = data.get('user_message', '')
        respondent_id = data.get('respondent_id', str(uuid.uuid4()))
        
        # === LANGGRAPH INTEGRATION (REPLACES LINES 97-112) ===
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
        # === END LANGGRAPH INTEGRATION ===
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        import traceback
        return JsonResponse({
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500)
