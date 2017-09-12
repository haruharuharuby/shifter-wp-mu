# -*- coding: utf-8 -*-

import base64
import json
import logging
import os
import sys
import random
import uuid
import boto3
import botocore

here = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(here, "./vendored"))
if os.environ.get('LAMBDA_LOCAL'):
    sys.path.append(os.path.join(here, "./localvendored"))


import yaml
from mylibs.DockerCtr import *
from mylibs.ResponseBuilder import *
from mylibs.ShifterExceptions import *

import rollbar

rollbar.init(os.getenv("ROLLBAR_TOKEN"), os.getenv("SHIFTER_ENV", "development"))
logger = logging.getLogger()
logger.setLevel(logging.INFO)
# logger.setLevel(logging.DEBUG)

# 'action_name': [required parameters except of 'action']
AVAIL_ACTIONS = {
    'test': [],
    'getTheService': ['siteId'],
    'digSiteDirs': ['fsId'],
    'bulkDelete': ['serviceIds'],
    'createNewService': ['siteId'],
    'syncEfsToS3': ['siteId'],
    'createArtifact': ['siteId', 'artifactId'],
    'restoreArtifact': ['siteId', 'artifactId'],
    'deletePublicContents': ['siteId'],
    'deleteTheService': ['siteId'],
    'deleteServiceByServiceId': ['siteId', 'serviceId'],
    'deployToNetlify': ['siteId', 'nf_siteID', 'nf_token']
}


def lambda_handler(event, context):
    """
    returns JSON String.
      - Hash of status(int), message(str), and informations for other Apps.
    """

    # Load Configrations
    config_base = yaml.load(open('./config/appconfig.yml', 'r'))
    if 'SHIFTER_ENV' in os.environ.keys():
        app_config = config_base[os.environ['SHIFTER_ENV']]
    else:
        app_config = config_base['development']

    try:

        validate_arguments(event)

        logger.info('invoke: ' + event["action"])
        ctr = DockerCtr(app_config, event)

        # これ外部公開しなくていいので閉じよう
        # if (event["action"] == "getAllServices"):
        #     return ctr.getServices()

        # Dispatch APIs for Clients
        """
        == INFO: These methods are returns `wrapped` docker response with Shifter context.
        == INFO: args should be lambda function because it needs to be evaluated lazily.
        """
        docker_actions = {
            'test': {'invoke': do_test, 'args': lambda: event},
            'getTheService': {'invoke': ctr.getTheService, 'args': lambda: event['siteId']},
            'digSiteDirs': {'invoke': ctr.createNewService},
            'bulkDelete': {'invoke': ctr.bulkDelete},
            'createNewService': {'invoke': ctr.createNewService},
            'syncEfsToS3': {'invoke': ctr.createNewService},
            'createArtifact': {'invoke': ctr.createNewService},
            'restoreArtifact': {'invoke': ctr.createNewService},
            'deployToNetlify': {'invoke': ctr.createNewService},
            'deletePublicContents': {'invoke': ctr.createNewService},
            'deleteTheService': {'invoke': ctr.deleteTheService, 'args': lambda: event['siteId']},
            'deleteServiceByServiceId': {'invoke': ctr.deleteServiceByServiceId, 'args': lambda: event}
        }

        action_name = event['action']

        if action_name not in list(docker_actions):
            # ここには来ないはずだけど一応。
            raise_message = event['action'] + ' is unregistered action type'
            raise ShifterRequestError(info=raise_message)

        docker_action = docker_actions[action_name]
        if 'args' in docker_action:
            args = docker_action['args']()
            result = docker_action['invoke'](args)
        else:
            result = docker_action['invoke']()

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
        rollbar.report_exc_info()
        logger.exception("Error occurred during calls Docker API: " + str(type(e)))
        return ResponseBuilder.buildResponse(
            status=500,
            message='Error occurred during calls Backend Service.',
            logs_to=event
        )

    return result


def validate_arguments(event):
    if 'action' not in event:
        raise ShifterRequestError(info="params 'action' not found.")

    if event['action'] not in AVAIL_ACTIONS.keys():
        raise_message = event['action'] + ' is unregistered action type'
        raise ShifterRequestError(info=raise_message)

    expect_args = AVAIL_ACTIONS[event['action']]
    # python3.x から、dictのキー配列を取得するには、以下のように書く
    actual_args = list(event)

    # チェック対象の引数がなければ通す
    if not expect_args:
        return True

    if not all([x in actual_args for x in expect_args]):
        raise_message = 'Arguments are not enough. expect: %(expect)s, actual: %(actual)s' % {'expect': expect_args, 'actual': actual_args}
        raise ShifterRequestError(info=raise_message)

    if event['action'] == 'bulkDelete' and not isinstance(event['serviceIds'], list):
        raise ShifterRequestError(info="params 'serviceIds' must be list.")

    return True


def do_test(event):
    return 'this is test'
