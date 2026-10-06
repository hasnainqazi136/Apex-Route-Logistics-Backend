from django.contrib import admin
from django.urls import path, include
from api.views import api_root

urlpatterns = [
    path('', api_root, name='root'),
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('api', api_root, name='api_root_no_slash'),
]
