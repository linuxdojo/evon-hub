# Generated by Django 4.1.10 on 2023-08-20 22:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0003_remove_userprofile_id_alter_userprofile_shared_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="rule",
            name="destination_protocol",
            field=models.CharField(
                choices=[
                    ("TCP", "TCP"),
                    ("UDP", "UDP"),
                    ("ICMP", "ICMP"),
                    ("ALL", "Any Protocol"),
                ],
                help_text="The destination protocol permitted by this Rule. For unlisted protocols, select 'Any Protocol (ALL)' and filter using your Server's firewall.",
                max_length=4,
            ),
        ),
    ]
