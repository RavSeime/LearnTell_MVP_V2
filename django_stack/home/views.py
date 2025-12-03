from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, reverse, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from .models import SurveyParams

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
    import json
    
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
        survey.params = request.POST["params"]
        survey.save()
        return HttpResponseRedirect(reverse("index"))
    
    # Pretty-print the JSON for display
    params_pretty = json.dumps(survey.params, indent=4)
    
    # Display the edit form (GET request)
    return render(request, "home/edit_survey.html", {
        "survey": survey,
        "params_pretty": params_pretty
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

from django.contrib.auth.models import User

def sql_test(request):
    return render(request, "home/sql_test.html", {
        "users":User.objects.all()
    })