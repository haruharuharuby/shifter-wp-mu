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
from mylibs.DockerCtr import *
from mylibs.DynamoDB import *
from mylibs.S3 import *

logger = logging.getLogger()
logger.setLevel(logging.INFO)
# logger.setLevel(logging.DEBUG)

print('Loading function')


def lambda_handler(event, context):
    if 'action' not in event:
        return createBadRequestMessage(event, "params 'action' not found.")

    ctr = DockerCtr()
    if (event["action"] == "test"):
        return test(event)

    if (event["action"] == "getAllServices"):
        result = ctr.getServices()
    else:
        if 'siteId' not in event:
            return createBadRequestMessage(event, "params 'siteId' not found.")
        if (event["action"] == "getTheService"):
            result = ctr.getTheService(event['siteId'])
        elif (event["action"] == "deleteTheService"):
            result = ctr.deleteTheService(event['siteId'])
        elif (event["action"] == "createNewService"):
            if 'fsId' not in event:
                return createBadRequestMessage(event, "params 'fsId' not found.")
            result = ctr.createNewService(event)
        elif (event["action"] == 'syncEfsToS3'):
            if 'fsId' not in event:
                return createBadRequestMessage(event, "params 'fsId' not found.")
            result = ctr.createNewService(event)
        elif (event["action"] == 'deleteServiceByServiceId'):
            if 'serviceId' not in event:
                return createBadRequestMessage(event, "params 'serviceId' not found.")
            result = ctr.deleteServiceByServiceId(event)
        else:
            return createBadRequestMessage(event, event["action"] + 'is unregistered action type')
    return result


def test(event):
    return 'this is test'


def createBadRequestMessage(event, error_text):
    message = {
        "status": 400,
        "message": error_text,
        "request": event
    }
    logger.warning(message)
    return message
