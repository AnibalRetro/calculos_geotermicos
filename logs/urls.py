from django.urls import path

from .views import analysis_view, upload_view

urlpatterns = [
    path('', upload_view, name='upload'),
    path('analysis/<int:file_id>/', analysis_view, name='analysis'),
]
