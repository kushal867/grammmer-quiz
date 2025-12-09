from django.urls import path
from . import views
from . import views_advanced
from . import views_enhanced

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
    
    # New Enhanced Features
    # Question Ratings
    path('api/rate-question/', views_enhanced.api_rate_question, name='rate_question'),
    path('api/question-ratings/<int:question_id>/', views_enhanced.api_get_question_ratings, name='get_question_ratings'),
    
    # Timed Quiz
    path('api/timed-quiz/start/', views_enhanced.api_start_timed_quiz, name='start_timed_quiz'),
    path('api/timed-quiz/submit/', views_enhanced.api_submit_timed_quiz, name='submit_timed_quiz'),
    path('api/timed-quiz/status/', views_enhanced.api_timed_quiz_status, name='timed_quiz_status'),
    path('timed-quiz/', views_enhanced.timed_quiz_page, name='timed_quiz_page'),
    
    # Performance Analytics
    path('api/analytics/performance/', views_enhanced.api_performance_analytics, name='performance_analytics'),
    path('api/analytics/trends/', views_enhanced.api_performance_trends, name='performance_trends'),
    path('api/analytics/domain-breakdown/', views_enhanced.api_domain_breakdown, name='domain_breakdown'),
    
    # Leaderboard
    path('api/leaderboard/', views_enhanced.api_leaderboard, name='leaderboard'),
    path('api/leaderboard/<str:period>/', views_enhanced.api_leaderboard_by_period, name='leaderboard_by_period'),
    path('leaderboard/', views_enhanced.leaderboard_page, name='leaderboard_page'),
    
    # User Preferences
    path('api/preferences/', views_enhanced.api_get_preferences, name='get_preferences'),
    path('api/preferences/update/', views_enhanced.api_update_preferences, name='update_preferences'),
    
    # Dashboard
    path('dashboard/', views_enhanced.dashboard_page, name='dashboard'),
]