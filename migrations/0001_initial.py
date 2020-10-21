# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import data_manager.models
from django.conf import settings
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='GpkgUpload',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('package', models.FileField(upload_to=data_manager.models.package_path, validators=[data_manager.models.validate_file_extension])),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True, on_delete=django.db.models.deletion.SET_NULL)),
            ],
            options={
                'ordering': ['-uploaded_at'],
                'permissions': (('view_package', 'View Geopackge'), ('download_package', 'Download Geopackge'), ('delete_package', 'Delete Geopackge'), ('publish_from_package', 'Publish Layers from Geopackge')),
            },
        ),
    ]
