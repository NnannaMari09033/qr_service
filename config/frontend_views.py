"""
Simple views that serve HTML templates.

These are NOT API views — they don't return JSON.
They just render an HTML page and let the JavaScript on that page
talk to the REST API.
"""
from django.shortcuts import render


def landing_view(request):
    return render(request, 'landing.html')


def login_view(request):
    return render(request, 'login.html')


def register_view(request):
    return render(request, 'register.html')


def dashboard_view(request):
    return render(request, 'dashboard.html')


def settings_view(request):
    return render(request, 'settings.html')
