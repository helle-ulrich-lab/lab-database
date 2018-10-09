# -*- coding: utf-8 -*-

from __future__ import unicode_literals

#################################################
#    DJANGO 'CORE' FUNCTIONALITIES IMPORTS      #
#################################################

from django.contrib import admin
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.core.mail import send_mail

#################################################
#        ADDED FUNCTIONALITIES IMPORTS          #
#################################################

import os
import sys
import time

# Google Sheets API to add new orders to Order Master List
import pygsheets

#################################################
#                OTHER IMPORTS                  #
#################################################

from django_project.private_settings import ORDER_MASTER_LIST_SHEET_ID

#################################################
#                 ORDER PAGES                   #
#################################################

class OrderPage(admin.ModelAdmin):
    list_display = ()

    def message_user(self, *args):
        pass
    
    def save_model(self, request, obj, form, change):
        '''Save order to Google Sheet Master Order List, not to MariaDB database'''

        if obj.pk == None:
            obj.created_by = request.user
            
            # Set value of urgent and delivery_alert fields to 'Yes', if ticked in the form
            if obj.urgent:
                urgent = ["Urgent", "Yes"]
            else:
                urgent = ["Urgent", ""]
            
            if obj.delivery_alert:
                delivery_alert = ["Delivery alert", "Yes"]
            else:
                delivery_alert = ["Delivery alert", ""]
            
            try:
                # Log in to GoogleDocs
                base_path = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..'))
                gc = pygsheets.authorize(service_file=base_path + "/beyond_django/gdrive_access_credentials.json", no_cache=True)
                # Open Order Master List spreadsheet
                spreadsheet = gc.open_by_key(ORDER_MASTER_LIST_SHEET_ID)
                # Open Orders sheet
                worksheet = spreadsheet.worksheet('title', 'Orders')
                # Create new order row to be added to the Orders spreadsheet
                new_order = [time.strftime("%Y-%m-%d %H:%M:%S"), obj.supplier, "'" + obj.supplier_part_no, '',
                obj.part_description.strip().replace('"',"").replace('\n',""), obj.quantity, obj.price, obj.cost_unit.name, '', obj.comment,
                '', '', obj.location.name, obj.created_by.labuser.abbreviation_code,
                obj.url, urgent[1], delivery_alert[1],]
                # Insert new order
                worksheet.insert_rows(1, number=1, values=new_order, inherit=False)
                # If successful, message user
                messages.success(request, 'Your order was added successfully')
            except Exception as err1:
                # If order cannot be added to Google Sheet, try sending it by email to ulrich-orders@imb-mainz.de
                try:
                    new_order[15] = ": ".join(urgent)
                    new_order[16] = ": ".join(delivery_alert)
                    message = 'There was a problem adding the following order to the Order Master List.\n\n' + \
                    'Please, review it, and should you need to, add it to the Order Master List.\n\n' + \
                    '\n'.join([str(x).lstrip("'") for x in new_order if len(x) > 0 ])
                    send_mail(
                        'New order from the Ulrich Lab Intranet',
                        message,
                        'system@imbc2.imb.uni-mainz.de',
                        ['ulrich-orders@imb-mainz.de'],
                        fail_silently=False,)
                    # If email successfully sent, message user
                    messages.warning(request, 'Your order was not added to the Order list. However, it was successfully sent by email to the lab managers')
                except Exception as err2:
                    # If order cannot be added to Google Sheet or sent by email, send error message to user
                    messages.error(request, "Your order could not be processed. Error: " + str(err1) + ', ' + str(err2))
                
    def response_add(self, request, obj, post_url_continue=None):
        '''Redirect user to the admin homepage after order submission'''
        
        return HttpResponseRedirect(reverse("admin:index"))
    
    # Include custom JS and CSS files to Order pages
    class Media:
        css = {
            "all": ('admin/css/vendor/jqueryui/jquery-ui.min.css', 
            'admin/css/vendor/jqueryui/jquery-ui.structure.min.css', 
            'admin/css/vendor/jqueryui/jquery-ui.theme.min.css',
            )}
        js = ('admin/js/vendor/jquery/jquery.js',
        'admin/js/vendor/jqueryui/jquery-ui.min.js',
        'admin/js/order_management/product-autocomplete.js',)
    
    def add_view(self,request,extra_content=None):
        '''Override default add_view to show only desired fields'''
        self.fields = ('supplier','supplier_part_no', 'part_description', 'quantity', 'price', 'cost_unit', 'urgent',
        'delivery_alert', 'location', 'comment', 'url')
        return super(OrderPage,self).add_view(request)

#################################################
#           ORDER COST UNIT PAGES               #
#################################################

class CostUnitPage(admin.ModelAdmin):
    list_display = ('id','name',)
    list_display_links = ('id','name', )
    list_per_page = 25
    ordering = ['id']

#################################################
#           ORDER LOCATION PAGES                #
#################################################

class LocationPage(admin.ModelAdmin):
    list_display = ('id','name')
    list_display_links = ('id','name', )
    list_per_page = 25
    ordering = ['id']