"""
LangGraph Interview Agent with LangSmith Tracking

This module implements the interview logic using LangGraph for state management
and orchestration, with LangSmith integration for observability and debugging.

Key changes from original implementation:
1. Uses LangGraph StateGraph for workflow management
2. LangSmith tracing for all LLM calls and agent actions
3. Simplified state management with TypedDict
4. Async support for better Django integration
5. More modular node-based architecture
"""

import os
import logging
from typing import TypedDict, Annotated, Literal, Optional
from datetime import datetime
import operator

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, END
from langsmith import traceable


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ===========================================
# STATE DEFINITION
# ===========================================

class InterviewState(TypedDict):
    """
    State schema for the interview graph.
    Uses Annotated with operator.add for messages to append rather than replace.
    """
    # Session identifiers
    session_id: str
    respondent_id: str
    
    # Conversation history (accumulated)
    messages: Annotated[list, operator.add]
    
    # Interview progress tracking
    topic_idx: int
    question_idx: int
    finish_idx: int
    flagged_messages: int
    terminated: bool
    
    # Summary and context
    summary: str
    current_user_message: str
    
    # Interview parameters (from config)
    parameters: dict
    
    # Output
    next_question: str
    should_moderate: bool
    moderation_passed: bool


# ===========================================
# HELPER FUNCTIONS
# ===========================================

def chat_to_string(messages: list, only_topic: Optional[int] = None, until_topic: Optional[int] = None) -> str:
    """Convert messages into formatted string for prompts."""
    history = ""
    for msg in messages:
        topic_idx = msg.get('topic_idx', 0)
        
        if only_topic and topic_idx != only_topic:
            continue
        if until_topic and topic_idx == until_topic:
            break
            
        if msg.get('type') == 'question':
            history += f'Interviewer: "{msg["content"]}"\n'
        elif msg.get('type') == 'answer':
            history += f'Interviewee: "{msg["content"]}"\n'
    
    return history.strip()


def fill_prompt_template(template: str, state: InterviewState) -> str:
    """Fill prompt template with current interview state."""
    params = state['parameters']
    topics = params['interview_plan']
    
    current_topic_idx = min(state['topic_idx'], len(topics))
    next_topic_idx = min(current_topic_idx + 1, len(topics))
    
    # Get current topic conversation
    current_topic_msgs = [m for m in state['messages'] if m.get('topic_idx') == current_topic_idx]
    current_topic_history = chat_to_string(current_topic_msgs)
    
    # Get summary or full history until current topic
    summary_or_history = state['summary'] or chat_to_string(
        [m for m in state['messages'] if m.get('topic_idx', 0) < current_topic_idx]
    )
    
    return template.format(
        topics='\n'.join([t['topic'] for t in topics]),
        question=state['messages'][-1].get('content', '') if state['messages'] else '',
        answer=state['current_user_message'],
        summary=summary_or_history,
        current_topic=topics[current_topic_idx - 1]['topic'],
        next_interview_topic=topics[next_topic_idx - 1]['topic'],
        current_topic_history=current_topic_history
    )


# ===========================================
# GRAPH NODES (AGENT FUNCTIONS)
# ===========================================

@traceable(name="check_termination")
def check_termination(state: InterviewState) -> InterviewState:
    """Check if interview should be terminated."""
    if state.get('terminated', False):
        logger.info(f"Interview {state['session_id']} already terminated")
        state['next_question'] = state['parameters']['termination_message']
    return state


