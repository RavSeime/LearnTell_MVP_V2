from django.urls import path

from . import views #Use . to retreive views from

urlpatterns = [
    path("", views.index, name="index"),
    path("<str:name>", views.greet, name ="greet"), #Custom routing!
    path("new_years/", views.is_new_years)
]
