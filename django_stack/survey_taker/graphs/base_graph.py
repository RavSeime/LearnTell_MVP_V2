
from langchain.chat_models import init_chat_model
import logging

logger = logging.getLogger(__name__)

"""
This is the most basic graph setup, which servers as a baseline skeleton for other graph setups
Only LLM components are prompter and transition.

It works of the standard param setup used in V1

All caches are warmed at the start of the interview.
The prompter system prompt cache is warmed once. ¨
The transition system prompt is warmed seperatly for every future transition. 

The transitions are NOT pre-generated
"""

from langchain.messages import AnyMessage
from typing_extensions import TypedDict, Annotated
import operator

def indexer_progression(params: dict, topic_index: int, question_index: int):
    """Standard progression logic.
    inputs: params, topic_index, question_index
    outputs: [topic_index, question_index]
    if question_index is equal to length in params: topic_index increases by 1 and question_index is set to zero.
    else question_index increases by one
    """
    
    # Get the length of questions for the current topic
    current_topic_length = params["interview_plan"][topic_index]["length"]
    
    # Check if we've reached the end of questions for this topic
    if question_index == current_topic_length:
        # Move to next topic and reset question index
        topic_index += 1
        question_index = 1 #Note that we start the index from 1!
    else:
        # Continue with next question in current topic
        question_index += 1
    
    return [topic_index, question_index]


