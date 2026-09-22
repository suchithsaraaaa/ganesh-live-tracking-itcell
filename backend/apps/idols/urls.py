from django.urls import path
from .views import IdolListView, IdolDetailView, DashboardStatsView
from apps.reports.views import DownloadIdolReportView

urlpatterns = [
    path('dashboard/', DashboardStatsView.as_view(), name='dashboard-stats'),
    path('', IdolListView.as_view(), name='idol-list'),
    path('<str:lookup>/', IdolDetailView.as_view(), name='idol-detail'),
    path('<str:gpid>/report/', DownloadIdolReportView.as_view(), name='idol-report'),
]
