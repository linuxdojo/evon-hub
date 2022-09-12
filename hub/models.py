from django.db import models
from django.core.validators import RegexValidator
import re

FQDN_PATTERN = re.compile(r'(?=^.{4,253}$)(^((?!-)[a-zA-Z0-9-]{1,63}(?<!-)\.)+[a-zA-Z]{2,63}$)')
UUID_PATTERN = re.compile(r'^[a-f0-9]{8}-?[a-f0-9]{4}-?4[a-f0-9]{3}-?[89ab][a-f0-9]{3}-?[a-f0-9]{12}$')


class Server(models.Model):
    # Max fqdn length is 1004 according to RFC, but max mariadb unique varchar is 255
    ipv4_address = models.GenericIPAddressField(protocol="IPv4")
    fqdn = models.CharField(
        max_length=255,
        unique=True,
        validators=[RegexValidator(regex=FQDN_PATTERN)],
    )
    uuid = models.CharField(
        max_length=36,
        unique=True,
        validators=[RegexValidator(regex=UUID_PATTERN)],
    )

    def __str__(self):
        return self.fqdn


class ServerGroup(models.Model):
    name = models.CharField(max_length=200)
    create_date = models.DateTimeField('date created')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Server Groups"


class Policy(models.Model):
    name = models.CharField(max_length=200)
    create_date = models.DateTimeField('date created')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Policies"
