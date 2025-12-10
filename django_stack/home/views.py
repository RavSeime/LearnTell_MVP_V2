from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, reverse, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.core.cache import cache
from .models import SurveyParams, SurveyResponse
import csv
import json

# Create your views here.
def index(request):
    # Check if user is logged in
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))
    
    # Get all surveys belonging to the current logged-in user
    user_surveys = SurveyParams.objects.filter(user=request.user)
    
    return render(request, "home/index.html", {
        "surveys": user_surveys
    })


def login_view(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "home/login.html", {
                "message" : "Invalid credentials"
                })
    return render(request, "home/login.html")

def logout_view(request):
    logout(request)
    return render(request, "home/login.html", {
        "message" : "Logged out"
        })

def edit_survey(request, survey_id):
    # Check if user is logged in
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))
    
    # Get the survey by ID, or return 404 if not found
    survey = get_object_or_404(SurveyParams, survey_id=survey_id)
    
    # Security: Make sure the survey belongs to the current user
    if survey.user != request.user:
        return HttpResponseRedirect(reverse("index"))
    
    # Handle form submission (POST request)
    if request.method == "POST":
        survey.survey_name = request.POST["survey_name"]
        # Parse the JSON string from the textarea
        params_string = request.POST["params"]
        try:
            survey.params = json.loads(params_string)
        except json.JSONDecodeError as e:
            # If parsing fails, return to form with error
            return render(request, "home/edit_survey.html", {
                "survey": survey,
                "params_pretty": params_string,
                "response_count": survey.get_response_count(),
                "error": f"Invalid JSON: {str(e)}"
            })
        survey.save()
        
        # Invalidate cache so survey_taker gets fresh params immediately
        cache.delete(f'survey_params_{survey_id}')
        
        return HttpResponseRedirect(reverse("index"))
    
    # Pretty-print the JSON for display
    # Handle case where params might be double-encoded as a string
    params_data = survey.params
    if isinstance(params_data, str):
        try:
            # First parse
            params_data = json.loads(params_data)
            # Check if it's still a string (triple-encoded)
            if isinstance(params_data, str):
                params_data = json.loads(params_data)
        except json.JSONDecodeError:
            pass  # If it fails, use as-is
    params_pretty = json.dumps(params_data, indent=4, ensure_ascii=False)
    
    # Get response count
    response_count = survey.get_response_count()
    
    # Display the edit form (GET request)
    return render(request, "home/edit_survey.html", {
        "survey": survey,
        "params_pretty": params_pretty,
        "response_count": response_count
    })



def greet(request, name):
    return render(request, "home/greet.html", {
        "name": name.capitalize()
    })

def is_new_years(request): #Basic new years condition
    import datetime as dt
    now = dt.datetime.now()
    result = now.day == 1 and now.month == 12
    return render(request, "home/new_years.html", {
        "newyear": result
    })

def download_responses(request, survey_id):
    # Check if user is logged in
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))
    
    # Get the survey by ID, or return 404 if not found
    survey = get_object_or_404(SurveyParams, survey_id=survey_id)
    
    # Security: Make sure the survey belongs to the current user
    if survey.user != request.user:
        return HttpResponseRedirect(reverse("index"))
    
    # Get all responses for this survey
    responses = SurveyResponse.objects.filter(survey=survey).order_by('submitted_at')
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{survey.survey_name}_responses.csv"'
    
    writer = csv.writer(response)
    
    # Write header
    writer.writerow(['Respondent ID', 'Submitted At', 'Message Order', 'Is Question', 'Topic', 'Content'])
    
    # Write data rows - one row per message
    for survey_response in responses:
        # Extract conversation from responses JSON
        conversation = survey_response.responses.get('conversation', [])
        
        # Handle both dict and list formats
        if not isinstance(conversation, list):
            conversation = []
        
        for msg in conversation:
            # Ensure msg is a dictionary
            if not isinstance(msg, dict):
                continue
            
            # Try both 'message' and 'content' keys for backwards compatibility
            message_text = msg.get('message', msg.get('content', ''))
            
            # Replace newlines with spaces to prevent multi-row issues
            message_text = str(message_text).replace('\n', ' ').replace('\r', ' ')
                
            writer.writerow([
                survey_response.respondent_id,
                survey_response.submitted_at.strftime('%Y-%m-%d %H:%M:%S'),
                msg.get('order', ''),
                'Yes' if msg.get('is_question') in [1, '1', True] else 'No',
                msg.get('topic', ''),
                message_text
            ])
    
    return response

from django.contrib.auth.models import User

def sql_test(request):
    return render(request, "home/sql_test.html", {
        "users":User.objects.all()
    })