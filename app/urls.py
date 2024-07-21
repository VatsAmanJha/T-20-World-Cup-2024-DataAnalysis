from django.urls import path
from . import views

urlpatterns = [
    path("", views.match_details, name="match_details"),
    path("match/<int:match_id>/", views.match_details_view, name="match_details_view"),
]
