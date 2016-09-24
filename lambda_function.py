from __future__ import print_function
from __future__ import unicode_literals
import urllib2
import json
import base64
import random
import uuid
import logging
import boto3
import botocore
import os
import lamvery
import yaml
from mylibs.ShifterExceptions import *
from mylibs.ResponseBuilder import *
from mylibs.DockerCtr import *

logger = logging.getLogger()
logger.setLevel(logging.INFO)
# logger.setLevel(logging.DEBUG)

print('Loading function')


def lambda_handler(event, context):
    """
    returns JSON String.
      - Hash of status(int), message(str), and informations for other Apps.
    """

    AVALI_ACTIONS = [
        'test',
        'getTheService',
        'digSiteDirs',
        'bulkDelete',
        'createNewService',
        'syncEfsToS3',
        'deletePublicContents',
        'deleteTheService',
        'deleteServiceByServiceId'
    ]

    # Load Configrations
    lamvery.env.load()
    config_base = yaml.load(open('./config/appconfig.yml', 'r'))
    if 'SHIFTER_ENV' in os.environ.keys():
        app_config = config_base[os.environ['SHIFTER_ENV']]
    else:
        app_config = config_base['development']

    try:
        if 'action' not in event:
            raise ShifterRequestError(info="params 'action' not found.")

        if event['action'] not in AVALI_ACTIONS:
            raise_message = event['action'] + ' is unregistered action type'
            raise ShifterRequestError(info=raise_message)

        logger.info('invoke: ' + event["action"])
        ctr = DockerCtr(app_config, event)

        # これ外部公開しなくていいので閉じよう
        # if (event["action"] == "getAllServices"):
        #     return ctr.getServices()

        # Dispatch APIs for Clients
        """
        == INFO: These methods are returns `wrapped` docker response with Shifter context.
        """
        if (event["action"] == "test"):
            return test(event)
        elif (event["action"] == "getTheService"):
            return ctr.getTheService(event['siteId'])
        elif (event["action"] == 'digSiteDirs'):
            if 'fsId' not in event:
                raise ShifterRequestError(info="params 'fsId' not found.")
            return ctr.createNewService()
        elif (event["action"] == 'bulkDelete'):
            if 'serviceIds' not in event:
                raise ShifterRequestError(info="params 'serviceIds' not found.")
            if not isinstance(event['serviceIds'], list):
                raise ShifterRequestError(info="params 'serviceIds' must be list.")
            return ctr.bulkDelete()

        # ここからsiteId必須
        if 'siteId' not in event:
            raise ShifterRequestError(info="params 'siteId' not found.")

        if (event["action"] == "createNewService"):
            if 'fsId' not in event:
                raise ShifterRequestError(info="params 'fsId' not found.")
            result = ctr.createNewService()
        elif (event["action"] == 'syncEfsToS3'):
            if 'fsId' not in event:
                raise ShifterRequestError(info="params 'fsId' not found.")
            result = ctr.createNewService()
        elif (event["action"] == 'deletePublicContents'):
            result = ctr.createNewService()
        elif (event["action"] == "deleteTheService"):
            result = ctr.deleteTheService(event['siteId'])
        elif (event["action"] == 'deleteServiceByServiceId'):
            if 'serviceId' not in event:
                raise ShifterRequestError(info="params 'serviceId' not found.")
            result = ctr.deleteServiceByServiceId(event)
        else:
            # ここには来ないはずだけど一応。
            raise_message = event['action'] + ' is unregistered action type'
            raise ShifterRequestError(info=raise_message)

    except ShifterRequestError as e:
        return ResponseBuilder.buildResponse(
                status=400,
                message=e.info,
                logs_to=event
        )
    except (ShifterNoAvaliPorts,
            ShifterConfrictPublishPorts,
            ShifterConfrictNewService) as e:
        return ResponseBuilder.buildResponse(
                status=e.exit_code,
                message=e.info,
                siteId=event['siteId'],
                logs_to=event
        )
    except Exception as e:
        logger.exception("Error occurred during calls Docker API: " + str(type(e)))
        return ResponseBuilder.buildResponse(
                status=500,
                message='Error occurred during calls Backend Service.',
                logs_to=event
        )

    return result


def test(event):
    return 'this is test'
