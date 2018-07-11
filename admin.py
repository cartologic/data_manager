from django.contrib import admin
from guardian.admin import GuardedModelAdmin
from .models import GpkgUpload, ManagerDownload


@admin.register(GpkgUpload)
class GpkgUploadAdmin(GuardedModelAdmin):
    list_display = ('pk', 'package', 'user')


@admin.register(ManagerDownload)
class ManagerDownloadAdmin(GuardedModelAdmin):
    list_display = ('pk', 'file_path', 'user')
