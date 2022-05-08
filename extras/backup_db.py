from os.path import join, dirname, isfile
from os import remove, listdir
from subprocess import check_output
from datetime import datetime
import pathlib

from collection_management.models import SaCerevisiaeStrain
from collection_management.admin import SaCerevisiaeStrainExportResource

from collection_management.models import Plasmid
from collection_management.admin import PlasmidExportResource

from collection_management.models import Oligo
from collection_management.admin import OligoExportResource

from collection_management.models import ScPombeStrain
from collection_management.admin import ScPombeStrainExportResource

from collection_management.models import EColiStrain
from collection_management.admin import EColiStrainExportResource

from collection_management.models import CellLine
from collection_management.admin import CellLineExportResource

from collection_management.models import Antibody
from collection_management.admin import AntibodyExportResource

from order_management.models import Order
from order_management.admin import OrderExportResource

from django_project.settings import BASE_DIR
from django_project.private_settings import DB_NAME 
from django_project.private_settings import DB_USER
from django_project.private_settings import DB_PASSWORD

from wiki.models.article import ArticleRevision

import warnings
# Suppress silly warning "UserWarning: Using a coordinate with ws.cell is deprecated..."
warnings.simplefilter("ignore")

def export_db_table_as_xlsx(model,export_resource):
    
    def convert_xlsx_to_tsv(file_name):
        import xlrd
        import csv
        
        xlsx_file = xlrd.open_workbook(file_name)
        sheet = xlsx_file.sheet_by_index(0)
        with open(file_name.replace("xlsx", "tsv"), 'w') as out_handle:
            wr = csv.writer(out_handle, delimiter="\t")
            for rownum in range(sheet.nrows):
                row_values = [str(i).replace("\n", "").replace('\r', '').replace("\t", "") for i in sheet.row_values(rownum)]
                wr.writerow(row_values)
    
    import os
    from django_project.settings import BASE_DIR

    file_name = os.path.join(
        BASE_DIR,
        "db_backup/excel_tables/",
        "{}.xlsx".format(model.__name__))
    with open(file_name, "wb") as out_handle:
        out_data = export_resource().export(model.objects.all()).xlsx
        out_handle.write(out_data)
    convert_xlsx_to_tsv(file_name)

def save_wiki_article_as_md(article_id):
    from wiki.models.article import ArticleRevision
    from os.path import join
    from django_project.settings import BASE_DIR

    obj = ArticleRevision.objects.filter(article_id=article_id).latest('id')
    file_name = ''.join(obj.title.title().split()) + '.md'
    with open(join(BASE_DIR, 'db_backup/wiki_articles', file_name), 'w') as handle:
        handle.write(obj.content)


ENV_DIR = dirname(BASE_DIR)
BACKUP_DIR = join(BASE_DIR, 'db_backup')

# Create any required folder, if necessary
pathlib.Path(join(BACKUP_DIR, 'db_dumps')).mkdir(parents=True, exist_ok=True)
pathlib.Path(join(BACKUP_DIR, 'excel_tables')).mkdir(parents=True, exist_ok=True)
pathlib.Path(join(BACKUP_DIR, 'wiki_articles')).mkdir(parents=True, exist_ok=True)
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
            (Order, OrderExportResource)]

for model, export_resource in DB_TABLES:
    if model.objects.exists(): export_db_table_as_xlsx(model, export_resource)

# Save wiki articles as markdown files

for f in listdir(join(BACKUP_DIR, 'wiki_articles')):
    file_path = join(BACKUP_DIR, 'wiki_articles/', f)
    if isfile(file_path):
        remove(file_path)

article_ids = set(ArticleRevision.objects.all().values_list('article_id', flat=True))
for article_id in article_ids:
    save_wiki_article_as_md(article_id)

# Sync uploads
check_output(f"/usr/bin/rsync -a {BASE_DIR}/uploads/ {BACKUP_DIR}/uploads", shell=True)