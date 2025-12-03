from django.urls import path

from . import views #Use . to retreive views from

urlpatterns = [
    path("", views.index, name="index"),
    path("login/", views.login_view, name ="login"),
    path("logout/", views.logout_view, name ="logout"),
    path("edit/<uuid:survey_id>/", views.edit_survey, name="edit_survey"),
    path("new_years/", views.is_new_years),
    path("sql_test/", views.sql_test),
    path("<str:name>", views.greet, name ="greet"), #Custom routing! Must be last
]
