#!/usr/bin/env python
import sys
from io import StringIO
from collections import defaultdict

from django.http import JsonResponse
import orgparse

from django.db.models import F
from syllabooster.models import *


class SyllaboostStyler:
    def ERROR(self, message):
        return message

    def WARNING(self, message):
        return message


def renumber_points(course):
    units = Unit.objects.filter(course=course).order_by("position")
    point_number = 1
    for unit in units:
        points = CoursePoint.objects.filter(unit=unit).order_by("position")
        for point in points:
            point.position = point_number
            point.save()
            point_number = point_number + 1


def should_be_imported(unit, unitnumbers):
    if len(unitnumbers) > 0:
        return unit in unitnumbers
    return True


def is_unit(node):
    return node.level and node.level == 1


def is_point(node):
    return node.level and node.level == 2


def parse_org(
    course,
    input_string,
    user,
    output=sys.stdout,
    styler=SyllaboostStyler(),
):
    root = orgparse.loads(input_string)
    current_unit = 0
    current_point_position_in_unit = defaultdict(int)
    unit_tags = {}
    unit = None
    # Both units and points are imported in the order in which they are found in the org file.
    # We expect the nodes in root[1:] to be stored in the order in which they were found in the file.
    # TODO: check the above expectation is fulfilled by orgparse.
    for node in root[1:]:
        if is_unit(node):
            current_unit += 1
            node.unit = current_unit
            if Unit.objects.filter(course=course, position=current_unit).exists():
                Unit.objects.filter(course=course, position=current_unit).delete()
            unit = Unit.objects.create(
                course=course,
                position=current_unit,
                title=node.heading,
            )
            unit_tags[current_unit] = []
            for tag in node.tags:
                unit_tags[current_unit].append(tag)
        elif is_point(node):
            point_type = node.get_property("TYPE") or "Theory"
            output.write(f'Importing point "{node.heading}" of type {point_type}')
            point, created = Point.objects.get_or_create(headline=node.heading)
            point.contents = node.body
            point.save()
            for tag in node.tags:
                db_tag, created = Tag.objects.get_or_create(name=tag)
                point.tags.add(db_tag)
            point.point_type = PointType.objects.get(name=point_type.lower())
            point.save()

            state = None
            todo = node.todo.lower()
            if todo:
                try:
                    state = DeliveryState.objects.filter(
                        point_type_id=point.point_type.id
                    ).get(name=todo)
                except DeliveryState.DoesNotExist:
                    state = None
                    unit = None
            if not (node.parent is root):
                unit_position = node.parent.unit
                current_point_position_in_unit[unit_position] += 1
                point_position = (
                    current_point_position_in_unit[unit_position] + 1000 * unit_position
                )
                unit = Unit.objects.get(course=course, position=unit_position)
                for tag in unit_tags[unit_position]:
                    db_tag, created = Tag.objects.get_or_create(name=tag)
                    point.tags.add(db_tag)
                    point.save()
                coursepoint, created = CoursePoint.objects.get_or_create(
                    course=course, point=point
                )
                coursepoint.position = point_position
                coursepoint.state = state
                coursepoint.unit = unit
                coursepoint.save()

    return {"status": "ok"}


def parse_md(input_string):
    return {"status": "error", "message": "Not implemented"}


def import_course(
    course_name,
    input_string,
    username,
    input_format,
    output=sys.stdout,
    styler=SyllaboostStyler(),
):

    user = None
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return {"status": "error", "message": f"User {username} does not exist"}

    course, created = Course.objects.get_or_create(name=course_name, user=user)
    if input_format == "md":
        return parse_md(input_string)
    elif input_format == "org":
        return parse_org(course, input_string, user, output, styler)
