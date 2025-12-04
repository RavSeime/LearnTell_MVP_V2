"""
Minimal thread-safe LangGraph interview handler.
Uses Django sessions for state isolation between survey attendees.
"""

def process_interview_message(user_message: str, params_dict: dict, respondent_id: str, session_state: dict = None) -> dict:
    """
    Process a single interview message.
    
    Args:
        user_message: User's response
        params_dict: Interview parameters from TEST_PARAMS
        respondent_id: Unique identifier for this respondent
        session_state: Previous state (None for new interview)
        
    Returns:
        dict with 'message', 'session_state', 'terminated' keys
    """
    
    # Initialize new interview
    if session_state is None:
        state = {
            'respondent_id': respondent_id,
            'messages': [],
            'topic_idx': 0,
            'question_idx': 0,
            'terminated': False
        }
        
        # Return first question
        first_question = params_dict.get('first_question', 'Hello! Let\'s begin.')
        state['messages'].append({
            'type': 'question',
            'content': first_question
        })
        
        return {
            'message': first_question,
            'session_state': state,
            'terminated': False
        }
    
    # Resume existing interview
    state = session_state.copy()
    
    # Store user's answer
    if user_message:
        state['messages'].append({
            'type': 'answer',
            'content': user_message
        })
    
    # TODO: Add your LangGraph logic here
    # This is where you'll:
    # 1. Build your StateGraph
    # 2. Define your agent nodes
    # 3. Execute the graph with the current state
    # 4. Generate the next question
    
    # TODO: Add your LangGraph logic here
    # For now, return a simple next question
    interview_plan = params_dict.get('interview_plan', [])
    closing_questions = params_dict.get('closing_questions', [])
    
    # Calculate total questions
    total_topic_questions = sum(topic.get('length', 0) for topic in interview_plan)
    total_questions = total_topic_questions + len(closing_questions)
    
    # Check if interview is complete
    if state['question_idx'] >= total_questions:
        state['terminated'] = True
        next_question = params_dict.get('end_of_interview_message', 'Thank you!---END---')
    else:
        # Placeholder: Generate next question
        next_question = f"Question {state['question_idx'] + 1}: This is a placeholder. Add your LangGraph agents here."
        state['question_idx'] += 1
    
    state['messages'].append({
        'type': 'question',
        'content': next_question
    })
    
    return {
        'message': next_question,
        'session_state': state,
        'terminated': state['terminated']
    }


def django_interview_handler(user_message: str, params_dict: dict, respondent_id: str, request) -> dict:
    """
    Django-specific wrapper with thread-safe session management.
    
    Args:
        user_message: User's response
        params_dict: Interview parameters
        respondent_id: Unique identifier for respondent
        request: Django request object (for session access)
        
    Returns:
        dict with 'message', 'status', 'respondent_id', 'terminated' keys
    """
    
    # Thread-safe: Each respondent gets unique session key
    session_key = f"interview_state_{respondent_id}"
    session_state = request.session.get(session_key)
    
    # Process the message
    result = process_interview_message(
        user_message=user_message,
        params_dict=params_dict,
        respondent_id=respondent_id,
        session_state=session_state
    )
    
    # Store updated state in Django session (thread-safe)
    request.session[session_key] = result['session_state']
    
    return {
        'message': result['message'],
        'status': 'success',
        'respondent_id': respondent_id,
        'terminated': result['terminated']
    }
