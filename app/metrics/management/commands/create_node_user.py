import getpass

from django.core.management.base import BaseCommand

from metrics.models import User

import string
import random

N = 7


# using random.choices()
# generating random strings


# print result

class Command(BaseCommand):
    help = "Creates a new node user"

    def add_arguments(self, parser):
        parser.add_argument("-u", "--username", help='Username for the user for non-interactive mode')
        parser.add_argument("--random-pass", help='Whether password input should not be requested and a password is '
                                                  'automatically computed instead', action='store_true')
        parser.add_argument('-N', type=int, default=8)
        parser.add_argument('--show', help='Whether final credentials should be shown to the command line instead of '
                                           'being placed inside a file', action='store_true')

    def handle(self, *args, **options):
        username = input('Enter username for user: ') if options['username'] is None else options['username']
        if User.objects.filter(username=username).exists():
            print(f'Username "{username}" is not available')
            return
        if not options['random_pass']:
            while True:
                pass0 = getpass.getpass(prompt='Enter password:')
                pass1 = getpass.getpass(prompt='Enter password again:')
                if pass0 != pass1:
                    print('Passwords do not match')
                else:
                    break
        else:
            if options['N'] < 1:
                print('N argument must be at least 1')
                return
            N = options['N']

            pass0 = ''.join(random.choices(string.ascii_uppercase + string.digits + string.ascii_lowercase, k=N))

        user = User.objects.create_user(username=username, password=pass0)

        if options['show']:
            print(f'User created - username: "{user.username}", password: "{pass0}"')
        else:
            with open(f'user-{user.username}.txt', 'w') as user_credentials_out:
                user_credentials_out.write(f'username: {user.username}, password: {pass0}')