class State(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    interview_meta: dict   #Can add more meta variables as need be, all depends on structure
    next_node: str
    params : dict

from langchain.messages import SystemMessage

def standard_question_llm(state: dict):

    # Handle default values for interview_meta if not present
    interview_meta = state.get('interview_meta', {"topic_index": 0, "question_index": 1}) #Question index is started from 1, but topic index is started from zero
    
    # Initialize model from params
    prompter_model = init_chat_model(
        state["params"]["prompter_llm"]["model"],
        api_key=state["params"].get("api_key"),
        **state["params"]["prompter_llm"]["kwargs"]
    )
    
    #Get current topic
    current_topic = state["params"]["interview_plan"][interview_meta["topic_index"]]["topic"]

    #Incrementing index logic
    interview_meta["topic_index"], interview_meta["question_index"] = indexer_progression(state["params"],
                                                                                                interview_meta["topic_index"],
                                                                                                interview_meta["question_index"]
                                                                                            )
    
    logger.debug(f"[standard_question_llm] interview_meta after update: {interview_meta}")
    
    return {
        "messages": [
            prompter_model.invoke(
                [
                    SystemMessage(
                        content=state["params"]["prompter_llm"]["prompt"].format(
                            current_topic=current_topic
                        )
                    )
                ]
                + state["messages"]
            )
        ],
        "interview_meta": interview_meta
    }

def transition_llm(state: dict):
    "This is the version that gives a short 'aha that is soo cool' and "
    "then just pastes in the initial question" 

    # Handle default values for interview_meta if not present
    interview_meta = state.get('interview_meta', {"topic_index": 0, "question_index": 1}) #Question index is started from 1, but topic index is started from zero
    
    # Initialize model from params
    transition_model = init_chat_model(
        state["params"]["transition_llm"]["model"],
        api_key=state["params"].get("api_key"),
        **state["params"]["transition_llm"]["kwargs"]
    )
    
    #Get current topic
    topic_inital_question = state["params"]["interview_plan"][interview_meta["topic_index"]]["initial_question"]

    #Get current and next topic for transition prompt
    current_topic = state["params"]["interview_plan"][interview_meta["topic_index"]]["topic"]
    next_topic = state["params"]["interview_plan"][interview_meta["topic_index"]]["topic"]

    #Incrementing index logic
    interview_meta["topic_index"], interview_meta["question_index"] = indexer_progression(state["params"],
                                                                                                interview_meta["topic_index"],
                                                                                                interview_meta["question_index"]
                                                                                            )
    transition_phrase = transition_model.invoke(
                [
                    SystemMessage(
                        content=state["params"]["transition_llm"]["prompt"].format(
                            previous_topic=current_topic,
                            next_topic=next_topic
                        )
                    )
                ]
                + state["messages"]
            )
    
    from langchain.messages import AIMessage
    response = transition_phrase.content + "\n\n" + topic_inital_question

    logger.debug(f"[transition_llm] interview_meta after update: {interview_meta}")

    return {
        "messages": [
            AIMessage(content=response)
        ],
        "interview_meta": interview_meta
    }

def first_question_node(state: dict):
    """Node to ask the first question in the interview plan."""
    
    from langchain.messages import AIMessage
    
    # Initialize interview_meta
    interview_meta = {"topic_index": 0, "question_index": 1}  # Start from the first topic and first question
    
    #Incrementing index logic
    interview_meta["topic_index"], interview_meta["question_index"] = indexer_progression(state["params"],
                                                                                                interview_meta["topic_index"],
                                                                                                interview_meta["question_index"]
                                                                                            )
    # Get the first topic and its initial question
    first_question = state["params"]["interview_plan"][0]["initial_question"]
    
    logger.debug(f"[first_question_node] interview_meta after update: {interview_meta}")
    
    return {
        "messages": [
            AIMessage(content=first_question)
        ],
        "interview_meta": interview_meta
    }

def last_qustion_node(state: dict):
    """Node to handle the last question in the interview plan."""
    
    from langchain.messages import AIMessage
    # You can add any specific logic for the last question here if needed
    last_question = state["params"]["end_of_interview_message"]
    
    logger.debug(f"[last_qustion_node] Reached end of interview")
    
    return {
        "messages": [
            AIMessage(content=last_question)
        ],
    }

def router_node(state: dict):
    """Router node to determine the next step in the interview process."""
    
    interview_meta = state.get('interview_meta', {"topic_index": 0, "question_index": 1})
    topic_index = interview_meta["topic_index"]
    question_index = interview_meta["question_index"]

    #Check if its the first question overall
    if topic_index == 0 and question_index == 1:
        next_node = "first_question_node"
    
    # Check if we've reached the end of the interview plan
    elif topic_index >= len(state["params"]["interview_plan"]):
        next_node = "last_qustion_node"
    
    # Determine if it's the first question of a topic
    elif question_index == 1:
        next_node = "transition_llm"
    else:
        next_node = "standard_question_llm"

    logger.debug(f"[router_node] interview_meta: {interview_meta}, next_node: {next_node}")

    return {"next_node": next_node}


from typing import Literal
from langgraph.graph import StateGraph, START, END

from langgraph.checkpoint.memory import MemorySaver

agent_builder = StateGraph(State)
agent_builder.add_node("router_node", router_node)
agent_builder.add_node("standard_question_llm", standard_question_llm)
agent_builder.add_node("first_question_node", first_question_node)
agent_builder.add_node("last_qustion_node", last_qustion_node)
agent_builder.add_node("transition_llm", transition_llm)
agent_builder.add_edge(START, "router_node")

def route_from_router_node(state: dict):
    """Routing logic from the router node."""
    return state.get("next_node")

agent_builder.add_conditional_edges(
    "router_node", 
    route_from_router_node,
    {
        "first_question_node": "first_question_node",
        "transition_llm": "transition_llm",
        "standard_question_llm": "standard_question_llm",
        "last_qustion_node": "last_qustion_node"
    }
)
agent_builder.add_edge("standard_question_llm", END)
agent_builder.add_edge("first_question_node", END)
agent_builder.add_edge("last_qustion_node", END)
agent_builder.add_edge("transition_llm", END)

checkpointer = MemorySaver()
agent = agent_builder.compile(checkpointer=checkpointer)

#Cache warming, AI made

def warm_llm_cache(params_dict):
    """
    Warm LLM provider cache by pre-invoking all LLM nodes with empty messages.
    This caches system prompts at the provider level (e.g., OpenAI prompt caching).
    """
    from langchain.messages import SystemMessage
    
    # Dictionary mapping node names to their warming logic
    warmers = {
        "standard_question_llm": lambda: _warm_standard_question(params_dict),
        "transition_llm": lambda: _warm_transition(params_dict),
        # Add more nodes as needed
    }
    
    logger.info("Starting LLM cache warming")
    
    for node_name, warmer in warmers.items():
        try:
            logger.debug("Warming node: %s", node_name)
            warmer()
            logger.debug("Completed warming node: %s", node_name)
        except Exception as e:
            logger.exception("Cache warming failed for node: %s", node_name)
    
    logger.info("LLM cache warming completed")

def _warm_standard_question(params_dict):
    """Warm cache for standard question node."""
    # Override kwargs to minimize output tokens for warming
    warm_kwargs = params_dict["prompter_llm"]["kwargs"].copy()
    warm_kwargs["max_tokens"] = 10  # Minimal tokens to allow completion
    
    num_topics = len(params_dict["interview_plan"])
    logger.debug("Warming %d topics for standard questions", num_topics)
    
    for topic in params_dict["interview_plan"]:
        prompter_model = init_chat_model(
            params_dict["prompter_llm"]["model"],
            api_key=params_dict.get("api_key"),
            **warm_kwargs
        )
        prompter_model.invoke([
            SystemMessage(
                content=params_dict["prompter_llm"]["prompt"].format(
                    current_topic=topic["topic"]
                )
            )
        ])

def _warm_transition(params_dict):
    """Warm cache for transition node."""
    # Override kwargs to minimize output tokens for warming
    warm_kwargs = params_dict["transition_llm"]["kwargs"].copy()
    warm_kwargs["max_tokens"] = 10  # Minimal tokens to allow completion
    
    num_transitions = len(params_dict["interview_plan"]) - 1
    logger.debug("Warming %d transitions", num_transitions)
    
    transition_model = init_chat_model(
        params_dict["transition_llm"]["model"],
        api_key=params_dict.get("api_key"),
        **warm_kwargs
    )
    for i in range(len(params_dict["interview_plan"]) - 1):
        transition_model.invoke([
            SystemMessage(
                content=params_dict["transition_llm"]["prompt"].format(
                    previous_topic=params_dict["interview_plan"][i]["topic"],
                    next_topic=params_dict["interview_plan"][i+1]["topic"]
                )
            )
        ])


def build_graph():
    return agent