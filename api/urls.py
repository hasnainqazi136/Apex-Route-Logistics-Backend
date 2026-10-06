from django.urls import path
from .views import health_check, geocode_search, plan_trip

urlpatterns = [
    path('health/', health_check, name='health_check'),
    path('geocode/', geocode_search, name='geocode_search'),
    path('plan-trip/', plan_trip, name='plan_trip'),
]
