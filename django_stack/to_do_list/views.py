from django import forms
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.shortcuts import render

class NewTaskForm(forms.Form):
    task = forms.CharField(label = "New Task")

# Create your views here.
def index(request):
    if "tasks" not in request.session:
        request.session["tasks"] = []
    return render(request, "to_do_list/index.html", {
        "tasks": request.session["tasks"]
    })

def add(request):
    if request.method == "POST": #Could use this logic for AI chat, but run into a problem of lacking caching
        form = NewTaskForm(request.POST) #We are passing the request back into a server side form here
        if form.is_valid():
            task = form.cleaned_data["task"]
            request.session["tasks"] += [task]
            return HttpResponseRedirect(reverse("to_do_list:index"))
        else: 
            return render(request, "to_do_list/add.html", {
                "form": form
            })
    return render(request, "to_do_list/add.html", {
        "form" : NewTaskForm()
    })
