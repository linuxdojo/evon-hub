from django.contrib import messages
from django.utils.safestring import mark_safe

from hub.models import Config


class HubMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response
        self.iam_warning_message = 'The EC2 IAM Role for this Hub is not properly configured, functionality will be limited. Please check <a href="/hub/config/1/change/">your Config</a>'

    def __call__(self, request):
        # show warning messsge to superusers if IAM role is improperly configured.
        if request.user.is_superuser:
            show = True
            storage = messages.get_messages(request)
            for message in storage:
                if message.message == self.iam_warning_message:
                    show = False
            storage.used = False
            # Code that is executed in each request before the view is called
            config = Config.get_solo()
            if not config.ec2_iam_role_status and show:
                messages.add_message(
                    request,
                    messages.WARNING,
                    mark_safe(self.iam_warning_message),
                )
            elif config.ec2_iam_role_status and not show:
                # IAM Role looks good, send green message
                messages.add_message(
                    request,
                    messages.SUCCESS,
                    "The EC2 IAM Role for this Hub is now configured correctly!",
                )
        response = self.get_response(request)
        # Code that is executed in each request after the view is called
        return response
