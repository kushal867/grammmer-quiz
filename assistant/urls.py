from django.urls import path
from . import views
from .views import ImproveAPIView

urlpatterns = [
    path("", views.improve_page, name="improve_page"),
    path("api/improve/", ImproveAPIView.as_view(), name="improve_api"),
]
