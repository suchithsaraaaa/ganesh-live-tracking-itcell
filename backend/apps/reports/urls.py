from django.urls import path
from .views import DownloadIdolReportView, CompletedReportsRegistryView

urlpatterns = [
    path('registry/', CompletedReportsRegistryView.as_view(), name='reports-registry'),
    path('idols/<str:gpid>/', DownloadIdolReportView.as_view(), name='download-idol-report'),
]
