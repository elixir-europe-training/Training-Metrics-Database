from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Create user groups'

    def handle(self, *args, **options):
        self.create_group(
            name='NodeUserGroup',
            permissions=[
                'view_question',
                'add_question',
                'change_question',
                'view_questionset',
                'add_questionset',
                'change_questionset',
                'view_questionsuperset',
                'add_questionsuperset',
                'change_questionsuperset',
                'view_answer',
                'add_answer',
                'change_answer'
                'view_dataset',
                'add_dataset',
                'change_dataset',
                'delete_dataset',
            ]
        )

    def create_group(self, name, permissions):
        # Create a new group
        node_user_group, created = Group.objects.get_or_create(name=name)

        # Assign permissions to the group
        for perm_name in permissions:
            perm = Permission.objects.get(codename=perm_name)
            node_user_group.permissions.add(perm)

        # Save the group to apply changes
        node_user_group.save()
