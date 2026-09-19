import getpass
import re

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Prompt for a six-digit creator PIN and print its Django password hash."

    def handle(self, *args, **options):
        first = getpass.getpass("New six-digit creator PIN: ")
        second = getpass.getpass("Repeat creator PIN: ")
        if first != second:
            raise CommandError("The PIN entries did not match.")
        if not re.fullmatch(r"[0-9]{6}", first):
            raise CommandError("The creator PIN must contain exactly six decimal digits.")
        self.stdout.write(make_password(first, hasher="argon2"))

