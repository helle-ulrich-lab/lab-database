from django import template

from laboratory_management.models import Category, Url

register = template.Library()

@register.simple_tag
def get_homepage_urls():
    home_page_urls = []
    for cat in Category.objects.all():
        if not cat.hidden:
            row_title = [(cat.name, cat.colour)]
            urls_in_cat = [(x.title, x.url) for x in Url.objects.all().filter(category=cat.id) if not x.hidden]
            home_page_urls.append(row_title + urls_in_cat)
    return home_page_urls