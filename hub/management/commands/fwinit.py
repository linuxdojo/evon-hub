from django.core.management.base import BaseCommand, CommandError

from hub import firewall


class Command(BaseCommand):
    help = "Initialise iptables with core Evon rules and chains"

    def add_arguments(self, parser):
        parser.add_argument(
            '--full',
            action='store_true',
            help='Insert all current Rule and Policy iptables rules and chains also',
        )

    def handle(self, *args, **options):
        if options['full']:
            firewall.init()
            self.stdout.write("All Evon iptables rules and chains initialised")
        else:
            firewall.init(full=False)
            self.stdout.write("Core Evon iptables rules and chains initialised")
