import os
import sys
import django
from django.core.management import execute_from_command_line

def runtests():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.test_settings")
    django.setup()
    args = [sys.argv[0], "test"]
    execute_from_command_line(args)

if __name__ == "__main__":
    runtests()
