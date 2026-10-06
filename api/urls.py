from django.urls import path
from .views import health_check, geocode_search, plan_trip, api_root

urlpatterns = [
    path('', api_root, name='api_root'),
    path('health/', health_check, name='health_check'),
    path('health', health_check, name='health_check_no_slash'),
    path('geocode/', geocode_search, name='geocode_search'),
    path('geocode', geocode_search, name='geocode_search_no_slash'),
    path('plan-trip/', plan_trip, name='plan_trip'),
    path('plan-trip', plan_trip, name='plan_trip_no_slash'),
]
