#!/bin/bash

# This file is triggered hourly via systemd timer: evonsync.timer

AUDITLOG_RETENTION_DAYS=90

# Sync all Evon-connected servers to reflect current connected state
/usr/local/bin/evon --sync-servers

#  Delete auditlogs older than AUDITLOG_RETENTION_DAYS days
/usr/local/bin/eapi auditlogflush -y -b $(date -d "-${AUDITLOG_RETENTION_DAYS} days" "+%Y-%m-%d")
