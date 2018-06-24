from django import forms
from .models import GpkgUpload


class GpkgUploadForm(forms.ModelForm):
    class Meta:
        model = GpkgUpload
        fields = ['package', ]