@traceable(name="moderate_answer")
def moderate_answer(state: InterviewState) -> InterviewState:
    """Moderate user's answer for appropriateness."""
    params = state['parameters']
    
    if not params.get('moderate_answers') or not params.get('moderator'):
        state['moderation_passed'] = True
        return state
    
    # Initialize LLM for moderation
    llm = ChatOpenAI(
        model=params['moderator'].get('model', 'gpt-4o-mini'),
        temperature=0,
        max_tokens=params['moderator'].get('max_tokens', 2),
        api_key=os.getenv('OPENAI_API_KEY')
    )
    
    # Construct moderation prompt
    last_question = [m for m in state['messages'] if m.get('type') == 'question']
    last_q_content = last_question[-1]['content'] if last_question else "No previous question"
    
    prompt = params['moderator']['prompt'].format(
        question=last_q_content,
        answer=state['current_user_message']
    )
    
    response = llm.invoke([SystemMessage(content=prompt)])
    is_appropriate = 'yes' in response.content.lower()
    
    state['moderation_passed'] = is_appropriate
    
    if not is_appropriate:
        state['flagged_messages'] += 1
        logger.warning(f"Message flagged in session {state['session_id']}: {state['current_user_message']}")
        
        # Check if flagged too often
        if state['flagged_messages'] >= params.get('max_flags_allowed', 3):
            state['terminated'] = True
            state['next_question'] = params['flagged_message']
            logger.info(f"Session {state['session_id']} terminated due to excessive flags")
        else:
            state['next_question'] = params['off_topic_message']
    
    return state


@traceable(name="add_user_message")
def add_user_message(state: InterviewState) -> InterviewState:
    """Add user message to conversation history."""
    if state.get('moderation_passed', True):
        new_message = {
            'type': 'answer',
            'content': state['current_user_message'],
            'topic_idx': state['topic_idx'],
            'question_idx': state['question_idx'],
            'timestamp': str(datetime.now())
        }
        state['messages'].append(new_message)
        logger.info(f"Added user message to session {state['session_id']}")
    return state


@traceable(name="probe_within_topic")
def probe_within_topic(state: InterviewState) -> InterviewState:
    """Generate probing question within current topic."""
    params = state['parameters']
    
    # Initialize LLM
    llm = ChatOpenAI(
        model=params['probe'].get('model', 'gpt-4o'),
        temperature=params['probe'].get('temperature', 0.7),
        max_tokens=params['probe'].get('max_tokens', 300),
        api_key=os.getenv('OPENAI_API_KEY')
    )
    
    # Fill prompt
    prompt = fill_prompt_template(params['probe']['prompt'], state)
    
    # Generate question
    response = llm.invoke([SystemMessage(content=prompt)])
    next_question = response.content.strip(' \n"\'')
    
    state['next_question'] = next_question
    state['question_idx'] += 1
    
    logger.info(f"Generated probe question for session {state['session_id']}: {next_question}")
    return state


@traceable(name="transition_topic")
def transition_topic(state: InterviewState) -> InterviewState:
    """Transition to next topic and optionally generate summary."""
    params = state['parameters']
    
    # Initialize LLM
    llm = ChatOpenAI(
        model=params['transition'].get('model', 'gpt-4o'),
        temperature=params['transition'].get('temperature', 0.7),
        max_tokens=params['transition'].get('max_tokens', 300),
        api_key=os.getenv('OPENAI_API_KEY')
    )
    
    # Generate transition question
    transition_prompt = fill_prompt_template(params['transition']['prompt'], state)
    transition_response = llm.invoke([SystemMessage(content=transition_prompt)])
    next_question = transition_response.content.strip(' \n"\'')
    
    # Generate summary if enabled
    if params.get('summarize') and params.get('summary'):
        summary_llm = ChatOpenAI(
            model=params['summary'].get('model', 'gpt-4o'),
            temperature=0,
            max_tokens=params['summary'].get('max_tokens', 1000),
            api_key=os.getenv('OPENAI_API_KEY')
        )
        
        summary_prompt = fill_prompt_template(params['summary']['prompt'], state)
        summary_response = summary_llm.invoke([SystemMessage(content=summary_prompt)])
        state['summary'] = summary_response.content.strip()
        logger.info(f"Generated summary for session {state['session_id']}")
    
    state['next_question'] = next_question
    state['topic_idx'] += 1
    state['question_idx'] = 1
    
    logger.info(f"Transitioned to topic {state['topic_idx']} in session {state['session_id']}")
    return state


