from django.contrib import admin
from guardian.admin import GuardedModelAdmin
from .models import GpkgUpload


@admin.register(GpkgUpload)
class GpkgUploadAdmin(GuardedModelAdmin):
    list_display = ('pk', 'package', 'user')
