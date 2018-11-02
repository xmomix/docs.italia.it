"""Rebuild documentation for all projects"""

from __future__ import absolute_import
from django.core.management.base import BaseCommand, CommandError

from readthedocs.builds.models import Build, Version
from readthedocs.projects.tasks import UpdateDocsTask
from readthedocs.projects.models import Project


from readthedocs.docsitalia.models import Publisher, PublisherProject


class Command(BaseCommand):

    """Rebuild all projects command"""

    help = 'Rebuild projects'

    def add_arguments(self, parser):
        """adds arguments"""
        parser.add_argument(
            '--publisher', nargs='?', type=str,
            help='A publisher project slug'
        )
        parser.add_argument(
            '--document', nargs='?', type=str,
            help='A Read the docs document slug'
        )
        parser.add_argument(
            '--version', nargs='?', type=str,
            help='A Read the docs version slug'
        )
        parser.add_argument(
            '--async', action='store_true', default=False,
            help='Run the rebuild tasks async'
        )

    def handle(self, *args, **options):
        """handle command"""
        versions = Version.objects.all()
        publisher = options['publisher']
        version = options['version']
        document = options['document']
        run_async = options['async']
        if publisher:
            try:
                publisher_obj = Publisher.objects.get(slug=publisher)
                projects = PublisherProject.objects.filter(
                    publisher=publisher_obj
                ).values_list('projects', flat=True)
                versions = versions.filter(project__in=projects)
            except Publisher.DoesNotExist:
                raise CommandError("Publisher {} doesn't exist".format(publisher))
        if document:
            try:
                project = Project.objects.get(slug=document)
                versions = versions.filter(project=project)
            except Project.DoesNotExist:
                raise CommandError("Project {} doesn't exist".format(document))
        if version:
            try:
                versions = versions.filter(slug=version)
            except Project.DoesNotExist:
                raise CommandError("Project {} doesn't exist".format(document))
        for version in versions:
            task = UpdateDocsTask()
            build = Build.objects.create(
                project=version.project,
                version=version,
                type='html',
                state='triggered',
            )
            kwargs = dict(
                pk=version.project.pk, version_pk=version.pk, build_pk=build.pk, search=True
            )
            if run_async:
                task.apply_async(kwargs=kwargs)
            else:
                task.run(**kwargs)
