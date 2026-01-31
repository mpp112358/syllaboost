#!/usr/bin/env python

from django.core.management.base import BaseCommand, CommandError
from syllabooster.utils.exportcourse import export_course_org
from syllabooster.models import *


class Command(BaseCommand):
    help = "Export course to orgmode"

    def add_arguments(self, parser):
        parser.add_argument("course", help="Course name")
        parser.add_argument("-u", "--user", default="manuel")

    def handle(self, *args, **options):

        username = options["user"]
        self.user = None
        try:
            self.user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError('User "%s" does not exist' % username)
        coursename = options["course"]
        self.course = None
        try:
            self.course = Course.objects.get(user=self.user, name=coursename)
        except Course.DoesNotExist:
            raise CommandError('Course "%s" does not exist.' % coursename)
        self.stdout.write(export_course_org(self.course))
