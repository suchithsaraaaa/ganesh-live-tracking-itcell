from django.urls import path
from .views import PoliceStationListView

urlpatterns = [
    path('police-stations/', PoliceStationListView.as_view(), name='geography-police-stations'),
]
