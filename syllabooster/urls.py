#!/usr/bin/env python

from django.urls import path

from . import views

app_name = "syllabooster"
urlpatterns = [
    path("", views.index, name="index"),
    path("unauthorised/", views.unauthorised, name="unauthorised"),
    path("courselist/", views.CourseListView.as_view(), name="courselist"),
    path("unitlist/<course>/", views.UnitListView.as_view(), name="unitlist"),
    path("unit/<course>/<unit>/", views.UnitView.as_view(), name="unit"),
    path("currentunit/<course>/", views.currentView, name="currentunit"),
    path(
        "coursepointdetail/<int:pk>/",
        views.CoursePointView.as_view(),
        name="coursepointdetail",
    ),
    path("cyclestate/", views.cycle_state, name="cyclestate"),
]
