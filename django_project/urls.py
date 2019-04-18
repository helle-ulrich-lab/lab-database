"""django_project URL Configuration

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

from wiki.urls import get_pattern as get_wiki_pattern
from django_nyt.urls import get_pattern as get_nyt_pattern

from collection_management.admin import my_admin_site

# Apply a decorator to every urlpattern and URLconf module returned by
# Django's include() method. From https://djangosnippets.org/snippets/2532/

from django.urls.resolvers import URLPattern, URLResolver

class DecoratedURLPattern(URLPattern):
    def resolve(self, *args, **kwargs):
        result = super(DecoratedURLPattern, self).resolve(*args, **kwargs)
        if result:
            result.func = self._decorate_with(result.func)
        return result

class DecoratedURLResolver(URLResolver):
    def resolve(self, *args, **kwargs):
        result = super(DecoratedURLResolver, self).resolve(*args, **kwargs)
        if result:
            result.func = self._decorate_with(result.func)
        return result

def decorated_includes(func, includes, *args, **kwargs):
    urlconf_module, app_name, namespace = includes

    for item in urlconf_module:
        if isinstance(item, URLPattern):
            item.__class__ = DecoratedURLPattern
            item._decorate_with = func

        elif isinstance(item, URLResolver):
            item.__class__ = DecoratedURLResolver
            item._decorate_with = func

    return urlconf_module, app_name, namespace

def wiki_check_login_guest(f):
    """For wiki pages, verify that user is logged in and is not a guest"""

    def decorator(request, **kwargs):
        if request.user.is_authenticated:
            if request.user.groups.filter(name='Guest').exists():
                from django.http import HttpResponseRedirect
                from django.urls import reverse
                from django.contrib import messages
                messages.error(request, 'Guests are not allowed to view our Wiki, you have been automatically redirected to this page')
                return HttpResponseRedirect(reverse('admin:app_list', kwargs={'app_label': 'collection_management'}))
            else:
                return f(request, **kwargs)
        else:
            from django.shortcuts import resolve_url
            from django.utils.six.moves.urllib.parse import urlparse
            from django.contrib.auth.views import redirect_to_login
            from django.contrib.auth import REDIRECT_FIELD_NAME
            path = request.build_absolute_uri()
            resolved_login_url = resolve_url(settings.LOGIN_URL)
            # If the login url is the same scheme and net location then just
            # use the path as the "next" url.
            login_scheme, login_netloc = urlparse(resolved_login_url)[:2]
            current_scheme, current_netloc = urlparse(path)[:2]
            if ((not login_scheme or login_scheme == current_scheme) and
                    (not login_netloc or login_netloc == current_netloc)):
                path = request.get_full_path()
            return redirect_to_login(
                path, resolved_login_url, REDIRECT_FIELD_NAME)
    return decorator

def check_guest(f):
    """If guest, do not allow access to view"""

    def decorator(request, **kwargs):
        if request.user.groups.filter(name='Guest').exists():
            from django.http import HttpResponseRedirect
            from django.urls import reverse
            from django.contrib import messages
            messages.error(request, 'Guests are not allowed to change their password, you have been automatically redirected to this page')
            return HttpResponseRedirect(reverse('admin:app_list', kwargs={'app_label': 'collection_management'}))
        else:
            return f(request, **kwargs)
    return decorator

#################################################
#                 URL PATTERNS                  #
#################################################

from .wiki_pdf_download import CustomAttachmentDownloadView

urlpatterns = [
    url(r'^wiki/(?P<article_id>[0-9]+)/plugin/attachments/download/(?P<attachment_id>[0-9]+)/$', login_required(CustomAttachmentDownloadView.as_view())),
    url(r'^notifications/', include('django_nyt.urls')),
    url(r'^wiki/',  decorated_includes(wiki_check_login_guest, get_wiki_pattern())),
    url(r'^password_change/$', check_guest(auth_views.PasswordChangeView.as_view())),
    url(r'', my_admin_site.urls),
    ]

if settings.DEBUG is True:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)