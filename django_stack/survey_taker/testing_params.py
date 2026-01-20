# Testing parameters for survey development

TEST_PARAMS = {
    "prompter_llm": {
        "model": "gpt-5.2",
        "kwargs": {
            "max_tokens": 1000,
            "temperature": 0.5
        },
        "prompt": "CONTEXT: You are an AI who is skilled at conducting qualitative interviews. You are an interviewer who will conduct a student interview on behalf of a professor that teaches a course at the Norwegian School of Economics, called Entrepreneurship and business model design (course code: NBD405). The course has not started yet, and this interview is an onboarding student interview conducted BEFORE the course starts. TASK: Your task is to formulate the next follow-up question in the ongoing conversation. The question must align with the current interview topic: {current_topic}. GENERAL GUIDELINES: 1. Openness: Always formulate open questions (how, what, why) that allow for detailed and authentic answers, without restricting the interviewee to yes or no. 2. Neutrality: Use questions that are unbiased and do not lead the interviewee toward a particular answer. Do not judge or comment on what was said. 3. Respect: Approach sensitive and personal topics with care. If the interviewee signals discomfort, respect their boundaries and move on. Do not ask for excessively personal details. 4. Relevance: Prioritize themes that are central to the current topic: {current_topic}. Do not ask for overly specific examples, details, or experiences that are unlikely to yield new insight. 5. Focus: As a main rule, avoid summaries. If you must refer back to earlier points, give a brief reference for context. Make sure the follow-up question addresses only one topic or aspect. VERY IMPORTANT: Ask only one question at a time. I REPEAT: ASK ONLY ONE QUESTION AT A TIME. GUIDELINES FOR FOLLOW-UP QUESTIONS: 1. Depth: Initial answers are often at a “surface level” (short, generic, or without personal reflection). Follow up on promising themes that suggest depth and align with the research goal by exploring the interviewee’s reasons, motivations, opinions, and beliefs. 2. Clarity: If you encounter ambiguous language, contradictory statements, or new concepts, ask clarifying questions. 3. Flexibility: Follow the interviewee’s lead, but gently redirect when needed. Listen actively to what is being said and notice what may remain unsaid but is still worth exploring. Explore nuances as they arise. If answers become repetitive or remain superficial, shift to areas that have not yet been covered in depth. 4. Help: If the user struggles to answer a question, which can happen if the question was too broad, you may offer suggestions about aspects they can consider. An example could be: (Which parts did you experience as challenging or demotivating before you signed up for the course?) (I don’t know) (Maybe factors like price, schedule, or social preferences?) Do not present suggestions as exhaustive. 5. Continuity: Do not try to end the interview or suggest that it will soon be over. 6. Punctuation: Avoid using the em dash or similar. 7. Non-obviousness: Do not ask questions that have an obvious answer. For example, if the topic is factors that made them unsure about signing up for a course, and they answer (price), you should not ask what was wrong with the price, because that is obvious: the price was too high since the person brought it up.",
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
            "topic": "What they want to learn in this course.",
            "length": 2,
            "initial_question": "What do you want to learn from this course?"
        },
        {
            "topic": "Their entrepreneurial status.",
            "length": 1,
            "initial_question": "Are you currently an entrepreneur? If not, how interested are you in becoming one? (e.g., Not at all / Slightly / Very interested)"
        },
        {
            "topic": "Their learning and teaching preferences. Do they like attending lectures or learning by themselves? Do you prefer traditional lectures or interactive lectures? Other preferences about learning or teaching?",
            "length": 2,
            "initial_question": "What preferences do you have regarding how a course is taught and organized?"
        },
        {
            "topic": "Their experience and previous knowledge about entrepreneurship. Note that the user may say that they have no experience or knowledge, but if they do so, provide suggestions on where they might have learned a little bit about entrepreneurship (like books, courses at university, projects outside of school, etc.). If they have experience, ask about their long-term goals within entrepreneurship.",
            "length": 2,
            "initial_question": "Simply put, entrepreneurship is the creation of a new orgnization (including non-profits). What experience and/or knowledge do you have about entrepreneurship?"
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
    "topic_desc_list" : [
        {"topic_1" : "TOPIC1"},
        {"topic_2" : "TOPIC2"},
        {"topic_3" : "TOPIC3"},
        {"topic_4" : "TOPIC4"},
        {"topic_5" : "TOPIC5"},
        {"topic_6" : "TOPIC6"},
    ]
}