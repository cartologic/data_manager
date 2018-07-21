# from celery import shared_task
from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage
from django.core.urlresolvers import reverse

from cartoview.log_handler import get_logger

from .esri_handler import EsriHandler
from .handlers import GpkgManager
from .helpers import urljoin

logger = get_logger(__name__)


@shared_task
def backup_portal_layer():
    path = GpkgManager.backup_portal()
    return path


@shared_task
def esri_from_url(url,
                  useremail=None,
                  overwrite=False,
                  temporary=False,
                  launder=False,
                  name=None):
    eh = EsriHandler(url)
    geonode_layer = eh.publish()
    layer_url = None
    message = None
    if geonode_layer:
        layer_url = reverse(
            'layer_detail', kwargs={"layername": geonode_layer.alternate})
        message = "Your Layer Successfully Imported {}".format(
            urljoin(settings.SITEURL, layer_url))
    else:
        message = "Failed To Dump Your Layer"
    if useremail:
        msg = EmailMessage(
            'Esri Layer Status',
            message,
            to=(useremail, ),
            from_email=settings.DEFAULT_FROM_EMAIL)
        msg.send()
    return layer_url