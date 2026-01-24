# Testing parameters for survey development

TEST_PARAMS = {
  "api_key": "openai_api_key",
  "graph_config": "gatekeeper_engagement",
  "prompter_llm": {
    "model": "gpt-5.2",
    "kwargs": {
      "max_tokens": 1000,
      "temperature": 0.5
    },
    "prompt": "CONTEXT: You are an AI who is skilled at conducting qualitative interviews. You are an interviewer who will conduct a student interview on behalf of a professor that teaches a course at the Norwegian School of Economics, called Entrepreneurship and business model design (course code: NBD405). The course has not started yet, and this interview is an onboarding student interview conducted BEFORE the course starts. TASK: Your task is to formulate the next follow-up question in the ongoing conversation. The question must align with the current interview topic: {current_topic}. GENERAL GUIDELINES: 1. Openness: Always formulate open questions (how, what, why) that allow for detailed and authentic answers, without restricting the interviewee to yes or no. 2. Neutrality: Use questions that are unbiased and do not lead the interviewee toward a particular answer. Do not judge or comment on what was said. 3. Respect: Approach sensitive and personal topics with care. If the interviewee signals discomfort, respect their boundaries and move on. Do not ask for excessively personal details. 4. Relevance: Prioritize themes that are central to the current topic: {current_topic}. Do not ask for overly specific examples, details, or experiences that are unlikely to yield new insight. 5. Focus: As a main rule, avoid summaries. If you must refer back to earlier points, give a brief reference for context. Make sure the follow-up question addresses only one topic or aspect. VERY IMPORTANT: Ask only one question at a time. I REPEAT: ASK ONLY ONE QUESTION AT A TIME. GUIDELINES FOR FOLLOW-UP QUESTIONS: 1. Depth: Initial answers are often at a surface level. Follow up on promising themes by exploring reasons, motivations, opinions, and beliefs. 2. Clarity: Ask clarifying questions when encountering ambiguity or contradictions. 3. Flexibility: Follow the interviewee’s lead, but gently redirect when needed. 4. Help: If the user struggles, you may offer non-exhaustive suggestions. 5. Continuity: Do not try to end the interview. 6. Punctuation: Avoid em dashes. 7. Non-obviousness: Do not ask questions with obvious answers. 8. Validation: Provide a brief validation statement before the next question.",
    "model_provider": "openai"
  },
  "engagement_llm": {
    "model": "gpt-5.2",
    "kwargs": {
      "max_tokens": 500,
      "temperature": 0.5
    },
    "prompt": "You are analyzing a participant's response in an interview to determine their engagement level. Return True if engaged, False if disengaged.",
    "model_provider": "openai"
  },
  "first_question": "Hi! Before we begin: are you a student at Grunderskolen?  ",
  "gatekeeper_llm": {
    "model": "gpt-5.2",
    "kwargs": {
      "max_tokens": 500,
      "temperature": 0.5
    },
    "prompt": "You are analyzing a participant's response in an interview. Determine whether they have more to add. Respond with only True or False.",
    "model_provider": "openai"
  },
  "interview_plan": [
    {
      "topic": "If they're a student at Grunderskolen or not. We're looking for a simple Yes or No.",
      "length": 0,
      "initial_question": "Hi! Before we begin: are you a student at Grunderskolen?  "
    },
    {
      "topic": "What they want to learn in this course (NBD405).",
      "length": 5,
      "initial_question": "What do you want to learn from this course?"
    },
    {
      "topic": "Their entrepreneurial goals.",
      "length": 4,
      "initial_question": "Are you currently an entrepreneur? If not, how interested are you in becoming one?"
    },
    {
      "topic": "Their learning and teaching preferences.",
      "length": 4,
      "initial_question": "What preferences do you have regarding how a course is taught and organized?"
    },
    {
      "topic": "Their experience and previous knowledge about entrepreneurship.",
      "length": 4,
      "initial_question": "What experience and/or knowledge do you have about entrepreneurship?"
    },
    {
      "topic": "Their experience and previous knowledge about business models.",
      "length": 4,
      "initial_question": "What experience and/or knowledge do you have about business models?"
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
  "gatekeeping_time": 3,
  "closing_questions": [],
  "gatekeeper_question": "Before we move on, do you have anything else you'd like to add to {short_topic}, that might help the professor understand you better?",
  "topics_banned_from_gatekeeping": [0, 9],
  "pre_gen_transitions": true,
  "gatekeeper_topic_list": [
    { "topic_1": "TOPIC 1" },
    { "topic_2": "what you want to learn in NBD405" },
    { "topic_3": "your entrepreneurial goals" },
    { "topic_4": "your preferences regarding how NBD405 is taught" },
    { "topic_5": "your experience/knowledge regarding entrepreneurship" },
    { "topic_6": "your experience/knowledge regarding business models" }
  ],
  "end_of_interview_message": "That's all, thank you!!  ---END---"
}
