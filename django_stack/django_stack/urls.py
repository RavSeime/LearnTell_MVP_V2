"""
URL configuration for django_stack project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from django.http import JsonResponse

def health_check(request):
    """Health check endpoint for Render"""
    return JsonResponse({"status": "healthy"})

urlpatterns = [
    path('', health_check),  # Root endpoint for health checks
    path('health/', health_check),  # Alternative health check endpoint
    path('admin/', admin.site.urls),
    path('home/', include("home.urls") ), #Linking to the url configuration of home
    path('to_do_list/', include("to_do_list.urls")),
    path('survey_taker/', include("survey_taker.urls")),  # Survey.js integration
]
