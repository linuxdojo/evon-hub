# Generated by Django 4.1 on 2022-10-11 04:52

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import hub.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("hub", "0013_alter_config_timezone"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "ipv4_address",
                    models.GenericIPAddressField(
                        editable=False,
                        help_text="This value is auto-assigned and static for this User",
                        protocol="IPv4",
                        validators=[hub.models.EvonIPV4UserValidator],
                        verbose_name="IPv4 Address",
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]