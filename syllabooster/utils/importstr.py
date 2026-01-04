#!/usr/bin/env python
import sys
from io import StringIO

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


def parse_org(
    course,
    input_string,
    user,
    unitnumbers,
    insert,
    force,
    output=sys.stdout,
    styler=SyllaboostStyler(),
):
    root = orgparse.loads(input_string)
    current_unit = 0
    next_point = 1
    unit_tags = {}
    unit = None
    output.write(f"Unit numbers to be imported: {unitnumbers or 'all'}")
    for node in root[1:]:
        if node.level == 1:
            current_unit = int(node.get_property("POSITION"))
            node.unit = current_unit
            output.write(f'Found unit "{node.heading}" with position {current_unit}')
            if should_be_imported(current_unit, unitnumbers):
                output.write(f"Position {current_unit} should be imported.")
                if Unit.objects.filter(course=course, position=current_unit).exists():
                    if not insert:
                        if not force:
                            output.write(
                                styler.WARNING(
                                    f"There is already a unit with number {current_unit} in course {course.name} for user {user.username}: it will be replaced."
                                )
                            )
                            confirm = input("Are you sure you want to proceed? [y/N]: ")
                            if confirm.lower() not in ["y", "yes"]:
                                output.write(styler.ERROR("Unit skipped."))
                                continue
                        Unit.objects.filter(
                            course=course, position=current_unit
                        ).delete()
                    else:
                        Unit.objects.filter(
                            course=course, position__gte=current_unit
                        ).update(position=F("position") + 10000)
                        Unit.objects.filter(
                            course, position__gte=current_unit + 10000
                        ).update(position=F("position") - 9999)

                unit = Unit.objects.create(
                    course=course,
                    position=current_unit,
                    title=node.heading,
                )
                unit_tags[current_unit] = []
                for tag in node.tags:
                    unit_tags[current_unit].append(tag)
        elif should_be_imported(current_unit, unitnumbers) and node.level == 2:
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
                unit = Unit.objects.get(course=course, position=unit_position)
                for tag in unit_tags[unit_position]:
                    db_tag, created = Tag.objects.get_or_create(name=tag)
                    point.tags.add(db_tag)
                    point.save()

            coursepoint = CoursePoint(
                course=course,
                point=point,
                position=next_point,
                state=state,
                unit=unit,
            )
            coursepoint.save()
            next_point = next_point + 1
            renumber_points(course)

    return {"status": "ok", "units": f"{unitnumbers}"}


def parse_md(input_string, unitnumbers, insert=False, force=True):
    return {"status": "error", "message": "Not implemented"}


def import_unit(
    course_name,
    input_string,
    username,
    input_format,
    unitnumbers=[],
    insert=False,
    force=True,
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
        return parse_md(input_string, unitnumbers, insert, force)
    elif input_format == "org":
        return parse_org(
            course, input_string, user, unitnumbers, insert, force, output, styler
        )
