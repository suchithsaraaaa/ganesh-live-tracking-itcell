from django.urls import path
from .views import (
    LoginView,
    LogoutView,
    CurrentUserView,
    UserListCreateView,
    UserDetailView,
    UserToggleActiveView,
    UserDeleteView,
    AssignableOfficerDirectoryView,
    RoleTemplateListView,
    RoleTemplateDetailView,
)

urlpatterns = [
    path('login/', LoginView.as_view(), name='auth-login'),
    path('logout/', LogoutView.as_view(), name='auth-logout'),
    path('me/', CurrentUserView.as_view(), name='auth-me'),
    path('users/', UserListCreateView.as_view(), name='auth-users-list'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='auth-users-detail'),
    path('users/<int:pk>/toggle-active/', UserToggleActiveView.as_view(), name='auth-users-toggle-active'),
    path('users/<int:pk>/delete/', UserDeleteView.as_view(), name='auth-users-delete'),
    path('officers/', AssignableOfficerDirectoryView.as_view(), name='auth-officers-directory'),
    path('role-templates/', RoleTemplateListView.as_view(), name='auth-role-templates-list'),
    path('role-templates/<str:role>/', RoleTemplateDetailView.as_view(), name='auth-role-templates-detail'),
]

