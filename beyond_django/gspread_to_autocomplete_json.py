import pygsheets
import sys
import os

# Switch from default ASCII to utf-8 encoding
reload(sys)
sys.setdefaultencoding('utf-8')

#Get base path
base_path = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '../../..'))

#Login to GoogleDocs
gc = pygsheets.authorize(service_file=base_path +"/ulrich_lab_intranet/django_project/beyond_django/gdrive_access_credentials.json", no_cache=True)

# Append path of  django_project/djang_project folder to system to easily import ORDER_MASTER_LIST_SHEET_ID
sys.path.append(base_path + '/ulrich_lab_intranet/django_project/django_project')
from private_settings import ORDER_MASTER_LIST_SHEET_ID

#  Order Master List from GoogleDocs and store it in a file as list
spreadsheet = gc.open_by_key(ORDER_MASTER_LIST_SHEET_ID)
lstoforders = spreadsheet.worksheet('title', 'Orders').get_all_values()

# Initialize a list to store product information
lstofprodname = []

# Create two files: one to supply info to the new order form's autocomplete functionality (js)
# and one to store a backup of the Order master list file (txt)
with open(base_path + "/ulrich_lab_intranet/django_project/static/admin/js/order_management/product-autocomplete.js","w") as out_handle_js, open(base_path + "/ulrich_lab_intranet_db_backup/order_master_list.tab","w") as out_handle_txt:

    header_js = "$(function(){\nvar product_names = [\n"
    out_handle_js.write(header_js)

    header_txt = "Submitted\tSupplier\tSupplier Part-No\tInternal order\tPart Description\tQuantity\tPrice\tCost Units (Global)\tStatus\tComments\tCreated\tDelivered\tLocation\tRequestor\tURL\tUrgent?\tDelivery alert?\tCAS Number\tGHS pictogram\tMSDS (click on link to view form)\t\n"
    out_handle_txt.write(header_txt)

    # Loop through all the elements (= rows) in the Order master list
    for line in lstoforders[1:]:
        
        # Output entire row to backup of the Order master list file, tab-delimited
        out_handle_txt.write("\t".join([item.strip().replace('"',"").replace('\n',"") for item in line]) + "\n")
        
        # Output specific order field to file new order form's autocomplete functionality
        prod = line[2].strip().lower()
        if (prod not in lstofprodname) and prod != "none" and prod != "idt-oligo":
            if (len(line[2])>0) and ("?" not in line[2]) :
                jsonlin = '{ value: "' + line[4].encode(encoding='UTF-8',errors='ignore').strip().replace('"',"").replace('\n',"") + '" , data: "'+ line[2].strip().replace("'","").replace('\n',"") + "#" + line[1].strip().replace("'","").replace('\n',"") +'" },\n'
                lstofprodname.append(prod)
                out_handle_js.write(jsonlin)

    footer_js = "];\n\n$('#id_part_description').autocomplete({\nsource: function(request, response) {\nvar results = $.ui.autocomplete.filter(product_names, request.term);\nresponse(results.slice(0, 10));\n},\nselect: function(e, ui) {\nvar extra_data = ui.item.data.split('#');\n$('#id_supplier_part_no').val(extra_data[0]);\n$('#id_supplier').val(extra_data[1]);}\n});\n});"
    out_handle_js.write(footer_js)