# from celery import shared_task
from geonode.celery_app import app
from django.conf import settings
from django.core.mail import EmailMessage
from django.core.urlresolvers import reverse

from cartoview.log_handler import get_logger

from .esri_handler import EsriHandler
from .handlers import GpkgManager
from .helpers import urljoin
logger = get_logger(__name__)


@app.task(bind=True)
def backup_portal_layer(self):
    path = GpkgManager.backup_portal()
    return path


@app.task(bind=True)
def esri_from_url(self,
                  url,
                  useremail=None,
                  overwrite=False,
                  temporary=False,
                  launder=False,
                  name=None):

    eh = EsriHandler(url)
    geonode_layer = eh.publish()
    layer_url = None
    message = None
    mail_on = settings.EMAIL_ENABLE if hasattr(
        settings, 'EMAIL_ENABLE') else False
    if geonode_layer:
        site_url = settings.SITEURL
        layer_url = reverse(
            'layer_detail', kwargs={"layername": geonode_layer.alternate})
        url = urljoin(site_url, layer_url.lstrip('/'))
        message = "Your Layer Successfully Imported {}".format(url)
    else:
        message = "Failed To Dump Your Layer please Contact Portal Admin"
    if useremail and mail_on:
        msg = EmailMessage(
            'Esri Layer Status',
            message,
            to=(useremail, ),
            from_email=settings.DEFAULT_FROM_EMAIL)
        msg.send()
    return layer_url
