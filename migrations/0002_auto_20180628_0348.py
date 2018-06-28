# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gpkg_manager', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='gpkgupload',
            options={'ordering': ['-uploaded_at']},
        ),
    ]
