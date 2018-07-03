# -*- coding: utf-8 -*-
from django.db import models
from geonode.people.models import Profile
from datetime import datetime
import os
from .handlers import GpkgManager, StyleManager
from django.dispatch import receiver
from guardian.shortcuts import assign_perm
from guardian.shortcuts import get_anonymous_user
GPKG_PERMISSIONS = (
    ('view_package', 'View Geopackge'),
    ('download_package', 'Download Geopackge'),
    ('delete_package', 'Delete Geopackge'),
    ('publish_from_package', 'Publish Layers from Geopackge'),
)


def validate_file_extension(value):
    import os
    from django.core.exceptions import ValidationError
    ext = os.path.splitext(value.name)[1]
    valid_extensions = ['.gpkg']
    if not ext.lower() in valid_extensions:
        raise ValidationError(u'Unsupported file extension.only {} allowed'
                              .format(','.join(valid_extensions)))


def package_path(instance, filename):
    today = datetime.now()
    date_as_path = today.strftime("%Y/%m/%d")
    return '/'.join(['gpkg', instance.user.username, date_as_path, filename])


class GpkgUpload(models.Model):
    user = models.ForeignKey(Profile, blank=True, null=True)
    package = models.FileField(
        upload_to=package_path, validators=[validate_file_extension])
    uploaded_at = models.DateTimeField(auto_now=False, auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, auto_now_add=False)

    def __str__(self):
        return self.package_name

    def __unicode__(self):
        return self.package_name

    class Meta:
        ordering = ['-uploaded_at']
        permissions = GPKG_PERMISSIONS

    @property
    def package_name(self):
        return os.path.basename(self.package.name)

    @property
    def gpkg_manager(self):
        return GpkgManager(self.package.path)

    @property
    def style_manager(self):
        return StyleManager(self.package.path)


@receiver(models.signals.post_delete, sender=GpkgUpload)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    if instance.package:
        if os.path.isfile(instance.package.path):
            os.remove(instance.package.path)


@receiver(models.signals.pre_save, sender=GpkgUpload)
def auto_delete_file_on_change(sender, instance, **kwargs):
    if not instance.pk:
        return False

    try:
        old_file = GpkgUpload.objects.get(pk=instance.pk).file
    except GpkgUpload.DoesNotExist:
        return False

    new_file = instance.package
    if not old_file == new_file:
        if os.path.isfile(old_file.path):
            os.remove(old_file.path)


@receiver(models.signals.post_save, sender=GpkgUpload)
def init_permissions(sender, instance, created, **kwargs):
    if created:
        # assign permissions for the owner of the package
        if instance.user and instance.user != get_anonymous_user():
            for p in GPKG_PERMISSIONS:
                assign_perm(p[0], instance.user, instance)
