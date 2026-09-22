from django.urls import path
from .views import DownloadIdolReportView

urlpatterns = [
    path('idols/<str:gpid>/', DownloadIdolReportView.as_view(), name='download-idol-report'),
]
