from django.urls import path

from . import views

app_name = "profiles"

urlpatterns = [
    path("", views.ProfileView.as_view(), name="profile"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("curator/", views.CuratorView.as_view(), name="curator"),
]
