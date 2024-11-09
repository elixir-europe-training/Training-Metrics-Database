from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError
from metrics.models import Question, QuestionSet, QuestionSuperSet


class Command(BaseCommand):
    help = 'Assign permissions to NodeUserGroup'

    def handle(self, *args, **options):
        self.assign_group()

    def assign_group(self):
        # Current nodes in the system
        node_users = ['be',
                      'ch',
                      'cz',
                      'de',
                      'dk',
                      'ebi',
                      'ee',
                      'embl',
                      'es',
                      'fi',
                      'fr',
                      'gr',
                      'hu',
                      'hub',
                      'ie',
                      'il',
                      'it',
                      'lu',
                      'nl',
                      'no',
                      'pt',
                      'se',
                      'si',
                      'uk'
                     ]


        # Create a new group
        node_user_group, created = Group.objects.get_or_create(name= 'NodeUserGroup')

        # Define the permissions to add
        permissions = [
            'view_question', 'add_question', 'change_question', 'delete_question',
            'view_questionset', 'add_questionset', 'change_questionset', 'delete_questionset',
            'view_questionsuperset', 'add_questionsuperset', 'change_questionsuperset', 'delete_questionsuperset',
            'view_answer', 'add_answer', 'change_answer', 'delete_answer'
        ]

        # Assign permissions to the group
        for perm_name in permissions:
            perm = Permission.objects.get(codename = perm_name)
            node_user_group.permissions.add(perm)

        # Save the group to apply changes
        node_user_group.save()

        # Add a user to this group
        from django.contrib.auth.models import User
        for node_user in node_users:
            user = User.objects.get(username = node_user)
            user.groups.add(node_user_group)
            user.is_staff = True
            user.save()