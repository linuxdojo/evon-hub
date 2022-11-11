import os
import time
import traceback

import boto3
import botocore
import django
import requests
os.environ['DJANGO_SETTINGS_MODULE'] = 'eapi.settings'  # noqa
django.setup()  # noqa

from eapi.settings import EVON_HUB_CONFIG  # noqa
from evon import evon_api  # noqa
from evon.cli import EVON_API_URL, EVON_API_KEY  # noqa
from evon.log import get_evon_logger  # noqa
from hub.models import Config  # noqa


logger = get_evon_logger()


def get_region():
    """
    Returns the region name in which the host EC2 instance is running
    """
    response = requests.get("http://169.254.169.254/latest/dynamic/instance-identity/document")
    region_name = response.json()["region"]
    return region_name


def save_ec2_role_status(current_status):
    """
    Updates Config.ec2_iam_role_status with input `status` (bool)
    """
    c = Config.get_solo()
    saved_status = c.ec2_iam_role_status
    if current_status != current_status:
        logger.info(f"detected ec2 role status change from '{saved_status}' to '{current_status}', persisting...")
        c.ec2_iam_role_status = current_status
        c.save()


def validate_ec2_role():
    """
    Checks if an IAM Role with Policy allowing the 'aws-marketplace:MeterUsage' action is attached to this EC2 instance.
    Returns json: {"status": bool, "message": str} where:
    "status" == True iff the iam role is setup correctly
    "message" string contains human readable information about the current status
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
                message = "The IAM Role attached to this EC2 instance is configured correctly."
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
    # update Config
    save_ec2_role_status(status)
    return {"status": status, "message": message}


def register_meters():
    response = evon_api.get_meters(EVON_API_URL, EVON_API_KEY)
    return response
