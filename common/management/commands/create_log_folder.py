from pathlib import Path

from django.core.management.base import BaseCommand

from config.settings import BASE_DIR


class Command(BaseCommand):
    help = "Creates the logs folder"

    def handle(self, *args, **options):
        p = Path(BASE_DIR / "logs")
        p.mkdir(parents=True, exist_ok=True)
        # NB: The user running the web app, e.g. www-data,
        # must have access to these folders
        p.chmod(0o770)

        self.stdout.write(self.style.SUCCESS("Successfully created logs folder"))
