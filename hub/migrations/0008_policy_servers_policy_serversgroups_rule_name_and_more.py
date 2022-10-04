# Generated by Django 4.1 on 2022-10-04 12:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0007_alter_policy_description"),
    ]

    operations = [
        migrations.AddField(
            model_name="policy",
            name="servers",
            field=models.ManyToManyField(
                blank=True, to="hub.server", verbose_name="Servers"
            ),
        ),
        migrations.AddField(
            model_name="policy",
            name="serversgroups",
            field=models.ManyToManyField(
                blank=True, to="hub.servergroup", verbose_name="Server Groups"
            ),
        ),
        migrations.AddField(
            model_name="rule",
            name="name",
            field=models.CharField(default="", max_length=200),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="rule",
            name="destination_protocol",
            field=models.CharField(
                choices=[("I", "ICMP"), ("T", "TCP"), ("U", "UDP"), ("A", "ANY")],
                max_length=1,
            ),
        ),
    ]
