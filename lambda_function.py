from __future__ import print_function, unicode_literals

import base64
import json
import logging
import os
import sys
import random
import urllib2
import uuid
import boto3
import botocore

here = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(here, "./vendored"))


import yaml
from mylibs.DockerCtr import *
from mylibs.ResponseBuilder import *
from mylibs.ShifterExceptions import *

logger = logging.getLogger()
logger.setLevel(logging.INFO)
# logger.setLevel(logging.DEBUG)


def lambda_handler(event, context):
    """
    returns JSON String.
      - Hash of status(int), message(str), and informations for other Apps.
    """

    AVAIL_ACTIONS = [
        'test',
        'getTheService',
        'digSiteDirs',
        'bulkDelete',
        'createNewService',
        'syncEfsToS3',
        'deletePublicContents',
        'deleteTheService',
        'deleteServiceByServiceId',
        'deployToNetlify'
    ]

    # Load Configrations
    config_base = yaml.load(open('./config/appconfig.yml', 'r'))
    if 'SHIFTER_ENV' in os.environ.keys():
        app_config = config_base[os.environ['SHIFTER_ENV']]
    else:
        app_config = config_base['dev']

    try:
        if 'action' not in event:
            raise ShifterRequestError(info="params 'action' not found.")

        if event['action'] not in AVAIL_ACTIONS:
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
            result = ctr.createNewService()
        elif (event["action"] == 'syncEfsToS3'):
            result = ctr.createNewService()
        elif (event["action"] == 'deployToNetlify'):
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
