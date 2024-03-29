# Generated by Django 4.1.10 on 2023-08-16 05:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="shared",
            field=models.BooleanField(
                default=False, help_text="Allow other systems to connect to your device"
            ),
        ),
    ]
