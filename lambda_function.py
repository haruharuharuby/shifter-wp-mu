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

        logger.info('invoke: ' + event["action"])
        ctr = DockerCtr(app_config, event)

        # Dispatch APIs for Backend
        """
        == WARNING: These methods are returns `raw` docker response.
                    Don't use by Frontend Services
        """
        if (event["action"] == "test"):
            return test(event)
        elif (event["action"] == "getAllServices"):
            return ctr.getServices()
        elif (event["action"] == "getTheService"):
            return ctr.getTheService(event['siteId'])

        # Dispatch APIs for Frontend Services
        """
        == INFO: These methods are returns `wrapped` docker response with Shifter context.
        """
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
            raise_message = event['action'] + ' is unregistered action type'
            raise ShifterRequestError(info=raise_message)

    except ShifterRequestError as e:
        return ResponseBuilder.buildResponse(
                status=400,
                message=e.info,
                logs_to=event
        )
    except (ShifterNoAvaliPorts, ShifterConfrictPublishPorts) as e:
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
