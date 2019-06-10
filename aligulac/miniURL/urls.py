from django.urls import path

from .views import new, find_redirect

urlpatterns = [
    path('new', new, name='url_new'),
    path('<slug:code>', find_redirect, name='url_redirect'),
]
