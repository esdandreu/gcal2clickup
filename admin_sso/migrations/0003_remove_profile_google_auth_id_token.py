# Generated by Django 3.2.5 on 2021-07-20 14:17

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('admin_sso', '0002_auto_20210720_1417'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='profile',
            name='google_auth_id_token',
        ),
    ]
