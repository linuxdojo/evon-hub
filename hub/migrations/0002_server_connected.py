# Generated by Django 4.1 on 2022-09-17 01:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="server",
            name="connected",
            field=models.BooleanField(default=False),
        ),
    ]
