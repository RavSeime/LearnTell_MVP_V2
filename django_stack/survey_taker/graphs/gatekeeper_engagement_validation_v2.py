
from langchain.chat_models import init_chat_model
import logging
import math
import asyncio

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

from langchain.messages import AnyMessage, AIMessage, SystemMessage
from typing_extensions import TypedDict, Annotated
import operator

def indexer_progression(params: dict, topic_index: int, question_index: int):
    """Speciall progression logic for gatekeeper_engagement setup.
    inputs: params, topic_index, question_index
    outputs: [topic_index, question_index]
    just increments question index by 1, no matter what!

    Arguably bad design, but works for now.(Less code change compared to base_graph)
    """
    
    # Get the length of questions for the current topic
    current_topic_length = params["interview_plan"][topic_index]["length"]
    
 
    question_index += 1 
    
    return [topic_index, question_index]


def calculate_progress_bar(params: dict, topic_index: int):
    """Calculate progress bar percentage based on current topic vs total topics.
    
    inputs: params, topic_index
    outputs: progress_bar_percent (0-100)
    """
    total_topics = len(params["interview_plan"])
    if total_topics == 0:
        return 0
    
    # Calculate percentage: current topic / total topics * 100
    # Add 1 to topic_index since it's 0-indexed
    progress = ((topic_index + 1) / total_topics) * 100
    
    # Round down to nearest integer and clamp between 0 and 100
    return min(100, max(0, math.floor(progress)))


