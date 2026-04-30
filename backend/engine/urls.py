from django.contrib import admin
from django.urls import path
from django.http import JsonResponse

from .api import api

def home(request):
    return JsonResponse({"message": "WELCOME TO CHEESEBALL API BASE"})

urlpatterns = [
    path('', home),
    path('admin/', admin.site.urls),
    path("api/", api.urls),
]