@traceable(name="closing_question")
def closing_question(state: InterviewState) -> InterviewState:
    """Get next closing question."""
    params = state['parameters']
    closing_questions = params.get('closing_questions', [])
    
    try:
        next_q = closing_questions[state['finish_idx'] - 1]
        state['next_question'] = next_q
        state['finish_idx'] += 1
        logger.info(f"Generated closing question {state['finish_idx']-1} for session {state['session_id']}")
    except IndexError:
        # No more closing questions
        state['terminated'] = True
        state['next_question'] = params['end_of_interview_message']
        logger.info(f"Interview {state['session_id']} completed")
    
    # Mark as in closing phase
    state['topic_idx'] = 99
    state['question_idx'] = 99
    
    return state


@traceable(name="moderate_question")
def moderate_question(state: InterviewState) -> InterviewState:
    """Check if generated question should be moderated."""
    params = state['parameters']
    
    if not params.get('moderate_questions'):
        return state
    
    # Use OpenAI moderation endpoint
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    response = client.moderations.create(
        model="omni-moderation-latest",
        input=state['next_question']
    )
    
    flagged = response.results[0].flagged
    
    if flagged:
        state['terminated'] = True
        state['next_question'] = params['end_of_interview_message']
        logger.warning(f"Question flagged by moderation in session {state['session_id']}")
    
    return state


@traceable(name="add_question_to_history")
def add_question_to_history(state: InterviewState) -> InterviewState:
    """Add generated question to conversation history."""
    new_message = {
        'type': 'question',
        'content': state['next_question'],
        'topic_idx': state['topic_idx'],
        'question_idx': state['question_idx'],
        'timestamp': str(datetime.now())
    }
    state['messages'].append(new_message)
    logger.info(f"Added question to history in session {state['session_id']}")
    return state


# ===========================================
# ROUTING LOGIC
# ===========================================

def should_terminate(state: InterviewState) -> Literal["terminate", "continue"]:
    """Determine if interview should terminate."""
    if state.get('terminated', False):
        return "terminate"
    return "continue"


def should_moderate(state: InterviewState) -> Literal["moderate", "add_message"]:
    """Determine if answer needs moderation."""
    params = state['parameters']
    if params.get('moderate_answers') and params.get('moderator'):
        return "moderate"
    return "add_message"


def moderation_result(state: InterviewState) -> Literal["failed", "passed"]:
    """Check moderation result."""
    if not state.get('moderation_passed', True):
        if state.get('terminated', False):
            return "failed"  # Too many flags
        return "failed"  # Single flag, show warning
    return "passed"


def determine_next_action(state: InterviewState) -> Literal["probe", "transition", "closing", "end"]:
    """Determine next interview action based on progress."""
    params = state['parameters']
    interview_plan = params['interview_plan']
    
    num_topics = len(interview_plan)
    current_topic_idx = state['topic_idx']
    current_question_idx = state['question_idx']
    
    # Check if on last topic
    on_last_topic = current_topic_idx >= num_topics
    
    # Check if on last question of current topic
    if current_topic_idx <= num_topics:
        num_questions = interview_plan[current_topic_idx - 1]['length']
        on_last_question = current_question_idx >= num_questions
    else:
        on_last_question = True
    
    # Determine action
    if on_last_topic and on_last_question:
        # Move to closing questions
        closing_qs = params.get('closing_questions', [])
        if state['finish_idx'] <= len(closing_qs):
            return "closing"
        else:
            return "end"
    elif on_last_question:
        # Transition to next topic
        return "transition"
    else:
        # Continue probing within topic
        return "probe"


# ===========================================
# BUILD GRAPH
# ===========================================