class State(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    interview_meta: dict   #Can add more meta variables as need be, all depends on structure
    next_node: str
    params : dict

from langchain.messages import SystemMessage

def standard_question_llm(state: dict):

    # Handle default values for interview_meta if not present
    interview_meta = state.get('interview_meta', {
        "topic_index": 0, 
        "question_index": 1,
        "gatekeeper_candle": 0,
        "just_asked_gatekeeper": False
    }) #Question index is started from 1, but topic index is started from zero
    
    # Initialize models from params
    prompter_model = init_chat_model(
        state["params"]["prompter_llm"]["model"],
        api_key=state["params"].get("api_key"),
        **state["params"]["prompter_llm"]["kwargs"]
    )
    
    validation_model = init_chat_model(
        state["params"]["validation_llm"]["model"],
        api_key=state["params"].get("api_key"),
        **state["params"]["validation_llm"]["kwargs"]
    )
    
    #Get current topic
    current_topic = state["params"]["interview_plan"][interview_meta["topic_index"]]["topic"]

    #Incrementing index logic
    interview_meta["topic_index"], interview_meta["question_index"] = indexer_progression(state["params"],
                                                                                                interview_meta["topic_index"],
                                                                                                interview_meta["question_index"]
                                                                                            )
    
    # Decrement gatekeeper_candle if it's above 0
    if interview_meta.get("gatekeeper_candle", 0) > 0:
        interview_meta["gatekeeper_candle"] -= 1
    
    logger.debug(f"[standard_question_llm] interview_meta after update: {interview_meta}")
    
    # Run both LLM calls in parallel
    async def run_parallel():
        question_task = prompter_model.ainvoke(
            [
                SystemMessage(
                    content=state["params"]["prompter_llm"]["prompt"].format(
                        current_topic=current_topic
                    )
                )
            ]
            + state["messages"]
        )
        
        validation_task = validation_model.ainvoke(
            [
                SystemMessage(
                    content=state["params"]["validation_llm"]["prompt"]
                )
            ]
            + state["messages"]
        )
        
        return await asyncio.gather(question_task, validation_task)
    
    # Execute parallel calls
    question_response, validation_response = asyncio.run(run_parallel())
    
    # Combine validation and question
    combined_content = validation_response.content.strip() + "\n\n" + question_response.content
    
    return {
        "messages": [
            AIMessage(content=combined_content)
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
    
    interview_meta["topic_index"] += 1  # Move to the next topic for transition
    interview_meta["question_index"] = 1  # Reset question index for the new topic
    #Get current topic
    topic_inital_question = state["params"]["interview_plan"][interview_meta["topic_index"]]["initial_question"]

    #Get current and next topic for transition prompt
    current_topic = state["params"]["interview_plan"][interview_meta["topic_index"]-1]["topic"]
    next_topic = state["params"]["interview_plan"][interview_meta["topic_index"]]["topic"]

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
    
    interview_meta = state.get('interview_meta', {
        "topic_index": 0, 
        "question_index": 1,
        "gatekeeper_candle": 0,
        "just_asked_gatekeeper": False
    })
    
    # You can add any specific logic for the last question here if needed
    last_question = state["params"]["end_of_interview_message"]
    
    logger.debug(f"[last_qustion_node] interview_meta: {interview_meta}, reached end of interview")
    
    return {
        "messages": [
            AIMessage(content=last_question)
        ],
    }


def engagement_llm(state: dict):
    "This checks if the user is engaged or not, returns True/False"
    
    interview_meta = state.get('interview_meta', {
        "topic_index": 0, 
        "question_index": 1,
        "gatekeeper_candle": 0,
        "just_asked_gatekeeper": False
    })
    
    # Initialize model from params
    engagement_model = init_chat_model(
        state["params"]["engagement_llm"]["model"],
        api_key=state["params"].get("api_key"),
        **state["params"]["engagement_llm"]["kwargs"]
    )

    engagement_response = engagement_model.invoke(
                [
                    SystemMessage(
                        content=state["params"]["engagement_llm"]["prompt"]
                    )
                ]
                + state["messages"]
            )
    # In engagement_llm function, return:
    engagement_response = engagement_response.content.strip().lower() == "true"

    if engagement_response:
        next_node = "gatekeeper_question_node"

        #elif not engaged and this is the last topic, go to last question
    elif not engagement_response and interview_meta["topic_index"] == len(state["params"]["interview_plan"]) - 1:
        next_node = "last_qustion_node"
    
    else: #We use else statement in case the engagmenet LLM returns something weird
        next_node = "transition_llm"

    logger.debug(f"[engagement_llm] interview_meta: {interview_meta}, engagement_response: {engagement_response}, next_node: {next_node}")

    return {"next_node": next_node}


def gatekeeper_llm(state: dict):
    """This checks if the user has more to add to the current topic, returns True/False"""
    
    interview_meta = state.get('interview_meta', {
        "topic_index": 0, 
        "question_index": 1,
        "gatekeeper_candle": 0,
        "just_asked_gatekeeper": False
    })
    
    # Initialize model from params
    gatekeeper_model = init_chat_model(
        state["params"]["gatekeeper_llm"]["model"],
        api_key=state["params"].get("api_key"),
        **state["params"]["gatekeeper_llm"]["kwargs"]
    )

    gatekeeper_response = gatekeeper_model.invoke(
                [
                    SystemMessage(
                        content=state["params"]["gatekeeper_llm"]["prompt"]
                    )
                ]
                + state["messages"]
            )
    
    # Convert LLM string response to boolean
    gatekeeper_response = gatekeeper_response.content.strip().lower() == "true"

    #Sets just_asked_gatekeeper to false after processing
    interview_meta["just_asked_gatekeeper"] = False

    if gatekeeper_response: #If user has more to add, go back to standard question set candle to gatekeeping_time
        next_node = "standard_question_llm"
        interview_meta["gatekeeper_candle"] = state["params"]["gatekeeping_time"]

    elif not gatekeeper_response and interview_meta["topic_index"] == len(state["params"]["interview_plan"]) - 1:
        next_node = "last_qustion_node"
    
    else: #Move to next topic
        next_node = "transition_llm"

    logger.debug(f"[gatekeeper_llm] interview_meta: {interview_meta}, gatekeeper_response: {gatekeeper_response}")

    #Return the state with updated interview_meta and gatekeeper_response
    return {
        "interview_meta": interview_meta,
        "next_node": next_node
    }


def gatekeeper_question_node(state: dict):
    """Ask a fixed gatekeeper question based on the current topic."""
    
    # Get interview_meta from state
    interview_meta = state.get('interview_meta', {
        "topic_index": 0, 
        "question_index": 1,
        "gatekeeper_candle": 0,
        "just_asked_gatekeeper": False
    })
    
    # Initialize validation model
    validation_model = init_chat_model(
        state["params"]["validation_llm"]["model"],
        api_key=state["params"].get("api_key"),
        **state["params"]["validation_llm"]["kwargs"]
    )
    
    # Get the gatekeeper question template
    gatekeeper_question_template = state["params"]["gatekeeper_question"]
    
    # Get the short topic from gatekeeper_topic_list based on current topic_index
    topic_dict = state["params"]["gatekeeper_topic_list"][interview_meta["topic_index"]]
    short_topic = list(topic_dict.values())[0]  # Get the first (and only) value from the dict
    
    # Format the question with the short topic
    gatekeeper_question = gatekeeper_question_template.format(short_topic=short_topic)
    
    # Update metadata to track that we just asked a gatekeeper question
    interview_meta["just_asked_gatekeeper"] = True
    
    # Get validation response
    validation_response = validation_model.invoke(
        [
            SystemMessage(
                content=state["params"]["validation_llm"]["prompt"]
            )
        ]
        + state["messages"]
    )
    
    # Combine validation and question
    combined_content = validation_response.content.strip() + "\n\n" + gatekeeper_question
    
    logger.debug(f"[gatekeeper_question_node] interview_meta after update: {interview_meta}")
    
    return {
        "messages": [
            AIMessage(content=combined_content)
        ],
        "interview_meta": interview_meta
    }


def router_node(state: dict):
    """Router node to determine the next step in the interview process."""
    
    interview_meta = state.get('interview_meta', 
                               {"topic_index": 0, 
                                "question_index": 1,
                                "gatekeeper_candle" : 0,
                                "just_asked_gatekeeper" : False,
                                "progress_bar_percent": 0
                               }) #Question index is started from 1, but topic index is started from zero
    topic_index = interview_meta["topic_index"]
    question_index = interview_meta["question_index"]
    just_asked_gatekeeper = interview_meta.get("just_asked_gatekeeper", False)
    gatekeeper_candle = interview_meta.get("gatekeeper_candle", 0)

    # Calculate progress bar percentage
    interview_meta["progress_bar_percent"] = calculate_progress_bar(state["params"], topic_index)

    banned_topics = [int(x) for x in state["params"].get("topics_banned_from_gatekeeping", [])] #Topics where we dont do engagement check, ensure all are ints
    
    # Debug type checking
    logger.debug(f"[router_node] topic_index={topic_index} (type={type(topic_index)}), banned_topics={banned_topics} (types={[type(x) for x in banned_topics]}), in_check={topic_index in banned_topics}")

    #Check if we just asked a gatekeeper question
    if just_asked_gatekeeper:
        next_node = "gatekeeper_llm"
    
    #Check if its the first question overall
    elif topic_index == 0 and question_index == 1:
        next_node = "first_question_node"
    
    #Check if gatekeeper_candle is active (need to ask more questions before engagement check)
    elif gatekeeper_candle > 0:
        next_node = "standard_question_llm"

    
    #Check if its we should check engagmenet. Check engament if current_question index is above topic lenght and gatekeeper candle is not 0
    elif question_index >= state["params"]["interview_plan"][topic_index]["length"] and gatekeeper_candle == 0 and topic_index not in banned_topics:
        next_node = "engagement_llm"
    
    elif question_index >= state["params"]["interview_plan"][topic_index]["length"] and gatekeeper_candle == 0 and topic_index in banned_topics:
        #Skip engagement check and go to transition directly
        next_node = "transition_llm"
    
    else:
        next_node = "standard_question_llm"

    logger.debug(f"[router_node] interview_meta: {interview_meta}, next_node: {next_node}")

    return {"next_node": next_node, "interview_meta": interview_meta}


from typing import Literal
from langgraph.graph import StateGraph, START, END

from langgraph.checkpoint.memory import MemorySaver

agent_builder = StateGraph(State)
agent_builder.add_node("router_node", router_node)
agent_builder.add_node("standard_question_llm", standard_question_llm)
agent_builder.add_node("first_question_node", first_question_node)
agent_builder.add_node("last_qustion_node", last_qustion_node)
agent_builder.add_node("transition_llm", transition_llm)
agent_builder.add_node("engagement_llm", engagement_llm)
agent_builder.add_node("gatekeeper_question_node", gatekeeper_question_node)
agent_builder.add_node("gatekeeper_llm", gatekeeper_llm)
agent_builder.add_edge(START, "router_node")


def route_function(state: dict):
    """Routing logic from the router node."""
    return state.get("next_node")

agent_builder.add_conditional_edges(
    "engagement_llm",
    route_function,
    {
        "gatekeeper_question_node": "gatekeeper_question_node",
        "last_qustion_node": "last_qustion_node",
        "transition_llm": "transition_llm"
    }
)


agent_builder.add_conditional_edges(
    "router_node", 
    route_function,
    {
        "first_question_node": "first_question_node",
        "standard_question_llm": "standard_question_llm",
        "last_qustion_node": "last_qustion_node",
        "engagement_llm": "engagement_llm",
        "transition_llm": "transition_llm",
        "gatekeeper_question_node": "gatekeeper_question_node",
        "gatekeeper_llm": "gatekeeper_llm"
    }
)
agent_builder.add_conditional_edges(
    "gatekeeper_llm",
    route_function,
    {
        "standard_question_llm": "standard_question_llm",
        "transition_llm": "transition_llm",
        "last_qustion_node": "last_qustion_node"
    }
)

agent_builder.add_edge("gatekeeper_question_node", END)
agent_builder.add_edge("standard_question_llm", END)
agent_builder.add_edge("first_question_node", END)
agent_builder.add_edge("last_qustion_node", END)
agent_builder.add_edge("transition_llm", END)

checkpointer = MemorySaver()
agent = agent_builder.compile(checkpointer=checkpointer)

#Cache warming, AI made

async def warm_llm_cache(params_dict):
    """
    Warm LLM provider cache by pre-invoking all LLM nodes with empty messages.
    This caches system prompts at the provider level (e.g., OpenAI prompt caching).
    """
    from langchain.messages import SystemMessage
    
    logger.info("Starting LLM cache warming")
    
    # Run all warming tasks in parallel
    await asyncio.gather(
        _warm_standard_question(params_dict),
        _warm_transition(params_dict),
        _warm_engagement(params_dict),
        _warm_gatekeeper(params_dict),
        _warm_validation(params_dict),
        return_exceptions=True
    )
    
    logger.info("LLM cache warming completed")

async def _warm_standard_question(params_dict):
    """Warm cache for standard question node."""
    # Override kwargs to minimize output tokens for warming
    warm_kwargs = params_dict["prompter_llm"]["kwargs"].copy()
    warm_kwargs["max_tokens"] = 110  # Minimal tokens to allow completion
    
    num_topics = len(params_dict["interview_plan"])
    logger.debug("Warming %d topics for standard questions", num_topics)
    
    prompter_model = init_chat_model(
        params_dict["prompter_llm"]["model"],
        api_key=params_dict.get("api_key"),
        **warm_kwargs
    )
    
    # Run all topic warming in parallel
    tasks = [
        prompter_model.ainvoke([
            SystemMessage(
                content=params_dict["prompter_llm"]["prompt"].format(
                    current_topic=topic["topic"]
                )
            )
        ])
        for topic in params_dict["interview_plan"]
    ]
    
    await asyncio.gather(*tasks)

async def _warm_transition(params_dict):
    """Warm cache for transition node."""
    # Override kwargs to minimize output tokens for warming
    warm_kwargs = params_dict["transition_llm"]["kwargs"].copy()
    warm_kwargs["max_tokens"] = 110  # Minimal tokens to allow completion
    
    num_transitions = len(params_dict["interview_plan"]) - 1
    logger.debug("Warming %d transitions", num_transitions)
    
    transition_model = init_chat_model(
        params_dict["transition_llm"]["model"],
        api_key=params_dict.get("api_key"),
        **warm_kwargs
    )
    
    # Run all transition warming in parallel
    tasks = [
        transition_model.ainvoke([
            SystemMessage(
                content=params_dict["transition_llm"]["prompt"].format(
                    previous_topic=params_dict["interview_plan"][i]["topic"],
                    next_topic=params_dict["interview_plan"][i+1]["topic"]
                )
            )
        ])
        for i in range(len(params_dict["interview_plan"]) - 1)
    ]
    
    await asyncio.gather(*tasks)

async def _warm_engagement(params_dict):
    """Warm cache for engagement LLM node."""
    warm_kwargs = params_dict["engagement_llm"]["kwargs"].copy()
    warm_kwargs["max_tokens"] = 110
    
    logger.debug("Warming engagement LLM")
    
    engagement_model = init_chat_model(
        params_dict["engagement_llm"]["model"],
        api_key=params_dict.get("api_key"),
        **warm_kwargs
    )
    await engagement_model.ainvoke([
        SystemMessage(content=params_dict["engagement_llm"]["prompt"])
    ])

async def _warm_gatekeeper(params_dict):
    """Warm cache for gatekeeper LLM node."""
    warm_kwargs = params_dict["gatekeeper_llm"]["kwargs"].copy()
    warm_kwargs["max_tokens"] = 110
    
    logger.debug("Warming gatekeeper LLM")
    
    gatekeeper_model = init_chat_model(
        params_dict["gatekeeper_llm"]["model"],
        api_key=params_dict.get("api_key"),
        **warm_kwargs
    )
    await gatekeeper_model.ainvoke([
        SystemMessage(content=params_dict["gatekeeper_llm"]["prompt"])
    ])

async def _warm_validation(params_dict):
    """Warm cache for validation LLM node."""
    warm_kwargs = params_dict["validation_llm"]["kwargs"].copy()
    warm_kwargs["max_tokens"] = 110
    
    logger.debug("Warming validation LLM")
    
    validation_model = init_chat_model(
        params_dict["validation_llm"]["model"],
        api_key=params_dict.get("api_key"),
        **warm_kwargs
    )
    await validation_model.ainvoke([
        SystemMessage(content=params_dict["validation_llm"]["prompt"])
    ])


def build_graph():
    return agent