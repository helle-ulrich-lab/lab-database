from os.path import join, dirname
from subprocess import check_output
from datetime import datetime
import pathlib
import xlrd
import csv

from collection.models.sa_cerevisiae_strain import SaCerevisiaeStrain
from collection.admin.sa_cerevisiae_strain import SaCerevisiaeStrainExportResource

from collection.models.plasmid import Plasmid
from collection.admin.plasmid import PlasmidExportResource

from collection.models.oligo import Oligo
from collection.admin.oligo import OligoExportResource

from collection.models.sc_pombe_strain import ScPombeStrain
from collection.admin.sc_pombe_strain import ScPombeStrainExportResource

from collection.models.e_coli_strain import EColiStrain
from collection.admin.e_coli_strain import EColiStrainExportResource

from collection.models.cell_line import CellLine
from collection.admin.cell_line import CellLineExportResource

from collection.models.antibody import Antibody
from collection.admin.antibody import AntibodyExportResource

from collection.models.worm_strain import WormStrain
from collection.admin.worm_strain import WormStrainExportResource

from collection.models.inhibitor import Inhibitor
from collection.admin.inhibitor import InhibitorExportResource

from collection.models.si_rna import SiRna
from collection.admin.si_rna import SiRnaExportResource

from ordering.models import Order
from ordering.admin import OrderExportResource

from django.conf import settings
BASE_DIR = settings.BASE_DIR
DB_NAME = getattr(settings, 'DB_NAME', '')
DB_USER = getattr(settings, 'DB_USER', '')
DB_PASSWORD = getattr(settings, 'DB_PASSWORD', '')

import warnings
# Suppress silly warning "UserWarning: Using a coordinate with ws.cell is deprecated..."
warnings.simplefilter("ignore")

def export_db_table_as_xlsx(model,export_resource):
    
    def convert_xlsx_to_tsv(file_name):
        xlsx_file = xlrd.open_workbook(file_name)
        sheet = xlsx_file.sheet_by_index(0)
        with open(file_name.replace("xlsx", "tsv"), 'w') as out_handle:
            wr = csv.writer(out_handle, delimiter="\t")
            for rownum in range(sheet.nrows):
                row_values = [str(i).replace("\n", "").replace('\r', '').replace("\t", "") for i in sheet.row_values(rownum)]
                wr.writerow(row_values)

    file_name = join(
        BASE_DIR,
        "db_backup/excel_tables/",
        "{}.xlsx".format(model.__name__))
    with open(file_name, "wb") as out_handle:
        out_data = export_resource().export(model.objects.all().order_by('-id')).xlsx
        out_handle.write(out_data)
    convert_xlsx_to_tsv(file_name)


ENV_DIR = dirname(BASE_DIR)
BACKUP_DIR = join(BASE_DIR, 'db_backup')

# Create any required folder, if necessary
pathlib.Path(join(BACKUP_DIR, 'db_dumps')).mkdir(parents=True, exist_ok=True)
pathlib.Path(join(BACKUP_DIR, 'excel_tables')).mkdir(parents=True, exist_ok=True)
pathlib.Path(join(BACKUP_DIR, 'uploads')).mkdir(parents=True, exist_ok=True)

# Remove all and .gz files older than 7 days from backup folder 
check_output(f"/usr/bin/find {BACKUP_DIR}/db_dumps/ -maxdepth 1 -type f -mtime +7 -iname '*.gz' -delete", shell=True)

# Create datadump for django database and gzip it
CURRENT_DATE_TIME = datetime.now().strftime("%Y%m%d_%H%M")
check_output(f'export PGPASSWORD="{DB_PASSWORD}"; /usr/bin/pg_dump {DB_NAME} -U {DB_USER} -h localhost | /bin/gzip > {BACKUP_DIR}/db_dumps/{CURRENT_DATE_TIME}.sql.gz', shell=True)

# Save db tables as Excel files

DB_TABLES = [(SaCerevisiaeStrain, SaCerevisiaeStrainExportResource),
            (Plasmid, PlasmidExportResource),
            (Oligo, OligoExportResource),
            (ScPombeStrain, ScPombeStrainExportResource),
            (EColiStrain, EColiStrainExportResource),
            (CellLine, CellLineExportResource),
            (Antibody, AntibodyExportResource),
            (WormStrain, WormStrainExportResource),
            (Inhibitor, InhibitorExportResource),
            (SiRna, SiRnaExportResource),
            (Order, OrderExportResource)]

for model, export_resource in DB_TABLES:
    if model.objects.exists(): export_db_table_as_xlsx(model, export_resource)

# Sync uploads
check_output(f"/usr/bin/rsync -a {BASE_DIR}/uploads/ {BACKUP_DIR}/uploads", shell=True)