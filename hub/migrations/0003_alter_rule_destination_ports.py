# Generated by Django 4.1 on 2022-10-13 23:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0002_alter_rule_destination_ports"),
    ]

    operations = [
        migrations.AlterField(
            model_name="rule",
            name="destination_ports",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Single or comma separated port numbers with dashed ranges are supported, eg: 80,443,7000-8000",
                max_length=256,
            ),
        ),
    ]
