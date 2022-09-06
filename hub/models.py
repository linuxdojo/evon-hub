from django.db import models


class User(models.Model):
    user_name = models.CharField(max_length=200)
    create_date = models.DateTimeField('date created')

    def __str__(self):
        return self.user_name


class Group(models.Model):
    group_name = models.CharField(max_length=200)
    create_date = models.DateTimeField('date created')

    def __str__(self):
        return self.group_name


class Server(models.Model):
    fqdn = models.CharField(max_length=1004)
    ipv4_address = models.CharField(max_length=15)

    def __str__(self):
        return self.fqdn


class Servergroup(models.Model):
    servergroup_name = models.CharField(max_length=200)
    create_date = models.DateTimeField('date created')

    def __str__(self):
        return self.servergroup_name


class Policy(models.Model):
    policy_name = models.CharField(max_length=200)
    create_date = models.DateTimeField('date created')

    def __str__(self):
        return self.policy_name
