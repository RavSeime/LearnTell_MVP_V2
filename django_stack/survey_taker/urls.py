from django.urls import path
from . import views

app_name = 'survey_taker'

urlpatterns = [
    # Tester ¨
    path("tester/<uuid:survey_id>/", views.tester, name = "tester"),

    # Survey frontend - displays the Survey.js interface
    path('survey/<uuid:survey_id>/', views.survey_view, name='survey'),
    
    # POST endpoint for processing responses
    path('api/response/<uuid:survey_id>/', views.process_response, name='process_response'),
    
    # POST endpoint for saving completed conversation
    path('api/complete/<uuid:survey_id>/', views.complete_survey, name='complete_survey'),
]
