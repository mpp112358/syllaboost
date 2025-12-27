#!/usr/bin/env python
from pathlib import Path

import mistune
import orgparse

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Max
from syllabooster.models import *


class Command(BaseCommand):
    help = "Imports syllabus items from the specified file"

    def add_arguments(self, parser):
        parser.add_argument("syllabus", help="Syllabus name")
        parser.add_argument("inputfilename", help="Input file name")
        parser.add_argument("-f", "--format", default="org", help="Input format")

    def parse_org(self, input_string):
        root = orgparse.loads(input_string)
        self.last_item = self.last_item + 1
        for node in root[1:]:
            print(node)
            point = Point(headline=node.heading, contents=node.body)
            point_type = node.get_property("TYPE") or "Theory"
            try:
                point.point_type = PointType.objects.get(name=point_type)
                point.save()
                for tag in node.tags:
                    db_tag, created = Tag.objects.get_or_create(name=tag)
                    point.tags.add(db_tag)
                    point.save()
                SyllabusPoint.objects.create(
                    syllabus=self.syllabus, point=point, position=self.last_item
                )
                self.last_item = self.last_item + 1
            except PointType.DoesNotExist:
                print(
                    f'Error: point type "{point_type}" does not exist. Point "{point}" is ignored.'
                )

    def parse_md(self, input_string):
        markdown_parser = mistune.create_markdown(renderer=None)
        ast = markdown_parser(input_string)
        print(ast)

    def handle(self, *args, **options):
        syllabus_name = options["syllabus"]
        self.syllabus, created = Syllabus.objects.get_or_create(name=syllabus_name)
        max_position = SyllabusPoint.objects.filter(
            syllabus_id=self.syllabus.id
        ).aggregate(Max("position", default=0))
        self.last_item = max_position["position__max"]
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
