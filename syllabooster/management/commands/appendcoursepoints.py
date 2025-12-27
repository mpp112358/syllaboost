#!/usr/bin/env python
#
# Adds a command to manage.py to import a Course from an org file
#
# The org file should be structured like this (text in brackets is for explaning purposes,
# it should not appear in the file):
#
# * (Unit 1) The first unit
# ** (Point 1) Whatever
#    :PROPERTIES:
#    :TYPE: theory
#    :END:
# ** (Point 2) Whatever
# * (Unit 2) The second unit
# ** (Point 3) Whatever
# ** (Point 4) Whatever
#
# Numbering will happen automatically: units are numbered in the order they appear in the file,
# and points are numbered in the order they appear in the file independently of the unit they
# belong to.
#
# The type of a poit is specified through a PROPERTY called TYPE.
#
# Any level 1 heading is parsed as a unit.
#
# Any level 2 heading is parsed as a point.
#
# Any level > 2 heading is parsed as part of their parent's contents.


from pathlib import Path

import mistune
import orgparse

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Max
from syllabooster.models import *


class Command(BaseCommand):
    help = "Imports course items from the specified file"

    def add_arguments(self, parser):
        parser.add_argument("course", help="Course name")
        parser.add_argument("inputfilename", help="Input file name")
        parser.add_argument("-f", "--format", default="org", help="Input format")

    def parse_org(self, input_string):
        root = orgparse.loads(input_string)
        self.last_unit = self.last_unit + 1
        self.last_point = self.last_point + 1
        for node in root[1:]:
            print(node)
            if node.level == 1:
                unit, created = Unit.objects.get_or_create(
                    course=self.course, position=self.last_unit
                )
                self.last_unit = self.last_unit + 1

            point = Point(headline=node.heading, contents=node.body)
            point_type = node.get_property("TYPE") or "Theory"
            todo = node.todo.lower()
            try:
                point.point_type = PointType.objects.get(name=point_type)
                point.save()
                for tag in node.tags:
                    db_tag, created = Tag.objects.get_or_create(name=tag)
                    point.tags.add(db_tag)
                    point.save()
                state = None
                if todo:
                    try:
                        state = DeliveryState.objects.filter(
                            point_type_id=point.point_type.id
                        ).get(name=todo)
                    except DeliveryState.DoesNotExist:
                        state = None
                CoursePoint.objects.create(
                    course=self.course,
                    point=point,
                    position=self.last_point,
                    state=state,
                )
                self.last_point = self.last_point + 1
            except PointType.DoesNotExist:
                print(
                    f'Error: point type "{point_type}" does not exist. Point "{point}" is ignored.'
                )

    def parse_md(self, input_string):
        markdown_parser = mistune.create_markdown(renderer=None)
        ast = markdown_parser(input_string)
        print(ast)

    def handle(self, *args, **options):
        course_name = options["course"]
        self.course, created = Course.objects.get_or_create(name=course_name)
        max_point_position = CoursePoint.objects.filter(
            course_id=self.course.id
        ).aggregate(Max("position", default=0))
        self.last_point = max_point_position["position__max"]
        max_unit_position = Unit.objects.filter(course_id=self.course.id).aggregate(
            Max("position", default=0)
        )
        self.last_unit = max_unit_position["position__max"]
        inputfilename = options["inputfilename"]
        inputfilepath = Path(inputfilename)
        if not inputfilepath.is_file():
            raise CommandError('File "%s" not found' % inputfilename)
        with open(inputfilepath, "r") as mdfile:
            input_string = mdfile.read()

        input_format = options["format"]
        if input_format == "md":
            self.parse_md(input_string)
        elif input_format == "org":
            self.parse_org(input_string)
