
def test_create_agent(params, key):
    from langchain_openai import ChatOpenAI
    from langgraph.checkpoint.memory import InMemorySaver
    test_agent = ChatOpenAI(model = "gpt-5",
                            api_key = key,
                            checkpointer = InMemorySaver())
    return "bingus"

def get_response(params, conversation_log, key, debug_caching=True, moderate=False):
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
    import asyncio
    
    prompt_llm = ChatOpenAI(
        model="gpt-4o-mini",
        api_key=key,
        temperature=0.7,
        max_tokens=200
    )
    
    messages = [
        SystemMessage(content=params["prompter_llm"]["prompt"]),
    ]
    for entry in conversation_log:
        is_question = entry.get('is_question', '0')
        if is_question == '1' or is_question == 1 or is_question == True:
            messages.append(AIMessage(content=entry['content']))
        else:
            messages.append(HumanMessage(content=entry['content']))
    
    # Parallel processing: Generate response + moderate simultaneously
    if moderate and len(conversation_log) > 0:
        # Get last user message
        last_user_msg = next((e['content'] for e in reversed(conversation_log) 
                              if e.get('is_question') in ['0', 0, False]), None)
        
        if last_user_msg:
            # Create moderator
            moderator_llm = ChatOpenAI(
                model="gpt-4o-mini",
                api_key=key,
                temperature=0.3,
                max_tokens=50
            )
            
            moderator_prompt = [
                SystemMessage(content="You are a content moderator. Reply ONLY 'OK' if appropriate, or 'FLAG' if inappropriate/off-topic."),
                HumanMessage(content=f"Moderate this response: {last_user_msg}")
            ]
            
            # Run both LLM calls in parallel using batch
            responses = prompt_llm.batch([messages, moderator_prompt])
            response = responses[0]
            moderation = responses[1].content.strip().upper()
            
            # If flagged, return warning message instead
            if "FLAG" in moderation:
                class FlaggedResponse:
                    content = "I noticed your response might be off-topic. Could you please answer the question?"
                    usage_metadata = {}
                return FlaggedResponse()
        else:
            response = prompt_llm.invoke(messages)
    else:
        # No moderation - single call
        response = prompt_llm.invoke(messages)
    
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
    
