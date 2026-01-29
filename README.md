# LearnTell

An AI-powered qualitative interview platform built with Django and LangGraph. LearnTell enables administrators to create, deploy, and manage interactive AI-driven interviews with dynamic question generation, real-time engagement validation, and answer moderation.

## Features

- **Multi-topic interview flows** with AI-generated follow-up questions
- **Real-time engagement analysis** to ensure quality responses
- **Answer moderation and validation** with retry logic
- **Progress tracking** during interviews
- **Response data export** to CSV
- **Multi-LLM provider support** (OpenAI, Anthropic, Google, Azure OpenAI, Mistral, Cohere, Groq, and more)

## Tech Stack

### Backend
- **Django 5.2** - Web framework
- **PostgreSQL** - Production database (SQLite for development)
- **Gunicorn + gevent** - ASGI server with async support

### AI/LLM
- **LangChain** - LLM orchestration
- **LangGraph** - State machine graphs for agentic conversation workflows
- **LangSmith** - Monitoring and tracing

### Frontend
- **Survey.js** - Dynamic form/survey UI
- **Custom chat interface** - Vanilla JavaScript and CSS

### Deployment
- **Docker** - Multi-stage containerized builds
- **WhiteNoise** - Static file serving

## Project Structure

```
LearnTell_claude/
├── django_stack/
│   ├── django_stack/           # Django settings & configuration
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   │
│   ├── home/                   # Authentication & survey management
│   │   ├── views.py            # Login, survey CRUD, response export
│   │   ├── models.py           # SurveyParams, SurveyResponse
│   │   └── templates/home/
│   │
│   ├── survey_taker/           # Interview execution engine
│   │   ├── views.py            # API endpoints for interview flow
│   │   ├── graphs/             # LangGraph conversation flows
│   │   │   └── gatekeeper_engagement_validation_v6.py
│   │   ├── self_eng_langgraph/ # LLM orchestration
│   │   │   └── multi_agent.py
│   │   └── templates/survey_taker/
│   │       └── survey.html     # Chat interface
│   │
│   └── manage.py
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── build.sh
```

## Installation

### Prerequisites
- Python 3.13+
- PostgreSQL (production) or SQLite (development)
- API keys for your chosen LLM provider

### Local Development

1. Clone the repository:
```bash
git clone <repository-url>
cd LearnTell_claude
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
# Create .env file in django_stack/
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
SECRET_KEY=your_django_secret_key
DEBUG=True
```

5. Run migrations:
```bash
cd django_stack
python manage.py migrate
```

6. Create a superuser:
```bash
python manage.py createsuperuser
```

7. Start the development server:
```bash
python manage.py runserver
```

### Docker Deployment

```bash
docker-compose up --build
```

## Usage

### Creating an Interview

1. Log in to the admin dashboard
2. Create a new survey with your interview plan
3. Configure the interview parameters:

```json
{
    "api_key": "openai_api_key",
    "graph_config": "gatekeeper_engagement",
    "prompter_llm": {
        "provider": "openai",
        "model": "gpt-4"
    },
    "interview_plan": [
        {
            "topic": "Background",
            "length": 3,
            "initial_question": "Tell me about yourself"
        }
    ]
}
```

4. Share the survey link with respondents

### Interview Flow

```
Survey View → Load Interview Plan → Chat UI
    ↓
User Input → LangGraph Processing
    ↓
Engagement Check → Moderation → Generate Question
    ↓
Progress Update → Repeat until complete
    ↓
Save Response → Export to CSV
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/survey/<uuid>/` | GET | Load interview interface |
| `/api/response/` | POST | Process user response |
| `/api/complete/` | POST | Save completed interview |
| `/home/` | GET | Dashboard |
| `/home/download/<uuid>/` | GET | Export responses as CSV |

## Configuration

### Supported LLM Providers

- OpenAI (GPT-3.5, GPT-4)
- Anthropic (Claude)
- Google AI
- Azure OpenAI
- Mistral
- Cohere
- Groq
- Together AI
- Fireworks AI

### Graph Configurations

- `base_graph` - Simple question-answer flow
- `gatekeeper_engagement` - Includes engagement validation
- `gatekeeper_engagement_validation_v6` - Full moderation with retry logic

## Development

### Running Tests

```bash
cd django_stack
python manage.py test
```

### Code Structure

- **home app**: User authentication, survey management, response export
- **survey_taker app**: Interview execution, LangGraph flows, API endpoints
- **graphs/**: LangGraph conversation state machines
- **self_eng_langgraph/**: LLM initialization and prompt handling

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]
