import csv
import importlib
import pathlib
import warnings
from datetime import datetime
from os.path import dirname, join
from subprocess import check_output

import xlrd
from django.apps import apps
from django.conf import settings

from collection.models import WormStrainAllele
from collection.wormstrain.export import WormStrainAlleleExportResource
from ordering.models import Order
from ordering.order.export import OrderExportResource

COLLECTION_MODELS = [
    "Antibody",
    "CellLine",
    "EColiStrain",
    "Inhibitor",
    "Oligo",
    "Plasmid",
    "SaCerevisiaeStrain",
    "ScPombeStrain",
    "SiRna",
    "WormStrain",
]

DB_TABLES = [
    (
        apps.get_model("collection", m),
        getattr(
            importlib.import_module(f"collection.{m.lower()}.export"),
            f"{m}ExportResource",
        ),
    )
    for m in COLLECTION_MODELS
]

DB_TABLES = DB_TABLES + [
    (WormStrainAllele, WormStrainAlleleExportResource),
    (Order, OrderExportResource),
]

BASE_DIR = settings.BASE_DIR
DB_NAME = getattr(settings, "DB_NAME", "")
DB_USER = getattr(settings, "DB_USER", "")
DB_PASSWORD = getattr(settings, "DB_PASSWORD", "")

# Suppress silly warning "UserWarning: Using a coordinate with ws.cell is deprecated..."
warnings.simplefilter("ignore")


def export_db_table_as_xlsx(model, export_resource):
    def convert_xlsx_to_tsv(file_name):
        xlsx_file = xlrd.open_workbook(file_name)
        sheet = xlsx_file.sheet_by_index(0)
        with open(file_name.replace("xlsx", "tsv"), "w") as out_handle:
            wr = csv.writer(out_handle, delimiter="\t")
            for rownum in range(sheet.nrows):
                row_values = [
                    str(i).replace("\n", "").replace("\r", "").replace("\t", "")
                    for i in sheet.row_values(rownum)
                ]
                wr.writerow(row_values)

    file_name = join(
        BASE_DIR, "db_backup/excel_tables/", "{}.xlsx".format(model.__name__)
    )
    with open(file_name, "wb") as out_handle:
        out_data = export_resource().export(model.objects.all().order_by("-id")).xlsx
        out_handle.write(out_data)
    convert_xlsx_to_tsv(file_name)


ENV_DIR = dirname(BASE_DIR)
BACKUP_DIR = join(BASE_DIR, "db_backup")

# Create any required folder, if necessary
pathlib.Path(join(BACKUP_DIR, "db_dumps")).mkdir(parents=True, exist_ok=True)
pathlib.Path(join(BACKUP_DIR, "excel_tables")).mkdir(parents=True, exist_ok=True)
pathlib.Path(join(BACKUP_DIR, "uploads")).mkdir(parents=True, exist_ok=True)

# Remove all and .gz files older than 7 days from backup folder
check_output(
    f"/usr/bin/find {BACKUP_DIR}/db_dumps/ -maxdepth 1 -type f -mtime +7 -iname '*.gz' -delete",
    shell=True,
)

# Create datadump for django database and gzip it
CURRENT_DATE_TIME = datetime.now().strftime("%Y%m%d_%H%M")
check_output(
    f'export PGPASSWORD="{DB_PASSWORD}"; /usr/bin/pg_dump {DB_NAME} -U {DB_USER} -h localhost | /bin/gzip > {BACKUP_DIR}/db_dumps/{CURRENT_DATE_TIME}.sql.gz',
    shell=True,
)

for model, export_resource in DB_TABLES:
    if model.objects.exists():
        export_db_table_as_xlsx(model, export_resource)

# Sync uploads
check_output(f"/usr/bin/rsync -a {BASE_DIR}/uploads/ {BACKUP_DIR}/uploads", shell=True)
