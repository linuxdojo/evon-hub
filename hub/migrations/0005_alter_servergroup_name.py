# Generated by Django 4.1 on 2022-09-28 23:22

from django.db import migrations, models
import hub.models


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0004_alter_server_server_groups"),
    ]

    operations = [
        migrations.AlterField(
            model_name="servergroup",
            name="name",
            field=models.CharField(
                max_length=200, validators=[hub.models.ServerGroupNameValidator]
            ),
        ),
    ]
