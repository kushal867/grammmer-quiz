from django.urls import path
from . import views
from .views import ImproveAPIView

urlpatterns = [
    path("improve", views.improve_page, name="kushal_writer"),
    path("api/improve/", ImproveAPIView.as_view(), name="improve_api"),
    
]
