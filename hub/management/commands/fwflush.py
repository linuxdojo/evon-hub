from django.core.management.base import BaseCommand, CommandError

from hub import firewall


class Command(BaseCommand):
    help = "flush all Evon Rule and Policy related IPTables rules and chains, reverting iptables to an initialised state"

    def add_arguments(self, parser):
        parser.add_argument(
            '--delete',
            action='store_true',
            help='Delete all Evon related firewall rules rather than just flush and re-initialise',
        )

    def handle(self, *args, **options):
        if options['delete']:
            firewall.delete_all(flush_only=False)
            self.stdout.write("Deleted all Evon iptables rules and chains")
        else:
            firewall.delete_all()
            self.stdout.write("Flushed Evon iptables rules and chains")

