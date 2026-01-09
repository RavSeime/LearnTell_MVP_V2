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
    
