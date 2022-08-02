
#################################
# EVON Logger
#################################


import logging
import logging.handlers
import sys

import click


class click_stderr():

    def write(data):
        parts = data.split()
        level = None
        if len(parts) > 3:
            level = parts[3][:-1]
        match level:
            case "DEBUG":
                color = "blue"
            case "INFO":
                color = "green"
            case "WARNING":
                color = "yellow"
            case "ERROR":
                color = "bright_red"
            case "CRITICAL":
                color = "red"
            case other:  # noqa
                color = "reset"
        click.echo(click.style(data.strip(), fg=color), err=True)
        click_stderr.flush()

    def flush():
        sys.stderr.flush()


class MutuallyExclusiveOption(click.Option):
    """
    Mutex group for Click. Example usage:
        @click.option("--silent", cls=log.MutuallyExclusiveOption, mutually_exclusive=["verbose"], is_flag=True, help="be silent")
        @click.option("--verbose", cls=log.MutuallyExclusiveOption, mutually_exclusive=["silent"], is_flag=True, help="be noisy")
    """

    def __init__(self, *args, **kwargs):
        self.mutually_exclusive = set(kwargs.pop('mutually_exclusive', []))
        help = kwargs.get('help', '')
        if self.mutually_exclusive:
            ex_str = ', '.join(self.mutually_exclusive)
            kwargs['help'] = help + (
                ' NOTE: This argument is mutually exclusive with '
                ' arguments: [' + ex_str + '].'
            )
        super(MutuallyExclusiveOption, self).__init__(*args, **kwargs)

    def handle_parse_result(self, ctx, opts, args):
        if self.mutually_exclusive.intersection(opts) and self.name in opts:
            raise click.UsageError(
                "Illegal usage: `{}` is mutually exclusive with "
                "arguments `{}`.".format(
                    self.name,
                    ', '.join(self.mutually_exclusive)
                )
            )

        return super(MutuallyExclusiveOption, self).handle_parse_result(
            ctx,
            opts,
            args
        )


def get_evon_logger():
    # setup logging
    logger = logging.getLogger()
    logger.handlers = []
    logger.setLevel(logging.INFO)
    syslog_handler = logging.handlers.SysLogHandler(address='/dev/log')
    stderr_handler = logging.StreamHandler(click_stderr)
    syslog_fmt = logging.Formatter(fmt='evon[%(process)d]: %(levelname)s: %(message)s')
    stderr_fmt = logging.Formatter(fmt='%(asctime)s - %(levelname)s: %(message)s')
    syslog_handler.setFormatter(syslog_fmt)
    stderr_handler.setFormatter(stderr_fmt)
    logger.addHandler(syslog_handler)
    logger.addHandler(stderr_handler)
    return logger
