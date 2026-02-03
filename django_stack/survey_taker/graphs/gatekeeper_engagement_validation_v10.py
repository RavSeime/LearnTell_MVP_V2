
from langchain.chat_models import init_chat_model
import logging
import math
import asyncio
import json

logger = logging.getLogger(__name__)

"""
V6 introduces the ability for moderators to update the prompt based on the analysis of the previous attempt.
"""

from langchain.messages import AnyMessage, AIMessage, SystemMessage, HumanMessage
from typing_extensions import TypedDict, Annotated
import operator

def get_last_n_messages(state: dict, n: int = 2) -> list[AnyMessage]:
    """Get the last n messages from state."""
    return state["messages"][-n:] if len(state["messages"]) >= n else state["messages"]

def parse_decision_from_json(response_content: str, default: bool = False) -> bool:
    """Parse decision from JSON response with 'analysis' and 'decision' fields.

    Matches the format used by moderator LLMs: {"analysis": "...", "decision": true/false}
    """
    content = response_content.strip()

    try:
        parsed = json.loads(content)
        if "decision" in parsed:
            return bool(parsed["decision"])
    except json.JSONDecodeError:
        pass

    # Fallback: backward compatibility for plain true/false responses
    if content.lower() in ('true', 'false'):
        return content.lower() == 'true'

    logger.warning(f"Could not parse decision from response: {content[:100]}...")
    return default

async def moderate_with_retry(
    generation_func,
    moderator_model,
    moderator_prompt: str,
    original_prompt: str,
    max_retries: int,
    llm_name: str,
    failed_moderation_message: str,
    update_prompt_func=None,
    context_messages=None
):
    """
    Generate content and moderate it with retries.
    
    Args:
        generation_func: Async function that generates content, returns AIMessage or similar
        moderator_model: The moderator LLM model
        moderator_prompt: The moderator's system prompt template (with {original_prompt} placeholder)
        original_prompt: The original LLM's system prompt
        max_retries: Maximum number of retry attempts
        llm_name: Name of the LLM for logging
        failed_moderation_message: Template message to append when moderation fails
        update_prompt_func: Optional function to update the prompt with analysis (takes updated_prompt string)
        context_messages: Optional list of messages that provide context (the messages the original LLM was replying to)
        
    Returns:
        The generated content that passed moderation (or last attempt if all fail)
    """
    for attempt in range(max_retries):
        # Generate content
        generated_content = await generation_func()
        
        # Build moderation messages: system prompt, then context messages (including human message), then AI response
        moderation_messages = [
            SystemMessage(
                content=moderator_prompt.format(original_prompt=original_prompt)
            )
        ]
        
        # Add context messages if provided (these include the human message the original LLM was replying to)
        if context_messages:
            moderation_messages.extend(context_messages)
        
        # Add the generated AI message
        moderation_messages.append(AIMessage(content=generated_content.content))
        
        # Moderate the content
        moderation_result = await moderator_model.ainvoke(moderation_messages)
        
        # Parse JSON response
        # Note: The moderator returns JSON with "analysis" first, then "passed" (decision)
        # Field order doesn't matter for parsing, but the prompt instructs analysis before passed
        try:
            moderation_data = json.loads(moderation_result.content.strip())
            is_valid = moderation_data.get("passed", False)
            analysis = moderation_data.get("analysis", "No analysis provided")
        except (json.JSONDecodeError, AttributeError):
            # Fallback for non-JSON responses (backward compatibility)
            is_valid = moderation_result.content.strip().lower() == "true"
            analysis = "Moderation check failed" if not is_valid else ""
        
        if is_valid:
            logger.debug(f"[{llm_name}] Passed moderation on attempt {attempt + 1}")
            return generated_content
        else:
            logger.warning(f"[{llm_name}] Failed moderation on attempt {attempt + 1}/{max_retries}. Analysis: {analysis}")
            
            # Update the prompt with the analysis for the next retry (if not the last attempt)
            if analysis and not is_valid and attempt < max_retries - 1 and update_prompt_func:
                updated_prompt = original_prompt + failed_moderation_message + analysis
                generation_func = update_prompt_func(updated_prompt)
    
    # If all retries failed, return the last attempt
    logger.error(f"[{llm_name}] All {max_retries} moderation attempts failed. Using last attempt.")
    return generated_content

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

