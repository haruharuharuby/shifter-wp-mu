# -*- coding: utf-8 -*-
from __future__ import print_function

import os, sys
import pytest
from unittest.mock import Mock
import yaml
from ..DockerCtr import DockerCtr
from ..ServiceBuilder import ServiceBuilder

app_config = yaml.load(open('../config/appconfig.yml', 'r'))['development']
test_event = {
      "siteId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
      "action": "syncS3ToS3",
      "serviceType": "syncS3ToS3",
      "sessionid": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
      "phpVersion": "5.5",
      "fsId": "fs-5286491b"
    }

test_site_item = {
    "access_url": "tender-ride7316.on.getshifter.io",
    "cf_id":"E2XDOVHUH57BXZ",
    "cf_url": "dw5aj9smo4km0.cloudfront.net",
    "cname_status": "ready",
    "efs_id": "fs-2308c16a",
    "ID": "c48db543-c3d0-27eb-9598-e6c33a2afdb7",
    "s3_bucket": "to.getshifter.io",
    "s3_region": "to-us-east-1",
    "site_name": "null",
    "site_owner": "null",
    "stock_state": "ready"
}
ServiceBuilder._ServiceBuilder__fetchDynamoSiteItem = Mock(return_value=test_site_item)

def test_DockerCtr():
    '''
    Constructor just store arguments to instance variables.
    '''
    result = DockerCtr(app_config, test_event)
    print(result)
    assert result


def test__getCreateImageBody():
    '''
    Pass to syncS3ToS3, return s3tos3 service_spec
    '''
    query = {
          "siteId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
          "action": "syncS3ToS3",
          "serviceType": "syncS3ToS3",
          "sessionid": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
          "phpVersion": "5.5",
          "fsId": "fs-5286491b",
          "s3_bucket": "from.getshifter.io",
          "s3_region": "from-us-east-1",
        }

    ServiceBuilder._ServiceBuilder__loadServiceTemplate = Mock(return_value=(open('../service_specs/sync-s3-to-s3.yml', 'r').read()))

    instance = DockerCtr(app_config, test_event)
    result = instance._DockerCtr__getCreateImageBody(query)
    print(result)
    assert result == {
        'Labels': {'Name': 'sync-s3-to-s3'},
        'Networks': [{'Target': 'shifter_net_user'}],
        'Name': '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd',
        'TaskTemplate': {
            'ContainerSpec': {
                'Env': [
                    'AWS_ACCESS_KEY_ID=AKIAIXELICZZAPYVYELA',
                    'AWS_SECRET_ACCESS_KEY=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',
                    'S3_REGION_FROM=from-us-east-1',
                    'S3_BUCKET_FROM=from.getshifter.io',
                    'S3_REGION_TO=to-us-east-1',
                    'S3_BUCKET_TO=to.getshifter.io',
                    'SITE_ID=5d5a3d8c-b578-9da9-2126-4bdc13fcaccd',
                    'SERVICE_NAME=5d5a3d8c-b578-9da9-2126-4bdc13fcaccd',
                    'CF_DIST_ID=E2XDOVHUH57BXZ',
                    'SNS_TOPIC_ARN=arn:aws:sns:us-east-1:027273742350:site-gen-sync-s3-finished-development'
                ],
                'Image': '027273742350.dkr.ecr.us-east-1.amazonaws.com/docker-s3tos3:latest',
                'Mounts': [
                    {'Target': '/run', 'Type': 'tmpfs'},
                    {'Target': '/tmp', 'Type': 'tmpfs'}
                ]
            },
            'LogDriver': {
                'Name': 'awslogs', 'Options': {
                    'awslogs-group': 'dockerlog-services',
                    'awslogs-region': 'us-east-1',
                    'awslogs-stream': '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd-s3tos3'
                    }
            },
            'Placement': {
                'Constraints': [
                    'node.labels.type == efs-worker'
                ]
            },
            'RestartPolicy': {
                'Condition': 'on-failure', 'Delay': 5000, 'MaxAttempts': 3
            }
        }
    }
