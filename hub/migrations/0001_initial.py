# Generated by Django 4.1 on 2022-09-12 13:10

import django.core.validators
from django.db import migrations, models
import re


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Policy",
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
                ("name", models.CharField(max_length=200)),
                ("create_date", models.DateTimeField(verbose_name="date created")),
            ],
            options={
                "verbose_name_plural": "Policies",
            },
        ),
        migrations.CreateModel(
            name="Server",
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
                ("ipv4_address", models.GenericIPAddressField(protocol="IPv4")),
                (
                    "fqdn",
                    models.CharField(
                        max_length=255,
                        unique=True,
                        validators=[
                            django.core.validators.RegexValidator(
                                regex=re.compile(
                                    "(?=^.{4,253}$)(^((?!-)[a-zA-Z0-9-]{1,63}(?<!-)\\.)+[a-zA-Z]{2,63}$)"
                                )
                            )
                        ],
                    ),
                ),
                (
                    "uuid",
                    models.CharField(
                        max_length=36,
                        unique=True,
                        validators=[
                            django.core.validators.RegexValidator(
                                regex=re.compile(
                                    "^[a-f0-9]{8}-?[a-f0-9]{4}-?4[a-f0-9]{3}-?[89ab][a-f0-9]{3}-?[a-f0-9]{12}$"
                                )
                            )
                        ],
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ServerGroup",
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
                ("name", models.CharField(max_length=200)),
                ("create_date", models.DateTimeField(verbose_name="date created")),
            ],
            options={
                "verbose_name_plural": "Server Groups",
            },
        ),
    ]
