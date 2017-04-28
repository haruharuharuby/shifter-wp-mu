#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base64
import json
import logging
import os
import random
import traceback

import boto3
import botocore
import pystache
import requests
import yaml

from DynamoDB import *
from S3 import *
from ShifterExceptions import *
from STSTokenGenerator import *

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
        self.s3client = S3(app_config)
        self.kms_client = boto3.client('kms')

        if 'siteId' in query:
            self.site_item = self.__fetchDynamoSiteItem()

        return None

    def __fetchDynamoSiteItem(self):
        dynamodb = DynamoDB(self.app_config)
        dbData = dynamodb.getServiceById(self.query['siteId'])

        rdbData = dynamodb.fetchUserDBById(self.query['siteId'])

        dbItem = {
            's3_bucket': '',
            's3_region': '',
            'user_database': rdbData
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
            service_spec = service_spec_base['dev']
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

        if 'serviceType' in self.query:
            context['service_type'] = self.query['serviceType']
        else:
            context['service_type'] = 'edit-wordpress'

        if 'phpVersion' in self.query:
            tag = self.query['phpVersion']
        elif self.site_item.get('php_version', False):
            tag = self.site_item['php_version']
        else:
            tag = 'latest'
        context['image_string'] = ':'.join([self.app_config['docker_images']['wordpress-worker'], tag])

        context['publish_port1'] = int(self.query['pubPort'])
        context['efs_point_web'] = self.site_item['efs_id'] + "/" + self.query['siteId'] + "/web"
        context['efs_point_db'] = self.site_item['efs_id'] + "/" + self.query['siteId'] + "/db"

        # Build Env
        notification_url = self.s3client.createNotificationUrl(self.query['notificationId'])
        notification_error_url = self.s3client.createNotificationErrorUrl(self.query['notificationId'])
        env = [
            "SERVICE_PORT=" + str(self.query['pubPort']),
            "SERVICE_TYPE=" + self.query['serviceType'],
            "SITE_ID=" + self.query['siteId'],
            "SERVICE_DOMAIN=" + self.app_config['service_domain'],
            "EFS_ID=" + self.site_item['efs_id'],
            "NOTIFICATION_URL=" + base64.b64encode(notification_url),
            "NOTIFICATION_ERROR_URL=" + base64.b64encode(notification_error_url),
            "CF_DOMAIN=" + self.site_item['access_url']
        ]

        if self.site_item.get('domain', False):
            if self.site_item['domain'].strip():
                env.append('SHIFTER_DOMAIN=' + self.site_item['domain'])

        if 'wpArchiveId' in self.query:
            archiveUrl = self.s3client.createWpArchiceUrl(self.query['wpArchiveId'])
            if archiveUrl is not False:
                env.append('ARCHIVE_URL=' + base64.b64encode(archiveUrl))

        if self.site_item['user_database']:
            pass
            rds = self.site_item['user_database']
            raw_passwd = self.kms_client.decrypt(CiphertextBlob=base64.b64decode(rds['enc_passwd']))
            ob_passwd = base64.b64encode(self.app_config['mgword'] + raw_passwd['Plaintext'])
            env.append('RDB_ENDPOINT=' + rds['endpoint'])
            env.append('RDB_USER=' + rds['role'])
            env.append('RDB_PASSWD=' + ob_passwd)

        if context['service_type'] in ['edit-wordpress']:
            env.append('DISPLAY_ERRORS=On')

        if context['service_type'] in ['create-archive']:
            env.append('SHIFTER_TOKEN=' + self.query['shifterToken'])
            token_gen = STSTokenGenerator(self.app_config)
            tokens = token_gen.generateToken('create-archive', 'uiless_wp')
            env.append('AWS_ACCESS_KEY_ID=' + tokens['AccessKeyId'])
            env.append('AWS_SECRET_ACCESS_KEY=' + tokens['SecretAccessKey'])
            env.append('AWS_SESSION_TOKEN=' + tokens['SessionToken'])

        if context['service_type'] in ['import-archive']:
            token_gen = STSTokenGenerator(self.app_config)
            tokens = token_gen.generateToken('import-archive', 'uiless_wp')
            env.append('AWS_ACCESS_KEY_ID=' + tokens['AccessKeyId'])
            env.append('AWS_SECRET_ACCESS_KEY=' + tokens['SecretAccessKey'])
            env.append('AWS_SESSION_TOKEN=' + tokens['SessionToken'])

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

        context['efs_point_root'] = self.site_item['efs_id'] + "/" + self.query['siteId']

        # Build Env
        if self.query['action'] == 'syncEfsToS3':
            env = [
                    "AWS_ACCESS_KEY_ID=" + self.app_config['awscreds']['s3sync']['access_key'],
                    "AWS_SECRET_ACCESS_KEY=" + self.app_config['awscreds']['s3sync']['secret_access_key'],
                    "S3_REGION=" + self.site_item['s3_region'],
                    "S3_BUCKET=" + self.site_item['s3_bucket'],
                    "SITE_ID=" + self.query['siteId'],
                    "SERVICE_NAME=" + self.query['sessionid']
            ]
        elif self.query['action'] == 'deletePublicContents':
            env = [
                    "AWS_ACCESS_KEY_ID=" + self.app_config['awscreds']['s3sync']['access_key'],
                    "AWS_SECRET_ACCESS_KEY=" + self.app_config['awscreds']['s3sync']['secret_access_key'],
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

    def build_context_docker_efs_dig_dirs(self):
        context = {}
        context['service_name'] = self.query['sessionid']
        if 'image_tag' in self.query:
            tag = self.query['image_tag']
        else:
            tag = 'latest'
        context['image_string'] = ':'.join([self.app_config['docker_images']['docker-efs-dig-dirs'], tag])

        context['efs_point_root'] = self.query['fsId']

        # Build Env
        env = [
                "AWS_ACCESS_KEY_ID=" + self.app_config['awscreds']['stock_manage']['access_key'],
                "AWS_SECRET_ACCESS_KEY=" + self.app_config['awscreds']['stock_manage']['secret_access_key'],
                "EFS_ID=" + self.query['fsId'],
                "SERVICE_NAME=" + self.query['sessionid'],
                "DYNAMO_TABLE=" + self.app_config['dynamo_settings']['site_table']
        ]

        context['envvars'] = self.__prepare_envs_for_pystache(env)

        logger.info(context)
        return context

    def build_context_docker_s3to_netlify(self):
        context = {}
        context['service_name'] = self.query['sessionid']
        if 'image_tag' in self.query:
            tag = self.query['image_tag']
        else:
            tag = 'latest'

        context['image_string'] = ':'.join([self.app_config['docker_images']['docker-s3to-netlify'], tag])

        # Build Env
        env = [
                "AWS_ACCESS_KEY_ID=" + self.app_config['awscreds']['s3sync']['access_key'],
                "AWS_SECRET_ACCESS_KEY=" + self.app_config['awscreds']['s3sync']['secret_access_key'],
                "SITE_ID=" + self.query['siteId'],
                "SERVICE_NAME=" + self.query['sessionid'],
                "NF_SITEID=" + self.query['nf_siteID'],
                "NF_TOKEN=" + self.query['nf_token']
        ]

        if 'nf_draft' in self.query:
            env.append('NF_DRAFT=' + str(self.query['nf_draft']))

        context['envvars'] = self.__prepare_envs_for_pystache(env)

        logger.info(context)
        return context
