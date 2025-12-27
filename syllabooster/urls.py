#!/usr/bin/env python

from django.urls import path

from . import views

app_name = "syllabooster"
urlpatterns = [
    path("", views.index, name="index"),
    path("unauthorised/", views.unauthorised, name="unauthorised"),
    path("courselist/", views.CourseListView.as_view(), name="courselist"),
    path("course/<course>/", views.CourseView.as_view(), name="course"),
    path("unitlist/<course>/", views.UnitListView.as_view(), name="unitlist"),
    path("unit/<course>/<unit>/", views.UnitView.as_view(), name="unit"),
    path("currentunit/<course>/", views.CurrentUnitView.as_view(), name="currentunit"),
    path("cyclestate/", views.cycle_state, name="cyclestate"),
]
