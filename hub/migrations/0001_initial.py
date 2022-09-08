# Generated by Django 4.1 on 2022-09-08 01:59

from django.db import migrations, models


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
                ("fqdn", models.CharField(max_length=1004)),
                ("ipv4_address", models.CharField(max_length=15)),
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
        ),
    ]
