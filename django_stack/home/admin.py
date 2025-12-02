from django.contrib import admin


from .models import User, SurveyParams, SurveyResponse
# Register your models here.
admin.site.register(User)
admin.site.register(SurveyParams)
admin.site.register(SurveyResponse)

