from django.core.management.base import BaseCommand, CommandError

from evon import sync_servers


class Command(BaseCommand):
    help = "Sync all Server objects to reflect current OpenVPN connected state"

    def handle(self, *args, **options):
        sync_servers.do_sync()
        self.stdout.write("Server connected state now synchronised in DB")
