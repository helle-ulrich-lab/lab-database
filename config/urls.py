from django.conf import settings
from django.conf.urls.static import static
from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.http import HttpResponseRedirect
from django.urls import path, reverse_lazy
from django.urls.conf import include

from common.admin_site import admin_site

ALLOW_OIDC = getattr(settings, "ALLOW_OIDC", False)


def check_guest(f):
    """If guest, do not allow access to view"""

    def decorator(request, **kwargs):
        if request.user.groups.filter(name="Guest").exists():
            messages.error(
                request,
                "Guests are not allowed to change their password, you have been automatically redirected to the home page.",
            )

            return HttpResponseRedirect("/")
        else:
            return f(request, **kwargs)

    return decorator


urlpatterns = [
    path(
        "password_change/",
        check_guest(
            auth_views.PasswordChangeView.as_view(
                success_url=reverse_lazy("admin:password_change_done")
            )
        ),
    ),
    path("", admin_site.urls),
]

if ALLOW_OIDC:
    urlpatterns = [path("oidc/", include("mozilla_django_oidc.urls"))] + urlpatterns

if settings.DEBUG is True:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
