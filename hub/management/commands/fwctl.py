from django.core.management.base import BaseCommand, CommandError

from hub import firewall


class Command(BaseCommand):
    help = "Control iptables chains and rules relating to Evon Rules and Policies"

    def add_arguments(self, parser):
        parser.add_argument(
            '--init',
            action='store_true',
            help='Initialise iptables and insert all current Hub Rules and Policies',
        )
        parser.add_argument(
            '--init-empty',
            action='store_true',
            help='Initialise iptables only without applying Hub Rules and Policies',
        )
        parser.add_argument(
            '--delete',
            action='store_true',
            help='flush all Evon Rule and Policy related iptables rules and chains, reverting iptables to an initialised state',
        )
        parser.add_argument(
            '--delete-all',
            action='store_true',
            help='Delete all Evon related firewall rules rather than just flush and re-initialise',
        )

    def handle(self, *args, **options):
        if not options:
            self.stdout.write("Please specify an option")
            return

        if options['init']:
            firewall.init()
            self.stdout.write("All Evon iptables rules and chains initialised")

        if options['init_empty']:
            firewall.init(full=False)
            self.stdout.write("Initialised core Evon iptables rules/chains only.")

        if options['delete']:
            firewall.delete_all()
            self.stdout.write("Flushed Evon iptables rules and chains")

        if options['delete_all']:
            firewall.delete_all(flush_only=False)
            self.stdout.write("Deleted all Evon iptables rules and chains")
