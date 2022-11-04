# Generated by Django 4.1.2 on 2022-11-04 13:14

import django.core.validators
from django.db import migrations, models
import re


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0002_alter_policy_rules_alter_policy_servergroups_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="server",
            name="server_groups",
            field=models.ManyToManyField(
                blank=True,
                help_text="A list of Server Gropup ID's in which this Server is a member. Visible only to superusers.",
                to="hub.servergroup",
                verbose_name="Server Groups",
            ),
        ),
        migrations.AlterField(
            model_name="server",
            name="uuid",
            field=models.CharField(
                editable=False,
                help_text="This value is set on line 1 of the evon.uuid file on your connected server. A unique static IPv4 address is auto-assigned to any new UUID values seen by the Hub. Visible only to superusers.",
                max_length=36,
                unique=True,
                validators=[
                    django.core.validators.RegexValidator(
                        regex=re.compile(
                            "^[a-f0-9]{8}-?[a-f0-9]{4}-?4[a-f0-9]{3}-?[89ab][a-f0-9]{3}-?[a-f0-9]{12}$"
                        )
                    )
                ],
                verbose_name="UUID",
            ),
        ),
    ]
