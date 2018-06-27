# -*- coding: utf-8 -*-
from django.db import models
from geonode.people.models import Profile
from datetime import datetime
import os
from .handlers import GpkgManager, StyleManager


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
    package = models.FileField(upload_to=package_path, validators=[
                               validate_file_extension])
    uploaded_at = models.DateTimeField(auto_now=False, auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, auto_now_add=False)

    def __str__(self):
        return self.package_name

    def __unicode__(self):
        return self.package_name

    @property
    def package_name(self):
        return os.path.basename(self.package.name)

    @property
    def gpkg_manager(self):
        return GpkgManager(self.package.path)

    @property
    def style_manager(self):
        return StyleManager(self.package.path)
