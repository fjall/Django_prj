# Generated by Django 2.2.19 on 2023-01-14 16:01

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0002_auto_20230114_1805'),
    ]

    operations = [
        migrations.RenameField(
            model_name='group',
            old_name='descriptiom',
            new_name='description',
        ),
    ]