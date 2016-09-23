#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import unicode_literals
import os
import json
import yaml
import base64
import random
import logging
import boto3
import botocore
import requests
import pystache
import traceback
from DynamoDB import *
from S3 import *

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
        self.site_item = self.__fetchDynamoSiteItem()
        self.s3client = S3(app_config)
        return None

    def __fetchDynamoSiteItem(self):
        dynamodb = DynamoDB(self.app_config)
        dbData = dynamodb.getServiceById(self.query['siteId'])
        dbItem = {
            's3_bucket': '',
            's3_region': '',
        }

        dbItem = dict(dbItem, **dbData)

        return dbItem

    def buildServiceDef(self, image_type):
        template_base = self.__loadServiceTemplate(image_type)

        try:
            context = getattr(self, 'build_context_' + image_type.replace('-', '_'))()
        except Exception as e:
            logger.error("Error occurred during builds Service definition: " + str(type(e)))
            logger.error(traceback.format_exc())
            raise StandardError("Error occurred during calls Backend Service.")

        service_spec_rendered = pystache.render(template_base, context)
        logger.debug(service_spec_rendered)
        service_spec_base = yaml.load(service_spec_rendered)
        logger.debug(service_spec_base)
        if 'SHIFTER_ENV' in os.environ.keys():
            service_spec = service_spec_base[os.environ['SHIFTER_ENV']]
        else:
            service_spec = service_spec_base['development']
        return service_spec

    def __loadServiceTemplate(self, image_type):
        template_base = open(self.spec_path + image_type + '.yml', 'r').read()
        return template_base

    def __prepare_envs_for_pystache(self, envs):
        new_array = []
        map(lambda ev: new_array.append({"envvar": ev}), envs)
        return new_array

    def build_context_wordpress_worker(self):
        context = {}
        context['service_name'] = self.query['siteId']
        if 'phpVersion' in self.query:
            tag = self.query['phpVersion']
        else:
            tag = 'latest'
        context['image_string'] = ':'.join([self.app_config['docker_images']['wordpress-worker'], tag])

        context['publish_port1'] = int(self.query['pubPort'])
        context['efs_point_web'] = self.query['fsId'] + "/" + self.query['siteId'] + "/web"
        context['efs_point_db'] = self.query['fsId'] + "/" + self.query['siteId'] + "/db"

        # Build Env
        notification_url = self.s3client.createNotificationUrl(self.query['notificationId'])
        notification_error_url = self.s3client.createNotificationErrorUrl(self.query['notificationId'])
        env = [
            "SERVICE_PORT=" + str(self.query['pubPort']),
            "SITE_ID=" + self.query['siteId'],
            "SERVICE_DOMAIN=" + self.app_config['service_domain'],
            "EFS_ID=" + self.query['fsId'],
            "NOTIFICATION_URL=" + base64.b64encode(notification_url),
            "NOTIFICATION_ERROR_URL=" + base64.b64encode(notification_error_url)
        ]

        if 'wpArchiveId' in self.query:
            archiveUrl = self.s3client.createWpArchiceUrl(self.query['wpArchiveId'])
            if archiveUrl is not False:
                env.append('ARCHIVE_URL=' + base64.b64encode(archiveUrl))

        context['envvars'] = self.__prepare_envs_for_pystache(env)

        logger.info(context)
        return context

    def build_context_sync_efs_to_s3(self):
        context = {}
        context['service_name'] = self.query['sessionid']
        context['service_id'] = self.query['siteId']
        if 'image_tag' in self.query:
            tag = self.query['image_tag']
        else:
            tag = 'latest'
        context['image_string'] = ':'.join([self.app_config['docker_images']['sync-efs-to-s3'], tag])

        context['efs_point_root'] = self.query['fsId'] + "/" + self.query['siteId']

        # Build Env
        if self.query['action'] == 'syncEfsToS3':
            env = [
                    "AWS_ACCESS_KEY_ID=" + self.app_config['awscreds']['access_key'],
                    "AWS_SECRET_ACCESS_KEY=" + self.app_config['awscreds']['secret_access_key'],
                    "S3_REGION=" + self.site_item['s3_region'],
                    "S3_BUCKET=" + self.site_item['s3_bucket'],
                    "SITE_ID=" + self.query['siteId'],
                    "SERVICE_NAME=" + self.query['sessionid']
            ]
        elif self.query['action'] == 'deletePublicContents':
            env = [
                    "AWS_ACCESS_KEY_ID=" + self.app_config['awscreds']['access_key'],
                    "AWS_SECRET_ACCESS_KEY=" + self.app_config['awscreds']['secret_access_key'],
                    "S3_REGION=" + self.site_item['s3_region'],
                    "S3_BUCKET=" + self.site_item['s3_bucket'],
                    "SITE_ID=" + self.query['siteId'],
                    "SERVICE_NAME=" + self.query['sessionid'],
                    "DELETE_MODE=TRUE",
                    "CF_DIST_ID=" + self.site_item['cf_id']
            ]

        context['envvars'] = self.__prepare_envs_for_pystache(env)

        logger.info(context)
        return context
