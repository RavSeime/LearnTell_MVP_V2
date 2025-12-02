from django.urls import path

from . import views #Use . to retreive views from

from django.contrib import admin

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.index, name="index"),
    path("new_years/", views.is_new_years),
    path("sql_test/", views.sql_test),
    path("<str:name>", views.greet, name ="greet"), #Custom routing! Must be last
]
