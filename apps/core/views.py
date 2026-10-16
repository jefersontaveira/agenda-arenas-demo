from django.shortcuts import render
from .demo_views import demo_autologin_view, demo_reset_database_view, demo_status_view

def home(request):
    return render(request, 'core/index.html')

