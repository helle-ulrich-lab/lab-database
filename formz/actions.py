import zipfile

from bs4 import BeautifulSoup
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.template.loader import get_template
from django.utils import timezone

from formz.models import Header

User = get_user_model()


@admin.action(description="Export Formblatt Z for selected items")
def formz_as_html(modeladmin, request, queryset):
    """Export ForblattZ as html"""

    # Get FormZ header
    if Header.objects.all().first():
        formz_header = Header.objects.all().first()
    else:
        formz_header = None

    # Get PI
    try:
        pi = User.objects.get(is_pi=True)
    except Exception:
        pi = None

    # Create response
    model_name = queryset[0].__class__.__name__
    response = HttpResponse(content_type="application/zip")
    response["Content-Disposition"] = (
        'attachment; filename="formblattz_{}_{}.zip'.format(
            model_name.lower(), timezone.now().strftime("%Y%m%d%H%M%S")
        )
    )

    template = get_template("admin/formz/formz_for_export_new.html")
    # Generate zip file
    with zipfile.ZipFile(response, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for obj in queryset:
            map_attachment_type = request.POST.get(
                "map_attachment_type", default="none"
            )
            html = template.render(
                {
                    "object": obj,
                    "formz_header": formz_header,
                    "map_attachment_type": map_attachment_type,
                    "pi": pi,
                }
            )
            html = BeautifulSoup(html, features="lxml")
            html = html.prettify("utf-8")
            zip_file.writestr(f"{model_name}_{obj.id}.html", html)

    return response
