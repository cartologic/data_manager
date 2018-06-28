from django.contrib import admin
from .models import GpkgUpload


@admin.register(GpkgUpload)
class GpkgUploadAdmin(admin.ModelAdmin):
    list_display = ('pk', 'package', 'user')
