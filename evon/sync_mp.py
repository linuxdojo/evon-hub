import os
import time
import traceback

import boto3
import botocore
import django
import requests
os.environ['DJANGO_SETTINGS_MODULE'] = 'eapi.settings'  # noqa
django.setup()  # noqa
from django.contrib.auth.models import User  # noqa

from eapi.settings import EVON_HUB_CONFIG  # noqa
from hub.models import Server  # noqa
from evon import evon_api  # noqa
from evon.cli import EVON_API_URL, EVON_API_KEY, inject_pub_ipv4  # noqa
from evon.log import get_evon_logger  # noqa


logger = get_evon_logger()


def get_region():
    """
    Returns the region name in which the host EC2 instance is running
    """
    response = requests.get("http://169.254.169.254/latest/dynamic/instance-identity/document")
    region_name = response.json()["region"]
    return region_name


def validate_ec2_role():
    """
    Checks if an IAM Role with Policy allowing the 'aws-marketplace:MeterUsage' action is attached to this EC2 instance.
    Returns json: {"status": bool, "message": str} where:
    "status" == True iff the iam role is setup correctly
    "message" string contains the reason the role is not setup correctly, or  "success" if "status" == True
    """
    # set default status
    status = False
    # get region name
    region_name = get_region()
    # get role attached to thie EC2 if any
    response = requests.get("http://169.254.169.254/latest/meta-data/iam/security-credentials")
    if not 400 > response.status_code >= 200:
        message = "No IAM Role is attached to this EC2 instance. Please attach a Role with a Policy allowing the 'aws-marketplace:MeterUsage' action."
    else:
        role_name = response.text
        client = boto3.client('meteringmarketplace', region_name=region_name)
        try:
            response = client.meter_usage(
                ProductCode=EVON_HUB_CONFIG["MP_PRODUCT_CODE"],
                Timestamp=int(time.time()),
                UsageDimension=EVON_HUB_CONFIG["MP_DIMENSIONS"]["server"],
                DryRun=True
            )
            if response['MeteringRecordId'] == 'DryRunOperation':
                status = True
                message = "success"
            else:
                logger.error(f"Unexpected response from meter_usage(): {response}")
                message = "Unexpected response from AWS meter_usage API. Please check syslog for more info."
        except botocore.exceptions.NoCredentialsError:
            message = "No IAM Role is attached to this EC2 instance. Please attach a Role with a Policy allowing the 'aws-marketplace:MeterUsage' action."
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "AccessDeniedException":
                message = f"The Role '{role_name}' does not have permission to perform the 'aws-marketplace:MeterUsage' action. Please update the Role's Policy to allow this action."
            else:
                logger.error(f"Unexpected ClientError Exception from meter_usage(): {traceback.format_exc()}")
                message = "Unexpected ClientError Exception when calling AWS meter_usage API. Please check syslog for more info."
        except Exception:
            logger.error(f"Unexpected Exception from meter_usage(): {traceback.format_exc()}")
            message = "Unexpected Exception when calling AWS meter_usage API. Please check syslog for more info."
    return {"status": status, "message": message}
