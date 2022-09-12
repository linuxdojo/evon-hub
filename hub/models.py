from django.db import models


class Server(models.Model):
    fqdn = models.CharField(max_length=255, unique=True)  # Max fqdn len is 1004 according to RFC, but max mariadb unique varchar is 255
    ipv4_address = models.CharField(max_length=15, unique=True)
    uuid = models.CharField(max_length=36, unique=True)

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
