# Global model cache to avoid reinitializing on every request
_model_cache = {}

def warm_openai_cache(params, topic_index, conversation_log, key):
    """Warm OpenAI's prompt cache for a specific topic by sending a minimal request.
    This populates the cache with system prompt + conversation history without generating a full response.
    """
    from langchain.chat_models import init_chat_model
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
    
    # Cache key based on model config
    cache_key = (
        params["prompter_llm"]["model"],
        params["prompter_llm"]["model_provider"],
        tuple(sorted(params["prompter_llm"]["kwargs"].items()))
    )
    
    # Get or create model
    if cache_key in _model_cache:
        prompt_llm = _model_cache[cache_key]
    else:
        model_kwargs = {**params["prompter_llm"]["kwargs"], "api_key": key}
        prompt_llm = init_chat_model(
            model=params["prompter_llm"]["model"],
            model_provider=params["prompter_llm"]["model_provider"],
            **model_kwargs
        )
        _model_cache[cache_key] = prompt_llm
    
    # Build messages with the target topic's system prompt
    system_prompt = params["prompter_llm"]["prompt"].format(
        current_topic=params["interview_plan"][topic_index]["topic"]
    )
    
    messages = [SystemMessage(content=system_prompt)]
    messages.extend(
        AIMessage(content=entry['content']) if entry.get('is_question') in ('1', 1, True)
        else HumanMessage(content=entry['content'])
        for entry in conversation_log
    )
    
    # Send minimal request to warm cache (only generate 1 token)
    try:
        prompt_llm.invoke(messages, max_tokens=1)
        print(f"[DEBUG] Warmed OpenAI cache for topic {topic_index}")
    except Exception as e:
        print(f"[DEBUG] Cache warming failed (non-critical): {e}")

def get_transition_question(params, next_topic_index, conversation_log, key):
    """Generate a transition question when moving to a new topic."""
    import time
    from langchain.chat_models import init_chat_model
    from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
    
    # Get previous and next topic names
    previous_topic = params["interview_plan"][next_topic_index - 1]["topic"] if next_topic_index > 0 else "introduction"
    next_topic = params["interview_plan"][next_topic_index]["topic"]
    
    # Format transition prompt
    transition_prompt = params["transition_llm"]["prompt"].format(
        previous_topic=previous_topic,
        next_topic=next_topic
    )
    
    # Cache key for transition model
    cache_key = (
        params["transition_llm"]["model"],
        params["transition_llm"]["model_provider"],
        tuple(sorted(params["transition_llm"]["kwargs"].items()))
    )
    
    # Check cache or create model
    if cache_key in _model_cache:
        transition_llm = _model_cache[cache_key]
    else:
        model_kwargs = {**params["transition_llm"]["kwargs"], "api_key": key}
        transition_llm = init_chat_model(
            model=params["transition_llm"]["model"],
            model_provider=params["transition_llm"]["model_provider"],
            **model_kwargs
        )
        _model_cache[cache_key] = transition_llm
    
    # Generate transition
    messages = [SystemMessage(content=transition_prompt)]
    messages.extend(
        AIMessage(content=entry['content']) if entry.get('is_question') in ('1', 1, True)
        else HumanMessage(content=entry['content'])
        for entry in conversation_log
    )

    response = transition_llm.invoke(messages)
    return response.content

def test_create_agent(params, key):
    from langchain_openai import ChatOpenAI
    from langgraph.checkpoint.memory import InMemorySaver
    test_agent = ChatOpenAI(model = "gpt-5",
                            api_key = key,
                            checkpointer = InMemorySaver())
    return "bingus"

