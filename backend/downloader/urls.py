from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('download/', views.download_video, name='download'),
    path('download/<str:download_id>/', views.stream_download, name='stream_download'),
    path('progress/<str:download_id>/', views.get_progress, name='progress'),
]
