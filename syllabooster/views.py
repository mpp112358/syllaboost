import json

from django.contrib.auth import user_logged_in
from django.core.exceptions import ImproperlyConfigured
from django.contrib.auth.views import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.views.generic import ListView
from django.views.decorators.http import require_POST
from django.db.models import Max, Min, OuterRef, Subquery
from django.conf import settings

from .models import (
    Tag,
    PointType,
    DeliveryState,
    Point,
    Syllabus,
    SyllabusPoint,
    Course,
    CoursePoint,
    Unit,
)


def get_course_current_unit(course):
    """Returns the unit of the current point."""
    print(f"Course current position: {course.current_position}")
    position = course.current_position if course.current_position > 0 else 1
    print(f"Position to look for: {position}")
    current_point = CoursePoint.objects.get(course=course, position=position)
    return current_point.unit


def update_course_current_position(course):
    """Update the current position for the course to the position
    following the maximum position of a done point (one whose
    state is the last one for its point type)."""

    # Subquery to get the maximum state position for each point type
    max_state_pos = (
        DeliveryState.objects.filter(point_type=OuterRef("point__point_type"))
        .order_by()
        .values("point_type")
        .annotate(max_pos=Max("position"))
        .values("max_pos")[:1]
    )

    # Find max position of done course points
    max_done_position = CoursePoint.objects.filter(
        course=course, state__position=Subquery(max_state_pos)
    ).aggregate(Max("position"))["position__max"]

    if max_done_position:
        course.current_position = max_done_position + 1
    else:
        course.current_position = 0

    course.save(update_fields=["current_position"])
    return course.current_position


class CustomUserPassesTestMixin(UserPassesTestMixin):
    unathorized_template = "unauthorised.html"

    def handle_no_permission(self):
        return render(self.request, self.unathorized_template, status=403)


@login_required
@require_POST
def cycle_state(request):
    """Cycle through posible states of the point."""
    try:
        data = json.loads(request.body)
        coursepoint_id = data["coursepointId"]

        coursepoint = CoursePoint.objects.get(id=coursepoint_id)
        course = coursepoint.course
        if course.user != request.user:
            raise Exception("Unauthorized access")
        point_type = coursepoint.point.point_type
        state = coursepoint.state
        next_state = state
        current_position = coursepoint.course.current_position
        if state:
            num_states = (
                DeliveryState.objects.filter(point_type_id=point_type.id).aggregate(
                    Max("position", default=0)
                )["position__max"]
                + 1
            )
            next_state_position = (state.position + 1) % num_states
            next_state = DeliveryState.objects.get(
                point_type_id=point_type.id, position=next_state_position
            )
            coursepoint.state = next_state
            coursepoint.save()
            current_position = update_course_current_position(coursepoint.course)

        return JsonResponse(
            {
                "status": "ok",
                "coursepointId": coursepoint_id,
                "stateId": next_state.id,
                "statePosition": next_state.position,
                "cssClassesStr": next_state.css_class if next_state else "",
                "currentPosition": current_position,
            }
        )

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


@login_required
def index(request):
    return HttpResponseRedirect("/courselist/")


class CourseListView(LoginRequiredMixin, ListView):
    model = Course
    template_name = "syllabooster/course_list.html"

    def get_queryset(self):
        loggedin_user = self.request.user
        return Course.objects.filter(user=loggedin_user)


class UnitListView(LoginRequiredMixin, CustomUserPassesTestMixin, ListView):
    model = Unit
    template_name = "syllabooster/unit_list.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.course = get_object_or_404(Course, id=self.kwargs["course"])

    def test_func(self):
        return self.course.user == self.request.user

    def get_queryset(self):
        return Unit.objects.filter(course=self.course)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["course"] = self.course
        context["currentunit"] = get_course_current_unit(self.course)
        return context


class CourseView(LoginRequiredMixin, CustomUserPassesTestMixin, ListView):
    model = CoursePoint
    template_name = "syllabooster/coursepoint_list.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.course = get_object_or_404(Course, id=self.kwargs["course"])

    def test_func(self):
        return self.course.user == self.request.user

    def get_queryset(self):
        return CoursePoint.objects.filter(course=self.course)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["course"] = self.course
        return context


class UnitView(LoginRequiredMixin, CustomUserPassesTestMixin, ListView):
    model = CoursePoint
    template_name = "syllabooster/unitcoursepoint_list.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.course = get_object_or_404(Course, id=self.kwargs["course"])
        self.unit = get_object_or_404(Unit, id=self.kwargs["unit"])

    def test_func(self):
        return self.course.user == self.request.user

    def get_queryset(self):
        return CoursePoint.objects.filter(course=self.course, unit=self.unit)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["course"] = self.course
        context["unit"] = self.unit
        return context


class CurrentUnitView(ListView):
    model = CoursePoint
    template_name = "syllabooster/unitcoursepoint_list.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.course = get_object_or_404(Course, id=self.kwargs["course"])
        self.unit = get_course_current_unit(self.course)

    def test_func(self):
        return self.course.user == self.request.user

    def get_queryset(self):
        return CoursePoint.objects.filter(course=self.course, unit=self.unit)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["course"] = self.course
        context["unit"] = self.unit
        return context


class GoogleRawLoginCredentials:
    def __init__(self, client_id="", client_secret="", project_id=""):
        self.client_id = client_id
        self.client_secret = client_secret
        self.project_id = project_id


def google_login_get_credentials():
    client_id = settings.GOOGLE_OAUTH_CLIENT_ID
    client_secret = settings.GOOGLE_OAUTH_CLIENT_SECRET
    project_id = settings.GOOGLE_OAUTH_PROJECT_ID

    if not client_id:
        raise ImproperlyConfigured("GOOGLE_OAUTH_CLIENT_ID is missing in env.")

    if not client_secret:
        raise ImproperlyConfigured("GOOGLE_OAUTH_CLIENT_SECRET is missing in env.")

    if not project_id:
        raise ImproperlyConfigured("GOOGLE_PROJECT_CLIENT_ID is missing in env.")

    credentials = GoogleRawLoginCredentials(client_id, client_secret, project_id)
    return credentials


def unauthorised(request):
    return render(request, "/unauthorised.html")
