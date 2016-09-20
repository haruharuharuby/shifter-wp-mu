#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import unicode_literals
import os
import json
import yaml
import base64
import random
import uuid
import logging
import boto3
import botocore
import requests
import traceback
from DynamoDB import *
from S3 import *
from common_helper import *

# logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger()
logger.setLevel(logging.INFO)


if __name__ == '__main__':
    print('module')


class ServiceBuilder:
    def __init__(self, app_config, query):
        self.app_config = app_config
        self.spec_path = './service_specs/'
        self.query = query
        self.uuid = uuid.uuid4().hex
        self.table_item = self.__fetchDynamoSiteItem()
        return None

    def __fetchDynamoSiteItem():
        dynamodb = DynamoDB(self.app_config)
        dbData = dynamodb.getServiceById(self.query['siteId'])
        dbItem = {
            's3_bucket': '',
            's3_region': '',
        }

        if (dbData['Count'] > 0):
            dbItem = dict(dbItem, **dbData['Items'][0])

        return dbItem

    def buildServiceDef(self, image_type):
        service_spec = self.__loadServiceTemplate(image_type)

        try:
            service_def = getattr(self, 'build_' + image_type.replace('-', '_'))(service_spec)
        except Exception as e:
            logger.error("Error occurred during builds Service definition: " + str(type(e)))
            logger.error(traceback.format_exc())
            raise StandardError("Error occurred during calls Backend Service.")

        return service_def

    def __loadServiceTemplate(self, image_type):
        template_base = yaml.load(open(self.spec_path + image_type + '.yml', 'r'))

        if 'SHIFTER_ENV' in os.environ.keys():
            template = template_base[os.environ['SHIFTER_ENV']]
        else:
            template = template_base['development']

        return template

    def build_wordpress_worker(self, spec):
        service_def = spec['template']

        logger.info(service_def)
        return service_def

    def build_sync_efs_to_s3(self, spec):
        service_def = spec['template']

        logger.info(service_def)
        return service_def

    def tSyncEfsToS3ImageBody(self, query):
        self.uuid = uuid.uuid4().hex
        dynamodb = DynamoDB()
        dbData = dynamodb.getServiceById(query['siteId'])
        dbItem = False
        if 'Items' in dbData:
            if (dbData['Count'] > 0):
                dbItem = dbData['Items'][0]
        if dbItem is False:
            dbItem = {
                's3_bucket': {'S': ''},
                's3_region': {'S': ''},
            }

        body = {
                "Name": self.uuid,
                "Labels": {
                    "Name": "sync-efs-to-s3"
                },
                "TaskTemplate": {
                    "RestartPolicy": {
                        "Condition": "on-failure",
                        "Delay": 5000,
                        "MaxAttempts": 3,
                    },
                    "ContainerSpec": {
                        "Image": self.__getImage('sync-efs-to-s3'),
                        "Env": [
                            "AWS_ACCESS_KEY_ID=" + self.app_config['awscreds']['access_key'],
                            "AWS_SECRET_ACCESS_KEY=" + self.app_config['awscreds']['secret_access_key'],
                            "S3_REGION=" + dbItem['s3_region']['S'],
                            "S3_BUCKET=" + dbItem['s3_bucket']['S'],
                            "SITE_ID=" + query['siteId'],
                            "SERVICE_NAME=" + self.uuid
                        ],
                        "Mounts": [{
                            "Type": "volume",
                            "Target": "/opt/efs/",
                            "Source": query['fsId'] + "/" + query['siteId'],
                            "VolumeOptions": {
                                "DriverConfig": {
                                    "Name": "efs"
                                }
                            }
                        }]
                    },
                    "Placement": {
                        "Constraints": ["node.labels.type == efs-worker"]
                    },
                }
            }
        return body

    def __getWpServiceImageBody(self, query):
        if 'phpVersion' not in query:
            query['phpVersion'] = '7.0'
        s3 = S3(self.app_config)
        notification_url = s3.createNotificationUrl(self.notificationId)
        env = [
            "SERVICE_PORT=" + str(query['pubPort']),
            "SITE_ID=" + query['siteId'],
            "SERVICE_DOMAIN=" + self.app_config['service_domain'],
            "EFS_ID=" + query['fsId'],
            "NOTIFICATION_URL=" + base64.b64encode(notification_url)
        ]
        if 'wpArchiveId' in query:
            archiveUrl = s3.createWpArchiceUrl(query['wpArchiveId'])
            if archiveUrl is not False:
                env.append('ARCHIVE_URL=' + base64.b64encode(archiveUrl))
        body = {
                "Name": query['siteId'],
                "Labels": {
                    "Name": "wordpress-worker"
                },
                "TaskTemplate": {
                    "LogDriver": {
                        "Name": "awslogs",
                        "Options": {
                            "awslogs-region": "us-east-1",
                            "awslogs-group": "dockerlog-services",
                            "awslogs-stream": query['siteId']
                        }
                    },
                    "ContainerSpec": {
                        "Image": self.__getImage('wordpress-worker', query['phpVersion']),
                        "Env": env,
                        "Mounts": [{
                            "Type": "volume",
                            "Target": "/var/www/html",
                            "Source": query['fsId'] + "/" + query['siteId'] + "/web",
                            "VolumeOptions": {
                                "DriverConfig": {
                                    "Name": "efs"
                                }
                            }
                        },
                        {
                            "Type": "volume",
                            "Target": "/var/lib/mysql",
                            "Source": query['fsId'] + "/" + query['siteId'] + "/db",
                            "VolumeOptions": {
                                "DriverConfig": {
                                    "Name": "efs"
                                }
                            }
                        }]
                    },
                    "Placement": {
                        "Constraints": ["node.labels.type == efs-worker"]
                    },
                },
                "EndpointSpec": {
                    "Ports": [
                        {
                            "Protocol": "tcp",
                            "PublishedPort": int(query['pubPort']),
                            "TargetPort": 443
                        }
                    ]
                }
        }
        return body
