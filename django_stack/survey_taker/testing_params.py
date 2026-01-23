# Testing parameters for survey development

TEST_PARAMS = {
    "graph_config": "base_graph",
    "prompter_llm": {
        "model": "gpt-5.2",
        "kwargs": {
            "max_tokens": 1000,
            "temperature": 0.5
        },
        "prompt": "CONTEXT: Ask a cool question about {current_topic}",
        "model_provider": "openai"
    },
    "first_question": "Hi! Before we begin: are you a student at Grunderskolen?  ",
    "interview_plan": [
        {
            "topic": "If they're a student at Grunderskolen or not. We're looking for a simple Yes or No.",
            "length": 1,
            "initial_question": "Denne blir overridet av first_question"
        },
        {
            "topic": "Their experience and previous knowledge about business models. Note that the user may say that they have no experience or knowledge, but if they do so, provide suggestions on where they might have learned a little bit about entrepreneurship (like books, courses at university, projects outside of school, etc.).",
            "length": 2,
            "initial_question": "Simply put, business models is how an organization creates something people want and how they get others to pay for it. What experience and/or knowledge do you have about business models?"
        }
    ],
    "transition_llm": {
        "model": "gpt-5.2",
        "kwargs": {
            "max_tokens": 500,
            "temperature": 0.5
        },
        "prompt": "You are a skilled AI interviewer who observes an interview. Your job is to come up with a transition phrase that signals the shift from the current topic ({previous_topic}) to the next topic ({next_topic}). Examples of transition phrases: A) Okay, let’s now talk a bit about your motivation for signing up for the course. B) Interesting! Let’s move on to what you want to achieve in the short and long term. C) Great, now we’ll talk a bit about your experiences with entrepreneurship. Notes: Assume that the next question will be handled by someone else. Keep it very general: So instead of (Thanks, let’s now talk about how you prefer to learn and whether you like lectures or self-directed learning.) instead say (Thanks, let's now talk about your learning preferences.) Use statements only, no questions. Only one sentence. Keep the sentence short; maximum 20 words. Make sure the same transition is never used more than once during the conversation, so review earlier transition phrases. Also, please do not use em dashes.",
        "model_provider": "openai"
    },
    "closing_questions": [],
    "pre_gen_transitions": True,
    "end_of_interview_message": "That's all, thank you!!  ---END---",
    "gatekeeper_llm": {
        "model": "gpt-5.2",
        "kwargs": {
            "max_tokens": 500,
            "temperature": 0.5
        },
        "prompt": "You are analyzing a participant's response in an interview. Your task is to determine if the participant indicates they have more information to add. Return True if the participant's statement suggests they have more to say (e.g., phrases like 'I could also mention...', 'There's more...', 'Also...', 'One more thing...', 'Additionally...', 'I should add...', or similar indicators). Return False if the participant indicates they are done or have nothing more to add (e.g., 'That's all', 'Nothing else', 'I think that's it', 'That's everything', 'No, that's it', or similar completion signals). Analyze the response carefully and respond with only True or False.",
        "model_provider": "openai"
    },
    "gatekeeping_time" : 2,
    "gatekeeper_question" : "Do you have anything more you'd like to add to {short_topic}",
    "gatekeeper_topic_list" : [
        {"topic_1" : "TOPIC1"},
        {"topic_2" : "TOPIC2"},
        {"topic_3" : "TOPIC3"},
        {"topic_4" : "TOPIC4"},
        {"topic_5" : "TOPIC5"},
        {"topic_6" : "TOPIC6"},
    ],
    "engagement_llm": {
        "model": "gpt-5.2",
        "kwargs": {
            "max_tokens": 500,
            "temperature": 0.5
        },
        "prompt": "You are analyzing a participant's response in an interview to determine their engagement level. Your task is to assess whether the participant is still actively engaged with the current topic. Return True if the participant shows engagement (e.g., provides detailed answers, asks relevant questions, shows enthusiasm, makes connections to the topic, elaborates on points, or demonstrates active thinking). Return False if the participant shows disengagement (e.g., gives very short/minimal answers, responses like 'I don't know', 'Not sure', 'Maybe', shows reluctance, repeatedly deflects, gives off-topic responses, or signals they want to move on). Analyze the response carefully and respond with only True or False.",
        "model_provider": "openai"
    }
}