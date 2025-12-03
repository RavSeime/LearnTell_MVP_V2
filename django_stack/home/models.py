from django.db import models
from django.contrib.auth.models import User
import uuid
# Create your models here.


class SurveyParams(models.Model):
    survey_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    survey_name = models.CharField(max_length=100)
    params = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.survey_name}"
    
    def get_response_count(self):
        return self.surveyresponse_set.count()
    
    def get_latest_response(self):
        return self.surveyresponse_set.order_by('-submitted_at').first()
    
    class Meta:
        unique_together = ['user', 'survey_name']
        verbose_name_plural = "Survey Parameters"
    

class SurveyResponse(models.Model):
    survey = models.ForeignKey(SurveyParams, on_delete=models.CASCADE)  # Fixed: renamed from survey_id to survey
    respondent_id = models.CharField(max_length=100)
    responses = models.JSONField()
    submitted_at = models.DateTimeField(auto_now_add=True)
        
    def __str__(self):
        return f"Response from {self.respondent_id} - {self.survey.survey_name}"
    
    def get_survey_owner(self):
        return self.survey.user
    
    class Meta:
        unique_together = ['survey', 'respondent_id']  # Fixed: use 'survey' not 'survey_id'
        ordering = ['-submitted_at']
