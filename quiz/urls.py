from django.urls import path
from . import views
from . import views_advanced

app_name = "quiz"  

urlpatterns = [
    # Web Interface
    path('quiz', views.home, name='home'),
    
    # Original API Endpoints
    path('api/new/', views.api_new_question, name='api_new'),     
    path('api/check/', views.api_check_answer, name='api_check'),
    path('api/reset/', views.api_reset_quiz, name='api_reset'),
    path('api/stats/', views.api_quiz_stats, name='api_stats'),
    
    # Daily Challenge
    path('api/daily-challenge/', views_advanced.api_daily_challenge, name='daily_challenge'),
    path('api/daily-challenge/complete/', views_advanced.api_complete_daily_challenge, name='complete_daily_challenge'),
    
    # Bookmarks
    path('api/bookmark/', views_advanced.api_bookmark_question, name='bookmark'),
    path('api/bookmark/remove/', views_advanced.api_remove_bookmark, name='remove_bookmark'),
    path('api/bookmarks/', views_advanced.api_get_bookmarks, name='get_bookmarks'),
    path('bookmarks/', views_advanced.bookmarks_page, name='bookmarks_page'),
    
    # Search
    path('api/search/', views_advanced.api_search_questions, name='search'),
    
    # User Profile
    path('profile/', views_advanced.user_profile, name='profile'),
    path('api/user/stats/', views_advanced.api_user_stats, name='user_stats'),
    
    # Export
    path('export/csv/', views_advanced.export_csv, name='export_csv'),
    path('export/pdf/', views_advanced.export_pdf, name='export_pdf'),
]