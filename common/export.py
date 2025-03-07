import csv

import xlrd
from django.http import HttpResponse
from django.utils import timezone


def export_objects(request, queryset, export_data):
    file_format = request.POST.get("format", default="none")
    now = timezone.localtime(timezone.now())
    file_name = f"{queryset.model.__name__}_{now.strftime('%Y%m%d_%H%M%S')}"

    # Excel file
    if file_format == "xlsx":
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="{file_name}.xlsx'
        response.write(export_data.xlsx)

    # TSV file
    elif file_format == "tsv":
        response = HttpResponse(content_type="text/tab-separated-values")
        response["Content-Disposition"] = f'attachment; filename="{file_name}.tsv'
        xlsx_file = xlrd.open_workbook(file_contents=export_data.xlsx)
        sheet = xlsx_file.sheet_by_index(0)
        wr = csv.writer(response, delimiter="\t")
        # Get rid of return chars
        for rownum in range(sheet.nrows):
            row_values = [
                str(i).replace("\n", "").replace("\r", "").replace("\t", "")
                for i in sheet.row_values(rownum)
            ]
            wr.writerow(row_values)

    return response
