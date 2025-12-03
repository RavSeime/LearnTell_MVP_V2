from django.contrib import admin

from .models import SurveyParams, SurveyResponse
# Register your models here.
# Note: User is already registered by Django, no need to register it here
admin.site.register(SurveyParams)
admin.site.register(SurveyResponse)

