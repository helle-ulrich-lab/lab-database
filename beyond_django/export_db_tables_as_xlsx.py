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

from collection_management.models import MammalianLine
from collection_management.admin import MammalianLineExportResource

from collection_management.models import Antibody
from collection_management.admin import AntibodyExportResource

from order_management.models import Order
from order_management.admin import OrderExportResource

import warnings
# Suppress silly warning "UserWarning: Using a coordinate with ws.cell is deprecated..."
warnings.simplefilter("ignore")

def export_xlsx(model,export_resource):
    
    def convert_xlsx_to_tsv(file_name):
        import xlrd
        import csv
        
        xlsx_file = xlrd.open_workbook(file_name)
        sheet = xlsx_file.sheet_by_index(0)
        with open(file_name.replace("xlsx", "tsv"), 'w') as out_handle:
            wr = csv.writer(out_handle, delimiter="\t")
            for rownum in range(sheet.nrows):
                row_values = [i.replace("\n", "").replace("\t", "") for i in sheet.row_values(rownum)]
                wr.writerow(row_values)
    
    import time
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

export_xlsx(SaCerevisiaeStrain, SaCerevisiaeStrainExportResource)
export_xlsx(Plasmid, PlasmidExportResource)
export_xlsx(Oligo, OligoExportResource)
export_xlsx(ScPombeStrain, ScPombeStrainExportResource)
export_xlsx(EColiStrain, EColiStrainExportResource)
export_xlsx(MammalianLine, MammalianLineExportResource)
export_xlsx(Antibody, AntibodyExportResource)
export_xlsx(Order, OrderExportResource)