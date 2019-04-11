from collection_management.models import SaCerevisiaeStrain
from collection_management.admin import SaCerevisiaeStrainExportResource

from collection_management.models import HuPlasmid
from collection_management.admin import HuPlasmidExportResource

from collection_management.models import Oligo
from collection_management.admin import OligoExportResource

from collection_management.models import ScPombeStrain
from collection_management.admin import ScPombeStrainExportResource

# from collection_management.models import NzPlasmid
# from collection_management.admin import NzPlasmidExportResource

from collection_management.models import EColiStrain
from collection_management.admin import EColiStrainExportResource

from collection_management.models import MammalianLine
from collection_management.admin import MammalianLineExportResource

from collection_management.models import Antibody
from collection_management.admin import AntibodyExportResource

from order_management.models import Order
from order_management.admin import OrderExportResource


def export_xlsx(model,export_resource):
    
    def convert_xlsx_to_tsv(file_name):
        import xlrd
        import csv
        
        xlsx_file = xlrd.open_workbook(file_name)
        sheet = xlsx_file.sheet_by_index(0)
        with open(file_name.replace("xlsx", "tsv"), 'w') as out_handle:
            wr = csv.writer(out_handle, delimiter="\t")
            for rownum in range(sheet.nrows):
                wr.writerow(sheet.row_values(rownum))
    
    import time
    import os
    from django_project.settings import BASE_DIR

    file_name = os.path.join(
        BASE_DIR,
        "ulrich_lab_intranet_db_backup/excel_tables/",
        "{}.xlsx".format(model.__name__))
    with open(file_name, "wb") as out_handle:
        out_data = export_resource().export(model.objects.all()).xlsx
        out_handle.write(out_data)
    convert_xlsx_to_tsv(file_name)

export_xlsx(SaCerevisiaeStrain, SaCerevisiaeStrainExportResource)
export_xlsx(HuPlasmid, HuPlasmidExportResource)
export_xlsx(Oligo, OligoExportResource)
export_xlsx(ScPombeStrain, ScPombeStrainExportResource)
# export_xlsx(NzPlasmid, NzPlasmidExportResource)
export_xlsx(EColiStrain, EColiStrainExportResource)
export_xlsx(MammalianLine, MammalianLineExportResource)
export_xlsx(Antibody, OrderExportResource)
export_xlsx(Order, OrderExportResource)