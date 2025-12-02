from django.http import HttpResponse
from django.shortcuts import render

# Create your views here.
def index(request):
    return render(request, "home/index.html")

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