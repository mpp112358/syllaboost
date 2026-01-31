#!/usr/bin/env python

from syllabooster.models import *


def export_course_org(course):

    output = f"#+title: {course.name}\n#+TODO: PENDING(p) | DELIVERED(d)\n#+TODO: UNASSIGNED(u) ASSIGNED(a) | REVIEWED(r)\n"

    units = Unit.objects.filter(course=course)

    for unit in units:
        output += (
            f"* {unit.title}\n  :PROPERTIES:\n  :POSITION: {unit.position}\n  :END:\n"
        )
        points = CoursePoint.objects.filter(course=course, unit=unit)
        for point in points:
            point_tags = ""
            for tag in point.point.tags.all():
                point_tags += f" :{tag.name}:"
            content_lines = point.point.contents.splitlines()
            output += f"** {point.state.display_name} {point.point.headline} {point_tags}\n   :PROPERTIES:\n   :TYPE: {point.point.point_type}\n   :POSITION: {point.position}\n   :END:\n"
            for line in content_lines:
                output += f"   {line}\n"

    return output