def validation_decision_llm(state: dict):
    """Decides whether the user's message deserves validation."""
    
    # Initialize model from params
    validation_decision_model = init_chat_model(
        state["params"]["validation_decision_llm"]["model"],
        api_key=state["params"].get("api_key"),
        **state["params"]["validation_decision_llm"]["kwargs"]
    )
    
    # Get the last user message (should be the most recent HumanMessage)
    decision_response = validation_decision_model.invoke(
        [
            SystemMessage(
                content=state["params"]["validation_decision_llm"]["prompt"]
            )
        ]
        + state["messages"]
    )
    
    # Convert response to boolean
    deserves_validation = parse_decision_from_json(decision_response.content, default=False)
    
    logger.debug(f"[validation_decision_llm] deserves_validation: {deserves_validation}")
    
    return deserves_validation

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
    
    # Initialize moderator models
    prompter_moderator_model = init_chat_model(
        state["params"]["prompter_moderator_llm"]["model"],
        api_key=state["params"].get("api_key"),
        **state["params"]["prompter_moderator_llm"]["kwargs"]
    )
    
    validation_moderator_model = init_chat_model(
        state["params"]["validation_moderator_llm"]["model"],
        api_key=state["params"].get("api_key"),
        **state["params"]["validation_moderator_llm"]["kwargs"]
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
    
    # Check if validation should be added before followup
    validation_before_followup = state["params"].get("validation_before_followup", False)
    
    # Prepare generation functions for moderation with prompt update capability
    base_question_prompt = state["params"]["prompter_llm"]["prompt"].format(current_topic=current_topic)
    base_validation_prompt = state["params"]["validation_llm"]["prompt"]
    
    question_prompt = [base_question_prompt]
    validation_prompt = [base_validation_prompt]
    
    async def generate_question():
        return await prompter_model.ainvoke(
            [
                SystemMessage(content=question_prompt[0])
            ]
            + state["messages"]
        )
    
    async def generate_validation():
        return await validation_model.ainvoke(
            [
                SystemMessage(content=validation_prompt[0])
            ]
            + get_last_n_messages(state, 2)
        )
    
    def update_question_prompt(updated_prompt):
        question_prompt[0] = updated_prompt
        return generate_question
    
    def update_validation_prompt(updated_prompt):
        validation_prompt[0] = updated_prompt
        return generate_validation
    
    # Prompter pipeline: question generation + moderation
    async def run_prompter_pipeline():
        return await moderate_with_retry(
            generation_func=generate_question,
            moderator_model=prompter_moderator_model,
            moderator_prompt=state["params"]["prompter_moderator_llm"]["prompt"],
            original_prompt=base_question_prompt,
            max_retries=state["params"]["prompter_moderator_max_retries"],
            llm_name="prompter_llm",
            failed_moderation_message=state["params"].get("prompter_failed_moderation_message", "\n\nIMPORTANT - Your previous attempt failed moderation. Please address the following issue:\n"),
            update_prompt_func=update_question_prompt,
            context_messages=get_last_n_messages(state, 2)
        )
    
    # Validation pipeline: decision → generation → moderation
    async def run_validation_pipeline():
        if not validation_before_followup:
            return None
        
        # Check if validation is deserved (run in executor since it's synchronous)
        import concurrent.futures
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            should_validate = await loop.run_in_executor(executor, validation_decision_llm, state)
        
        if not should_validate:
            return None
        
        # Generate and moderate validation
        return await moderate_with_retry(
            generation_func=generate_validation,
            moderator_model=validation_moderator_model,
            moderator_prompt=state["params"]["validation_moderator_llm"]["prompt"],
            original_prompt=base_validation_prompt,
            max_retries=state["params"]["validation_moderator_max_retries"],
            llm_name="validation_llm",
            failed_moderation_message=state["params"].get("validation_failed_moderation_message", "\n\nIMPORTANT - Your previous attempt failed moderation. Please address the following issue:\n"),
            update_prompt_func=update_validation_prompt,
            context_messages=get_last_n_messages(state, 2)
        )
    
    # Run both pipelines in parallel
    async def run_both_pipelines():
        prompter_task = run_prompter_pipeline()
        validation_task = run_validation_pipeline()
        return await asyncio.gather(prompter_task, validation_task)
    
    # Execute both pipelines in parallel
    question_response, validation_response = asyncio.run(run_both_pipelines())
    
    # Combine results
    if validation_response:
        # Combine validation and question
        combined_content = validation_response.content.strip() + "\n\n" + question_response.content
    else:
        # Just use the question
        combined_content = question_response.content
    
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
    
    # Prepare async function for transition phrase generation
    async def generate_transition():
        return await transition_model.ainvoke(
            [
                SystemMessage(
                    content=state["params"]["transition_llm"]["prompt"].format(
                        previous_topic=current_topic,
                        next_topic=next_topic
                    )
                )
            ]
            + get_last_n_messages(state, 2)
        )
    
    # Check if validation should be added before transition and run decision check in parallel with transition
    validation_before_transition = state["params"].get("validation_before_transition", False)
    
    async def check_validation_decision():
        if validation_before_transition:
            # Make validation_decision_llm async by wrapping the synchronous call
            # Since validation_decision_llm uses invoke(), we'll run it in executor
            import concurrent.futures
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                should_validate = await loop.run_in_executor(executor, validation_decision_llm, state)
            return should_validate
        return False
    
    # Start both transition generation and validation decision check in parallel
    async def run_initial_parallel():
        logger.debug("[transition_llm] Starting transition phrase generation and validation decision check in parallel")
        transition_task = generate_transition()
        validation_decision_task = check_validation_decision()
        transition_phrase, should_validate = await asyncio.gather(transition_task, validation_decision_task)
        logger.debug(f"[transition_llm] Both tasks completed. should_validate: {should_validate}")
        return transition_phrase, should_validate
    
    transition_phrase, should_validate = asyncio.run(run_initial_parallel())
    
    # Conditionally add validation and run in parallel with transition (if needed)
    if should_validate:
        # Initialize validation model
        validation_model = init_chat_model(
            state["params"]["validation_llm"]["model"],
            api_key=state["params"].get("api_key"),
            **state["params"]["validation_llm"]["kwargs"]
        )
        
        # Initialize validation moderator model
        validation_moderator_model = init_chat_model(
            state["params"]["validation_moderator_llm"]["model"],
            api_key=state["params"].get("api_key"),
            **state["params"]["validation_moderator_llm"]["kwargs"]
        )
        
        # Prepare generation function for validation with prompt update capability
        base_validation_prompt = state["params"]["validation_llm"]["prompt"]
        validation_prompt = [base_validation_prompt]
        
        async def generate_validation():
            return await validation_model.ainvoke(
                [
                    SystemMessage(content=validation_prompt[0])
                ]
                + state["messages"]
            )
        
        def update_validation_prompt(updated_prompt):
            validation_prompt[0] = updated_prompt
            return generate_validation
        
        # Get validation response with moderation
        async def run_validation_with_moderation():
            return await moderate_with_retry(
                generation_func=generate_validation,
                moderator_model=validation_moderator_model,
                moderator_prompt=state["params"]["validation_moderator_llm"]["prompt"],
                original_prompt=base_validation_prompt,
                max_retries=state["params"]["validation_moderator_max_retries"],
                llm_name="validation_llm_transition",
                failed_moderation_message=state["params"].get("validation_failed_moderation_message", "\n\nIMPORTANT - Your previous attempt failed moderation. Please address the following issue:\n"),
                update_prompt_func=update_validation_prompt,
                context_messages=state["messages"]
            )
        
        # Generate validation with moderation (transition is already done)
        validation_response = asyncio.run(run_validation_with_moderation())
        
        # Combine validation, transition, and question
        response = validation_response.content.strip() + "\n\n" + transition_phrase.content + "\n\n" + topic_inital_question
    else:
        # Just use transition and question (transition is already done)
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
                + get_last_n_messages(state, 2)
            )
    # Convert LLM string response to boolean
    engagement_response = parse_decision_from_json(engagement_response.content, default=False)

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
                + get_last_n_messages(state, 2)
            )
    
    # Convert LLM string response to boolean
    gatekeeper_response = parse_decision_from_json(gatekeeper_response.content, default=False)

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
    
    # Initialize validation moderator model
    validation_moderator_model = init_chat_model(
        state["params"]["validation_moderator_llm"]["model"],
        api_key=state["params"].get("api_key"),
        **state["params"]["validation_moderator_llm"]["kwargs"]
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
    
    # Check if validation should be added before gatekeeper question
    # Use validation_before_followup for gatekeeper questions as well
    validation_before_followup = state["params"].get("validation_before_followup", False)
    should_validate = False
    
    if validation_before_followup:
        # Check if validation is deserved
        should_validate = validation_decision_llm(state)
    
    # Conditionally add validation
    if should_validate:
        # Prepare generation function for validation with prompt update capability
        base_validation_prompt = state["params"]["validation_llm"]["prompt"]
        validation_prompt = [base_validation_prompt]
        
        async def generate_validation():
            return await validation_model.ainvoke(
                [
                    SystemMessage(content=validation_prompt[0])
                ]
                + get_last_n_messages(state, 2)
            )
        
        def update_validation_prompt(updated_prompt):
            validation_prompt[0] = updated_prompt
            return generate_validation
        
        # Get validation response with moderation
        async def run_with_moderation():
            return await moderate_with_retry(
                generation_func=generate_validation,
                moderator_model=validation_moderator_model,
                moderator_prompt=state["params"]["validation_moderator_llm"]["prompt"],
                original_prompt=base_validation_prompt,
                max_retries=state["params"]["validation_moderator_max_retries"],
                llm_name="validation_llm_gatekeeper",
                failed_moderation_message=state["params"].get("validation_failed_moderation_message", "\n\nIMPORTANT - Your previous attempt failed moderation. Please address the following issue:\n"),
                update_prompt_func=update_validation_prompt,
                context_messages=get_last_n_messages(state, 2)
            )
        
        validation_response = asyncio.run(run_with_moderation())
        
        # Combine validation and question
        combined_content = validation_response.content.strip() + "\n\n" + gatekeeper_question
    else:
        # Just use the question
        combined_content = gatekeeper_question
    
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
        _warm_validation_decision(params_dict),
        _warm_prompter_moderator(params_dict),
        _warm_validation_moderator(params_dict),
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

async def _warm_validation_decision(params_dict):
    """Warm cache for validation decision LLM node."""
    if "validation_decision_llm" not in params_dict:
        return
    
    warm_kwargs = params_dict["validation_decision_llm"]["kwargs"].copy()
    warm_kwargs["max_tokens"] = 10
    
    logger.debug("Warming validation decision LLM")
    
    validation_decision_model = init_chat_model(
        params_dict["validation_decision_llm"]["model"],
        api_key=params_dict.get("api_key"),
        **warm_kwargs
    )
    await validation_decision_model.ainvoke([
        SystemMessage(content=params_dict["validation_decision_llm"]["prompt"])
    ])

async def _warm_prompter_moderator(params_dict):
    """Warm cache for prompter moderator LLM node."""
    if "prompter_moderator_llm" not in params_dict:
        return
    
    warm_kwargs = params_dict["prompter_moderator_llm"]["kwargs"].copy()
    warm_kwargs["max_tokens"] = 200  # Enough tokens for JSON response with analysis
    
    logger.debug("Warming prompter moderator LLM")
    
    # Get a sample topic for formatting the prompt
    sample_topic = params_dict["interview_plan"][0]["topic"] if params_dict["interview_plan"] else "sample topic"
    sample_original_prompt = params_dict["prompter_llm"]["prompt"].format(current_topic=sample_topic)
    
    prompter_moderator_model = init_chat_model(
        params_dict["prompter_moderator_llm"]["model"],
        api_key=params_dict.get("api_key"),
        **warm_kwargs
    )
    await prompter_moderator_model.ainvoke([
        SystemMessage(
            content=params_dict["prompter_moderator_llm"]["prompt"].format(
                original_prompt=sample_original_prompt
            )
        )
    ])

async def _warm_validation_moderator(params_dict):
    """Warm cache for validation moderator LLM node."""
    if "validation_moderator_llm" not in params_dict:
        return
    
    warm_kwargs = params_dict["validation_moderator_llm"]["kwargs"].copy()
    warm_kwargs["max_tokens"] = 50  # Minimal tokens for moderation response
    
    logger.debug("Warming validation moderator LLM")
    
    validation_moderator_model = init_chat_model(
        params_dict["validation_moderator_llm"]["model"],
        api_key=params_dict.get("api_key"),
        **warm_kwargs
    )
    await validation_moderator_model.ainvoke([
        SystemMessage(
            content=params_dict["validation_moderator_llm"]["prompt"].format(
                original_prompt=params_dict["validation_llm"]["prompt"]
            )
        )
    ])


def build_graph():
    return agent