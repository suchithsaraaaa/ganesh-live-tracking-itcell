from django.urls import path
from .views import (
    AssignmentListView,
    CreateAssignmentView,
    HandoverAssignmentView,
    CurrentAssignmentView,
    EndAssignmentView,
    AssignableIdolRegistryView,
    AssignableIdolDetailView,
    AssignmentExportExcelView,
)

urlpatterns = [
    path('', AssignmentListView.as_view(), name='assignment-list'),
    path('registry/', AssignableIdolRegistryView.as_view(), name='assignment-registry'),
    path('registry/<str:gpid>/', AssignableIdolDetailView.as_view(), name='assignment-registry-detail'),
    path('export/', AssignmentExportExcelView.as_view(), name='assignment-export-excel'),
    path('create/', CreateAssignmentView.as_view(), name='assignment-create'),
    path('current/', CurrentAssignmentView.as_view(), name='assignment-current'),
    path('<int:pk>/handover/', HandoverAssignmentView.as_view(), name='assignment-handover'),
    path('<int:pk>/end/', EndAssignmentView.as_view(), name='assignment-end'),
]
