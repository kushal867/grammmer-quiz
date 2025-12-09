from django.urls import path
from . import views
from .views import ImproveAPIView
from . import views_enhanced

urlpatterns = [
    path("improve", views.improve_page, name="kushal_writer"),
    path("api/improve/", ImproveAPIView.as_view(), name="improve_api"),
    
    # Draft Management
    path("api/drafts/save/", views_enhanced.api_save_draft, name="save_draft"),
    path("api/drafts/", views_enhanced.api_get_drafts, name="get_drafts"),
    path("api/drafts/<int:draft_id>/", views_enhanced.api_get_draft, name="get_draft"),
    path("api/drafts/<int:draft_id>/delete/", views_enhanced.api_delete_draft, name="delete_draft"),
    path("drafts/", views_enhanced.drafts_page, name="drafts_page"),
    
    # Templates
    path("api/templates/", views_enhanced.api_get_templates, name="get_templates"),
    path("api/templates/use/", views_enhanced.api_use_template, name="use_template"),
    path("templates/", views_enhanced.templates_page, name="templates_page"),
    
    # Text Comparison
    path("api/compare/", views_enhanced.api_compare_text, name="compare_text"),
    
    # Transformation History
    path("api/history/save/", views_enhanced.api_save_transformation, name="save_transformation"),
    path("api/history/", views_enhanced.api_get_transformation_history, name="get_transformation_history"),
    
    # Writing Statistics
    path("api/stats/", views_enhanced.api_get_writing_stats, name="get_writing_stats"),
    path("stats/", views_enhanced.writing_stats_page, name="writing_stats_page"),
]
