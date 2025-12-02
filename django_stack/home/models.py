from django.db import models
import uuid
# Create your models here.


class User(models.Model):
    user_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    password = models.EmailField()

    def __str__(self):
        return self.username  # Display in admin and debugging
    
    def get_survey_count(self):
        return self.surveyparams_set.count()

class SurveyParams(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    survey_name = models.CharField(max_length=100)
    params = models.JSONField()
    
    class Meta:
        unique_together = ['user', 'survey_name']  # Composite unique constraint
        # Or in newer Django:
        constraints = [
            models.UniqueConstraint(fields=['user', 'survey_name'], name='unique_user_survey')
        ]
    def __str__(self):
        return f"{self.user.username} - {self.survey_name}"
    
    def get_response_count(self):
        return self.surveyresponse_set.count()
    
    def get_latest_response(self):
        return self.surveyresponse_set.order_by('-submitted_at').first()
    

class SurveyResponse(models.Model):
    survey = models.ForeignKey(SurveyParams, on_delete=models.CASCADE)
    respondent_id = models.CharField(max_length=100)
    responses = models.JSONField()
    submitted_at = models.DateTimeField(auto_now_add=True)
        
    def __str__(self):
        return f"Response from {self.respondent_id} - {self.survey.survey_name}"
    
    def get_survey_owner(self):
        return self.survey.user
    
    class Meta:
        unique_together = ['survey', 'respondent_id']
