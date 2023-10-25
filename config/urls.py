"""config URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""

from django.conf.urls import url
from django.conf import settings
from django.urls.conf import include
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.urls import path

from config.private_settings import ALLOW_OIDC
from common.admin import main_admin_site


def check_guest(f):
    """If guest, do not allow access to view"""

    def decorator(request, **kwargs):
        
        if request.user.groups.filter(name='Guest').exists():
            
            from django.http import HttpResponseRedirect
            from django.urls import reverse
            from django.contrib import messages
            
            messages.error(request, 'Guests are not allowed to change their password, you have been automatically redirected to the home page.')
            
            return HttpResponseRedirect('/')
        else:

            return f(request, **kwargs)

    return decorator

#################################################
#                 URL PATTERNS                  #
#################################################

urlpatterns = [
    path('password_change/', check_guest(auth_views.PasswordChangeView.as_view(success_url=reverse_lazy('admin:password_change_done')))),
    path('', main_admin_site.urls),
    ]

if ALLOW_OIDC:
    urlpatterns = [path('oidc/', include('mozilla_django_oidc.urls'))] + urlpatterns

if settings.DEBUG is True:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)