def get_response(params, current_topic_index, conversation_log, key, debug_caching=True):
    import time
    from langchain_openai import ChatOpenAI
    from langchain.chat_models import init_chat_model
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

    t_start = time.time()
    
    # Cache key based on model config
    cache_key = (
        params["prompter_llm"]["model"],
        params["prompter_llm"]["model_provider"],
        tuple(sorted(params["prompter_llm"]["kwargs"].items()))
    )
    
    #Logic for picking out right topic_param, based on conversation log


    t_before_init = time.time()
    # Check cache first
    if cache_key in _model_cache:
        prompt_llm = _model_cache[cache_key]
        print(f"[TIMING] init_chat_model: 0.00ms (cached)")
    else:
        # Add API key to kwargs and unpack them
        model_kwargs = {**params["prompter_llm"]["kwargs"], "api_key": key}
        
        prompt_llm = init_chat_model(
            model = params["prompter_llm"]["model"],
            model_provider = params["prompter_llm"]["model_provider"],
            **model_kwargs
        )
        _model_cache[cache_key] = prompt_llm
        t_after_init = time.time()
        print(f"[TIMING] init_chat_model: {(t_after_init - t_before_init) * 1000:.2f}ms (created)")




    t_before_messages = time.time()

    system_prompt = params["prompter_llm"]["prompt"].format(
        current_topic = params["interview_plan"][current_topic_index]["topic"]
    )

    messages = [SystemMessage(content=system_prompt)]
    messages.extend(
        AIMessage(content=entry['content']) if entry.get('is_question') in ('1', 1, True)
        else HumanMessage(content=entry['content'])
        for entry in conversation_log
    )
    t_after_messages = time.time()
    print(f"[TIMING] Building messages ({len(messages)} msgs): {(t_after_messages - t_before_messages) * 1000:.2f}ms")
    
    # Invoke the LLM
    t_before_invoke = time.time()
    response = prompt_llm.invoke(messages)
    t_after_invoke = time.time()
    print(f"[TIMING] LLM invoke: {(t_after_invoke - t_before_invoke) * 1000:.2f}ms")
    
    # === DEBUG START (Set debug_caching=False to disable) ===
    if debug_caching:
        usage = getattr(response, 'usage_metadata', {})
        if usage:
            input_tokens = usage.get('input_tokens', 0)
            output_tokens = usage.get('output_tokens', 0)
            cached = usage.get('input_token_details', {}).get('cache_read', 0)
            
            if cached > 0:
                cache_pct = (cached / input_tokens * 100) if input_tokens > 0 else 0
                savings = f"{cache_pct:.0f}% cached"
            else:
                savings = "No cache yet" if input_tokens < 1024 else "No cache hit"
            
            print(f"[TOKENS] In:{input_tokens} Out:{output_tokens} Cache:{cached} | {savings}")
    # === DEBUG END ===
    
    # Return the content string
    return response.content

def get_gatekeeper_response(params, conversation_log, key, debug_caching=True):
    """
    Evaluate if the participant indicates they have more information to add.
    Returns True if participant has more to add, False if they're done.
    """
    import time
    from langchain.chat_models import init_chat_model
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
    
    t_start = time.time()
    
    # Cache key based on model config
    cache_key = (
        params["gatekeeper_llm"]["model"],
        params["gatekeeper_llm"]["model_provider"],
        tuple(sorted(params["gatekeeper_llm"]["kwargs"].items()))
    )
    
    t_before_init = time.time()
    # Check cache first
    if cache_key in _model_cache:
        gatekeeper_llm = _model_cache[cache_key]
        print(f"[TIMING] init_chat_model (gatekeeper): 0.00ms (cached)")
    else:
        # Add API key to kwargs and unpack them
        model_kwargs = {**params["gatekeeper_llm"]["kwargs"], "api_key": key}
        
        gatekeeper_llm = init_chat_model(
            model=params["gatekeeper_llm"]["model"],
            model_provider=params["gatekeeper_llm"]["model_provider"],
            **model_kwargs
        )
        _model_cache[cache_key] = gatekeeper_llm
        t_after_init = time.time()
        print(f"[TIMING] init_chat_model (gatekeeper): {(t_after_init - t_before_init) * 1000:.2f}ms (created)")
    
    t_before_messages = time.time()
    
    # Use the gatekeeper prompt
    system_prompt = params["gatekeeper_llm"]["prompt"]
    
    messages = [SystemMessage(content=system_prompt)]
    messages.extend(
        AIMessage(content=entry['content']) if entry.get('is_question') in ('1', 1, True)
        else HumanMessage(content=entry['content'])
        for entry in conversation_log
    )
    t_after_messages = time.time()
    print(f"[TIMING] Building messages for gatekeeper ({len(messages)} msgs): {(t_after_messages - t_before_messages) * 1000:.2f}ms")
    
    # Debug: Show last few messages to verify gatekeeper question is included
    print(f"[DEBUG GATEKEEPER] Last 3 messages being sent to LLM:")
    for msg in messages[-3:]:
        msg_type = type(msg).__name__
        content_preview = msg.content[:80] if hasattr(msg, 'content') else str(msg)[:80]
        print(f"  - {msg_type}: {content_preview}")
    
    # Invoke the LLM
    t_before_invoke = time.time()
    response = gatekeeper_llm.invoke(messages)
    t_after_invoke = time.time()
    print(f"[TIMING] Gatekeeper LLM invoke: {(t_after_invoke - t_before_invoke) * 1000:.2f}ms")
    
    # Parse the response - look for True or False
    response_text = response.content.strip().upper()
    
    # Check for True/False in the response
    has_more = False
    if "TRUE" in response_text and "FALSE" not in response_text:
        has_more = True
    elif "FALSE" in response_text:
        has_more = False
    else:
        # Default: if unclear, assume False (no more to add)
        print(f"[DEBUG] Gatekeeper response unclear: {response.content}, defaulting to False")
        has_more = False
    
    if debug_caching:
        print(f"[DEBUG] Gatekeeper check result: has_more={has_more}")
    
    return has_more 