def build_interview_graph() -> StateGraph:
    """Build the LangGraph state graph for interview flow."""
    
    # Initialize graph
    workflow = StateGraph(InterviewState)
    
    # Add nodes
    workflow.add_node("check_termination", check_termination)
    workflow.add_node("moderate_answer", moderate_answer)
    workflow.add_node("add_user_message", add_user_message)
    workflow.add_node("probe_within_topic", probe_within_topic)
    workflow.add_node("transition_topic", transition_topic)
    workflow.add_node("closing_question", closing_question)
    workflow.add_node("moderate_question", moderate_question)
    workflow.add_node("add_question_to_history", add_question_to_history)
    
    # Set entry point
    workflow.set_entry_point("check_termination")
    
    # Add edges with conditional routing
    workflow.add_conditional_edges(
        "check_termination",
        should_terminate,
        {
            "terminate": END,
            "continue": "moderate_answer"
        }
    )
    
    workflow.add_conditional_edges(
        "moderate_answer",
        moderation_result,
        {
            "failed": "add_question_to_history",  # Return warning or termination message
            "passed": "add_user_message"
        }
    )
    
    workflow.add_conditional_edges(
        "add_user_message",
        determine_next_action,
        {
            "probe": "probe_within_topic",
            "transition": "transition_topic",
            "closing": "closing_question",
            "end": END
        }
    )
    
    workflow.add_edge("probe_within_topic", "moderate_question")
    workflow.add_edge("transition_topic", "moderate_question")
    workflow.add_edge("closing_question", "moderate_question")
    
    workflow.add_conditional_edges(
        "moderate_question",
        should_terminate,  # Check if question moderation triggered termination
        {
            "terminate": "add_question_to_history",
            "continue": "add_question_to_history"
        }
    )
    
    workflow.add_edge("add_question_to_history", END)
    
    return workflow.compile()


# ===========================================
# MAIN INTERVIEW FUNCTION
# ===========================================

@traceable(name="process_interview_message", run_type="chain")
def process_interview_message(
    user_message: str,
    params_dict: dict,
    respondent_id: str,
    session_state: Optional[dict] = None
) -> dict:
    """
    Main entry point for processing interview messages.
    
    Args:
        user_message: The user's response
        params_dict: Interview parameters (from TEST_PARAMS)
        respondent_id: Unique identifier for respondent
        session_state: Optional existing session state for resuming
        
    Returns:
        dict with 'message', 'session_state', and 'terminated' keys
    """
    
    # Initialize or resume state
    if session_state is None:
        # New interview - start with first question
        state = InterviewState(
            session_id=respondent_id,
            respondent_id=respondent_id,
            messages=[],
            topic_idx=1,
            question_idx=1,
            finish_idx=1,
            flagged_messages=0,
            terminated=False,
            summary="",
            current_user_message=user_message,
            parameters=params_dict,
            next_question="",
            should_moderate=params_dict.get('moderate_answers', True),
            moderation_passed=True
        )
        
        # Add first question to history
        first_q = params_dict['first_question']
        state['messages'].append({
            'type': 'question',
            'content': first_q,
            'topic_idx': 1,
            'question_idx': 0,
            'timestamp': str(datetime.now())
        })
        
        # If user_message is empty, this is just initialization
        if not user_message:
            return {
                'message': first_q,
                'session_state': state,
                'terminated': False
            }
    else:
        # Resume existing interview
        state = session_state.copy()
        state['current_user_message'] = user_message
    
    # Build and run graph
    graph = build_interview_graph()
    
    # Execute graph
    result = graph.invoke(state)
    
    # Extract results
    return {
        'message': result['next_question'],
        'session_state': result,
        'terminated': result.get('terminated', False)
    }


# ===========================================
# DJANGO INTEGRATION HELPER
# ===========================================

def django_interview_handler(user_message: str, params_dict: dict, respondent_id: str, request) -> dict:
    """
    Django-specific wrapper for interview processing.
    Manages session state via Django session framework.
    
    Usage in views.py (lines 97-112):
        from .langgraph_interview import django_interview_handler
        
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
            'terminated': result['terminated']
        })
    """
    
    # Get session state from Django session
    session_key = f"interview_state_{respondent_id}"
    session_state = request.session.get(session_key)
    
    # Process message
    result = process_interview_message(
        user_message=user_message,
        params_dict=params_dict,
        respondent_id=respondent_id,
        session_state=session_state
    )
    
    # Store updated state in Django session
    request.session[session_key] = result['session_state']
    
    return result
