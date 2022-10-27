import datetime
import pytz

from crontab import CronTab

from hub.models import on_al2

def apply(config):
    """
    takes in a hub.Config instance and saves out the specified update schedule crontab
    """
    if on_al2():
        # delete the crontab, and replace if needed
        cron = CronTab(user=True)
        cron.remove_all()
        if config.auto_update:
            tz = pytz.timezone(config.timezone)
            utc_start = datetime.datetime.now(tz).replace(
                hour=config.auto_update_time.hour,
                minute=config.auto_update_time.minute,
                second=0).astimezone()
            start_hour = utc_start.hour
            start_minute = utc_start.minute
            job = cron.new(command='sudo /opt/evon-hub/.env/bin/evon --update')
            job.minute.on(start_minute)
            job.hour.on(start_hour)
        cron.write()
