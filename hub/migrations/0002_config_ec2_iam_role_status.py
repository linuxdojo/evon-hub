# Generated by Django 4.1.2 on 2022-11-11 06:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="config",
            name="ec2_iam_role_status",
            field=models.BooleanField(
                default=False,
                editable=False,
                help_text="Health status of your EC2 IAM Role. Must be True, else Hub will not function. SSH to this EC2 instance and run command 'evon --iam-validate' for more information.",
            ),
        ),
    ]
