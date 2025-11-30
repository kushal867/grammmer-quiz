
from django.urls import path
from . import views

app_name = "quiz"  

urlpatterns = [
    # Web Interface
    path('quiz', views.home, name='home'),                    # http://127.0.0.1:8000/quiz/

    # API Endpoints
    path('api/new/', views.api_new_question, name='api_new'),     
    path('api/check/', views.api_check_answer, name='api_check'),

]