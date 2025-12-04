
def test_create_agent(params, key):
    from langchain_openai import ChatOpenAI
    from langgraph.checkpoint.memory import InMemorySaver
    test_agent = ChatOpenAI(model = "gpt-5",
                            api_key = key,
                            checkpointer = InMemorySaver())
    return "bingus"

def get_response(params, conversation_log, key):
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
    prompt_llm = ChatOpenAI(model = "gpt-4o", 
                            api_key = key)
    messages = [
        SystemMessage(content = params["prompter_llm"]["prompt"]),
    ]
    for entry in conversation_log:
        # Check if is_question exists and handle both string and int values
        is_question = entry.get('is_question', '0')
        if is_question == '1' or is_question == 1 or is_question == True:
            # AI's question
            messages.append(AIMessage(content=entry['content']))
        else:
            # User's answer
            messages.append(HumanMessage(content=entry['content']))
    
    # Actually invoke the LLM (you forgot to call the method!)
    response = prompt_llm.invoke(messages)
    
    # === DEBUG START ===
    usage = response.response_metadata.get('usage', {})
    prompt_tokens = usage.get('prompt_tokens', 0)
    cached_tokens = usage.get('prompt_tokens_details', {}).get('cached_tokens', 0)
    completion_tokens = usage.get('completion_tokens', 0)
    print(f"[DEBUG CACHING] Tokens - Prompt: {prompt_tokens}, Cached: {cached_tokens}, Completion: {completion_tokens}")
    if cached_tokens > 0:
        cache_percentage = (cached_tokens / prompt_tokens * 100) if prompt_tokens > 0 else 0
        print(f"[DEBUG CACHING] Cache hit! {cache_percentage:.1f}% of prompt tokens from cache")
    # === DEBUG END ===
    
    # Return the content string
    return response.content 
    
