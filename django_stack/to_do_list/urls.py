from django.urls import path

from . import views

app_name = "to_do_list" #Give an app name to avoid potential
#namespace collision

urlpatterns = [
    path("", views.index, name = "index"),
    path("add/", views.add, name = "add"),
]