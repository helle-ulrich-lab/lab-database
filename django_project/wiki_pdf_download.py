import mimetypes
import os
from datetime import datetime

from django.http import HttpResponse
from django.utils import dateformat
from django.utils.encoding import filepath_to_uri
from django.utils.http import http_date
from wiki.conf import settings
from wiki.plugins.attachments.views import AttachmentDownloadView
from wiki.plugins.attachments import settings
from django.http import Http404, HttpResponseRedirect

from django_project.settings import MEDIA_ROOT

def django_sendfile_response(request, filepath):
    from sendfile import sendfile
    return sendfile(request, filepath)

def send_file(request, filepath, last_modified=None, filename=None):
    fullpath = filepath
    # Respect the If-Modified-Since header.
    statobj = os.stat(fullpath)
    if filename:
        mimetype, encoding = mimetypes.guess_type(filename)
    else:
        mimetype, encoding = mimetypes.guess_type(fullpath)

    mimetype = mimetype or 'application/octet-stream'

    try:
        settings.USE_SENDFILE
        response = django_sendfile_response(request, filepath)
    except:
        #response = HttpResponse(open(fullpath, 'rb').read(), content_type=mimetype)
        response = HttpResponse(content_type=mimetype)
        response['X-Accel-Redirect'] = os.path.join("/secret/", fullpath.replace(MEDIA_ROOT,""))

    if not last_modified:
        response["Last-Modified"] = http_date(statobj.st_mtime)
    else:
        if isinstance(last_modified, datetime):
            last_modified = float(dateformat.format(last_modified, 'U'))
        response["Last-Modified"] = http_date(epoch_seconds=last_modified)

    response["Content-Length"] = statobj.st_size

    if encoding:
        response["Content-Encoding"] = encoding
    if filename:
        filename_escaped = filepath_to_uri(filename)
        if 'pdf' in mimetype.lower():
            response["Content-Disposition"] = "inline; filename=%s" % filename_escaped
        else:
            response["Content-Disposition"] = "attachment; filename=%s" % filename_escaped

    return response

class CustomAttachmentDownloadView(AttachmentDownloadView):
    def get(self, request, *args, **kwargs):
        if self.revision:
            if settings.USE_LOCAL_PATH:
                try:
                    return send_file(
                        request,
                        self.revision.file.path,
                        self.revision.created,
                        self.attachment.original_filename)
                except OSError:
                    pass
            else:
                return HttpResponseRedirect(self.revision.file.url)
        raise Http404