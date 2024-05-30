from django.core.management.base import BaseCommand
from pathlib import Path
from config.settings import MEDIA_ROOT

FOLDERS = ['collection/antibody/',
           'collection/antibodydoc/',
           'collection/celllinedoc/',
           'collection/ecolistraindoc/',
           'collection/inhibitor/',
           'collection/inhibitordoc/',
           'collection/oligo/',
           'collection/oligodoc/',
           'collection/plasmid/gbk/',
           'collection/plasmid/png/',
           'collection/plasmid/png/',
           'collection/plasmiddoc/',
           'collection/sacerevisiaestraindoc/',
           'collection/scpombestraindoc/',
           'collection/sirna/',
           'collection/sirnadoc/',
           'collection/wormstraindoc/',
           'ordering/msdsform/',
           'ordering/orderextradoc/']


class Command(BaseCommand):
    help = "Creates the folder structure for uploads"

    def handle(self, *args, **options):

        for folder in FOLDERS:
            p = Path(MEDIA_ROOT / folder)
            p.mkdir(parents=True, exist_ok=True)
            # NB: The user running the web app, e.g. www-data,
            # must have access to these folders
            p.chmod(0o770)

        self.stdout.write(
            self.style.SUCCESS('Successfully created upload folder structure')
        )
