from .handlers import GpkgManager
from celery import shared_task


@shared_task
def backup_portal_layer():
    GpkgManager.backup_portal()
