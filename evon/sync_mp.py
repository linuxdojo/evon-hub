import os
import datetime
import time
import traceback

import boto3
import botocore
import django
import requests
os.environ['DJANGO_SETTINGS_MODULE'] = 'eapi.settings'  # noqa
django.setup()  # noqa
from django.contrib.auth.models import User  # noqa


from eapi.settings import EVON_HUB_CONFIG, EVON_VARS  # noqa
from evon import evon_api  # noqa
from evon.cli import EVON_API_URL, EVON_API_KEY  # noqa
from evon.log import get_evon_logger  # noqa
from hub.models import Config, Server  # noqa


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
    if current_status != saved_status:
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
        except client.exceptions.DuplicateRequestException:
            # This is fine, it indicates a working IAM role
            status = True
            message = "The IAM Role attached to this EC2 instance is configured correctly."
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
    if not status:
        raise Exception(message)
    return {"status": status, "message": message}


def get_aggregate_meters():
    """
    Returns aggregate ServerConnections and Users for the account in which the calling EC2 instance resides.
    """
    response = evon_api.get_meters(EVON_API_URL, EVON_API_KEY)
    return response


def register_meters():
    """
    Registers meter usage unit dimensions with AWS.  Blocks until meters are
    successfully registered (we retry on failure), or at 5 minutes before the
    hour, or an Exception is raised while computing input params, whichever
    occurs first.
    Returns json if successful else rasises
    """
    # compute paramters
    region_name = get_region()
    marketplaceClient = boto3.client('meteringmarketplace', region_name=region_name)
    evon_account_domain = EVON_VARS["account_domain"]
    aws_account_id = EVON_VARS["aws_account_id"]
    aws_ec2_id = EVON_VARS["ec2_id"]
    product_code = EVON_HUB_CONFIG["MP_PRODUCT_CODE"]
    server_dimension_name = EVON_HUB_CONFIG["MP_DIMENSIONS"]["server"]
    user_dimension_name = EVON_HUB_CONFIG["MP_DIMENSIONS"]["user"]
    server_count = Server.objects.count()
    user_count = User.objects.count() - 2  # subtract the two default users, "admin" and "deployer"
    meter_timestamp = int(datetime.datetime.utcnow().replace(minute=0, second=0, microsecond=0).timestamp())
    server_usage_record = [
        {
            "AllocatedUsageQuantity": server_count,
            "Tags": [
                {"Key": "evon_account_domain", "Value": evon_account_domain},
                {"Key": "aws_account_id", "Value": aws_account_id},
                {"Key": "aws_ec2_id", "Value": aws_ec2_id},
            ]
        },
    ]
    user_usage_record = [
        {
            "AllocatedUsageQuantity": user_count,
            "Tags": [
                {"Key": "evon_account_domain", "Value": evon_account_domain},
                {"Key": "aws_account_id", "Value": aws_account_id},
                {"Key": "aws_ec2_id", "Value": aws_ec2_id},
            ]
        },
    ]
    # register usages
    try:
        # register server usage
        response_server = marketplaceClient.meter_usage(
            ProductCode=product_code,
            Timestamp=meter_timestamp,
            UsageDimension=server_dimension_name,
            UsageQuantity=server_count,
            DryRun=False,
            UsageAllocations=server_usage_record
        )
        logger.info(f"Server metering usage response: {response_server}")
        # register user usage
        response_user = marketplaceClient.meter_usage(
            ProductCode=product_code,
            Timestamp=meter_timestamp,
            UsageDimension=user_dimension_name,
            UsageQuantity=user_count,
            DryRun=False,
            UsageAllocations=user_usage_record
        )
        logger.info(f"User metering usage response: {response_user}")
    except Exception as e:
        logger.error(f"Got exception while registering meters with AWS Metering Service: {traceback.format_exc()}")
        raise e
    return {
        "message": "success",
        "meter_timestamp": meter_timestamp,
    }
