from django.urls import path
from .views import (
    AssignmentListView,
    CreateAssignmentView,
    HandoverAssignmentView,
    CurrentAssignmentView,
    EndAssignmentView
)

urlpatterns = [
    path('', AssignmentListView.as_view(), name='assignment-list'),
    path('create/', CreateAssignmentView.as_view(), name='assignment-create'),
    path('current/', CurrentAssignmentView.as_view(), name='assignment-current'),
    path('<int:pk>/handover/', HandoverAssignmentView.as_view(), name='assignment-handover'),
    path('<int:pk>/end/', EndAssignmentView.as_view(), name='assignment-end'),
]