def check_engagement(params, current_topic_index, conversation_log, key, debug_caching=True):
    """
    Check if engagement is low and should move to next topic.
    Returns True if engagement is low (should move on), False if engagement is good (continue current topic).
    Uses structured output to force boolean response.
    """
    import time
    from langchain.chat_models import init_chat_model
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
    from pydantic import BaseModel, Field
    
    # Define structured output schema
    class EngagementResponse(BaseModel):
        """Response indicating whether engagement is low."""
        low_engagement: bool = Field(
            description="True if engagement is low and should move to next topic, False if engagement is good and should continue current topic"
        )
    
    t_start = time.time()
    
    # Cache key based on model config
    cache_key = (
        params["engagement_llm"]["model"],
        params["engagement_llm"]["model_provider"],
        tuple(sorted(params["engagement_llm"]["kwargs"].items()))
    )
    
    t_before_init = time.time()
    # Always create fresh model with structured output to avoid caching issues
    # Add API key to kwargs and unpack them
    model_kwargs = {**params["engagement_llm"]["kwargs"], "api_key": key}
    
    engagement_llm = None
    try:
        # print(f"[DEBUG] Initializing engagement model: {params['engagement_llm']['model']} from {params['engagement_llm']['model_provider']}")
        base_llm = init_chat_model(
            model=params["engagement_llm"]["model"],
            model_provider=params["engagement_llm"]["model_provider"],
            **model_kwargs
        )
        # print(f"[DEBUG] Base model created, binding structured output...")
        # print(f"[DEBUG] EngagementResponse class: {EngagementResponse}")
        # print(f"[DEBUG] EngagementResponse fields: {EngagementResponse.__fields__ if hasattr(EngagementResponse, '__fields__') else EngagementResponse.model_fields if hasattr(EngagementResponse, 'model_fields') else 'N/A'}")
        # Bind structured output
        try:
            engagement_llm = base_llm.with_structured_output(EngagementResponse)
            # print(f"[DEBUG] Structured output bound successfully")
            # print(f"[DEBUG] Bound LLM type: {type(engagement_llm)}")
        except Exception as bind_error:
            print(f"[DEBUG] Error binding structured output: {type(bind_error).__name__}: {bind_error}")
            import traceback
            print(f"[DEBUG] Bind error traceback: {traceback.format_exc()}")
            raise
        t_after_init = time.time()
        print(f"[TIMING] init_chat_model (engagement): {(t_after_init - t_before_init) * 1000:.2f}ms (created)")
    except Exception as init_error:
        print(f"[DEBUG] Failed to initialize engagement model: {type(init_error).__name__}: {init_error}")
        import traceback
        print(f"[DEBUG] Traceback: {traceback.format_exc()}")
        # Will fall through to fallback approach
    
    t_before_messages = time.time()
    # print(f"[DEBUG] About to build messages, current_topic_index: {current_topic_index}")
    # print(f"[DEBUG] interview_plan length: {len(params.get('interview_plan', []))}")
    
    # Format engagement prompt with current topic
    try:
        current_topic = params["interview_plan"][current_topic_index]["topic"]
        # print(f"[DEBUG] Current topic retrieved: {current_topic[:100] if len(current_topic) > 100 else current_topic}")
    except Exception as topic_error:
        print(f"[DEBUG] Error getting current topic: {type(topic_error).__name__}: {topic_error}")
        raise
    
    try:
        # Use replace instead of format to avoid conflicts with JSON braces in prompt
        engagement_prompt = params["engagement_llm"]["prompt"].replace("{current_topic}", current_topic)
        # print(f"[DEBUG] Engagement prompt formatted successfully, length: {len(engagement_prompt)}")
    except Exception as prompt_error:
        print(f"[DEBUG] Error formatting prompt: {type(prompt_error).__name__}: {prompt_error}")
        raise
    
    try:
        messages = [SystemMessage(content=engagement_prompt)]
        # print(f"[DEBUG] SystemMessage created successfully")
        messages.extend(
            AIMessage(content=entry['content']) if entry.get('is_question') in ('1', 1, True)
            else HumanMessage(content=entry['content'])
            for entry in conversation_log
        )
        # print(f"[DEBUG] All messages extended, total count: {len(messages)}")
    except Exception as message_error:
        print(f"[DEBUG] Error creating messages: {type(message_error).__name__}: {message_error}")
        import traceback
        print(f"[DEBUG] Message error traceback: {traceback.format_exc()}")
        raise
    
    t_after_messages = time.time()
    print(f"[TIMING] Building messages for engagement check ({len(messages)} msgs): {(t_after_messages - t_before_messages) * 1000:.2f}ms")
    # print(f"[DEBUG] Messages built successfully, engagement_llm is None: {engagement_llm is None}")
    
    # Invoke the LLM with structured output
    t_before_invoke = time.time()
    # print(f"[DEBUG] About to check if engagement_llm is None...")
    
    # If structured output model failed to initialize, skip to fallback
    if engagement_llm is None:
        print(f"[DEBUG] Structured output model not available, using fallback approach")
        raise Exception("Engagement LLM not initialized - using fallback")
    
    # print(f"[DEBUG] engagement_llm is not None, proceeding to invoke...")
    # print(f"[DEBUG] engagement_llm type: {type(engagement_llm)}")
    
    try:
        # print(f"[DEBUG] Entered try block for invoke...")
        # print(f"[DEBUG] About to invoke engagement LLM with {len(messages)} messages")
        # print(f"[DEBUG] First message type: {type(messages[0])}, content preview: {str(messages[0].content)[:200] if hasattr(messages[0], 'content') else 'N/A'}")
        # print(f"[DEBUG] Engagement LLM type: {type(engagement_llm)}")
        # print(f"[DEBUG] Engagement LLM has invoke: {hasattr(engagement_llm, 'invoke')}")
        
        response = engagement_llm.invoke(messages)
        # print(f"[DEBUG] Engagement LLM invoke completed successfully")
        # print(f"[DEBUG] Response type: {type(response)}")
        # print(f"[DEBUG] Response value: {response}")
        # print(f"[DEBUG] Response repr: {repr(response)}")
        t_after_invoke = time.time()
        print(f"[TIMING] Engagement LLM invoke: {(t_after_invoke - t_before_invoke) * 1000:.2f}ms")
        
        # Handle different response formats from structured output
        low_engagement = False
        # print(f"[DEBUG] Starting to extract low_engagement from response...")
        try:
            # Try accessing as Pydantic model attribute
            # print(f"[DEBUG] Checking if response has 'low_engagement' attribute...")
            if hasattr(response, 'low_engagement'):
                # print(f"[DEBUG] Response has low_engagement attribute, accessing...")
                low_engagement = bool(response.low_engagement)
                # print(f"[DEBUG] Successfully got low_engagement={low_engagement} via attribute access")
            # Try accessing as dict
            elif isinstance(response, dict):
                # print(f"[DEBUG] Response is dict, accessing key 'low_engagement'...")
                # print(f"[DEBUG] Dict keys: {list(response.keys())}")
                low_engagement = bool(response.get("low_engagement", False))
                # print(f"[DEBUG] Successfully got low_engagement={low_engagement} from dict")
            # Try accessing as string that needs parsing
            elif isinstance(response, str):
                # print(f"[DEBUG] Response is string, parsing as JSON...")
                import json
                parsed = json.loads(response)
                # print(f"[DEBUG] Parsed JSON: {parsed}")
                low_engagement = bool(parsed.get("low_engagement", False))
                # print(f"[DEBUG] Successfully got low_engagement={low_engagement} from parsed JSON")
            else:
                # Try to convert to dict if it's a Pydantic model
                # print(f"[DEBUG] Response is neither dict nor has attribute, trying Pydantic methods...")
                # print(f"[DEBUG] Response has 'dict' method: {hasattr(response, 'dict')}")
                # print(f"[DEBUG] Response has 'model_dump' method: {hasattr(response, 'model_dump')}")
                try:
                    if hasattr(response, 'dict'):
                        # print(f"[DEBUG] Using dict() method...")
                        response_dict = response.dict()
                        # print(f"[DEBUG] Dict result: {response_dict}")
                        low_engagement = bool(response_dict.get("low_engagement", False))
                        # print(f"[DEBUG] Successfully got low_engagement={low_engagement} via dict()")
                    elif hasattr(response, 'model_dump'):
                        # print(f"[DEBUG] Using model_dump() method...")
                        response_dict = response.model_dump()
                        # print(f"[DEBUG] Model dump result: {response_dict}")
                        low_engagement = bool(response_dict.get("low_engagement", False))
                        # print(f"[DEBUG] Successfully got low_engagement={low_engagement} via model_dump()")
                    else:
                        print(f"[DEBUG] Unexpected response type: {type(response)}, value: {response}")
                        # print(f"[DEBUG] Response dir (first 20): {[attr for attr in dir(response) if not attr.startswith('_')][:20]}")
                        low_engagement = False
                except Exception as parse_error:
                    print(f"[DEBUG] Failed to parse response: {type(parse_error).__name__}: {parse_error}")
                    import traceback
                    print(f"[DEBUG] Parse error traceback: {traceback.format_exc()}")
                    # print(f"[DEBUG] Response that failed: {response}")
                    low_engagement = False
        except Exception as access_error:
            print(f"[DEBUG] ERROR accessing low_engagement: {type(access_error).__name__}: {access_error}")
            print(f"[DEBUG] Response type: {type(response)}")
            # print(f"[DEBUG] Response value: {response}")
            # print(f"[DEBUG] Response repr: {repr(response)}")
            import traceback
            print(f"[DEBUG] Access error traceback: {traceback.format_exc()}")
            # Fall through to fallback
            raise access_error
        
        # === DEBUG START ===
        if debug_caching:
            print(f"[DEBUG] Engagement check result: low_engagement={low_engagement}")
        # === DEBUG END ===
        
        # Return the boolean value
        return low_engagement
    except Exception as e:
        # Fallback: if structured output fails, try parsing JSON from regular response
        print(f"[DEBUG] Structured output failed, trying fallback: {type(e).__name__}: {e}")
        import traceback
        # print(f"[DEBUG] Traceback: {traceback.format_exc()}")
        try:
            # Create a regular model without structured output
            model_kwargs = {**params["engagement_llm"]["kwargs"], "api_key": key}
            fallback_llm = init_chat_model(
                model=params["engagement_llm"]["model"],
                model_provider=params["engagement_llm"]["model_provider"],
                **model_kwargs
            )
            fallback_response = fallback_llm.invoke(messages)
            import json
            # Try to parse JSON from response
            response_text = fallback_response.content.strip()
            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            response_text = response_text.strip()
            parsed = json.loads(response_text)
            low_engagement = parsed.get("low_engagement", False)
            print(f"[DEBUG] Fallback engagement check result: low_engagement={low_engagement}")
            return low_engagement
        except Exception as fallback_error:
            print(f"[DEBUG] Fallback also failed: {fallback_error}")
            # Default to False (continue current topic) if all parsing fails
            return False
    
