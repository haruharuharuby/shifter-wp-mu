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

from .DynamoDB import *
from .S3 import *
from .ShifterExceptions import *
from .STSTokenGenerator import *

# logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

import rollbar

rollbar.init(os.getenv("ROLLBAR_TOKEN"), os.getenv("SHIFTER_ENV", "development"))

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
            rollbar.report_exc_info()
            raise ShifterBackendError("Error occurred during calls Backend Service.")

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
        list(map(lambda ev: new_array.append({"envvar": ev}), envs))
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
            "NOTIFICATION_URL=" + base64.b64encode(notification_url.encode('utf-8')).decode(),
            "NOTIFICATION_ERROR_URL=" + base64.b64encode(notification_error_url.encode('utf-8')).decode(),
            "CF_DOMAIN=" + self.site_item['access_url'],
            "SNS_TOPIC_ARN=" + self.app_config['sns_arns']['to_delete']
        ]

        if self.site_item.get('domain', False):
            if self.site_item['domain'].strip():
                env.append('SHIFTER_DOMAIN=' + self.site_item['domain'])

        if 'wpArchiveId' in self.query:
            archiveUrl = self.s3client.createWpArchiceUrl(self.query['wpArchiveId'])
            if archiveUrl is not False:
                env.append('ARCHIVE_URL=' + base64.b64encode(archiveUrl.encode('utf-8')).decode())

        if self.site_item['user_database']:
            rds = self.site_item['user_database']
            raw_passwd = self.kms_client.decrypt(CiphertextBlob=base64.b64decode(rds['enc_passwd']))
            ob_passwd = base64.b64encode((self.app_config['mgword'] + raw_passwd['Plaintext'].decode()).encode('utf-8'))
            env.append('RDB_ENDPOINT=' + rds['endpoint'])
            env.append('RDB_USER=' + rds['role'])
            env.append('RDB_PASSWD=' + ob_passwd.decode())

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
        target_buckets = {
            'syncEfsToS3': self.app_config['s3_settings']['public_bucket'],
            'deletePublicContents': self.app_config['s3_settings']['public_bucket'],
            'deleteArtifact': self.app_config['s3_settings']['artifacts_bucket']
        }

        delete_options = [
            "DELETE_MODE=TRUE",
            "CF_DIST_ID=" + self.site_item['cf_id']
        ]

        context = {}
        context['service_name'] = self.query['sessionid']
        context['service_id'] = self.query['siteId']
        context['image_string'] = ':'.join([self.app_config['docker_images']['sync-efs-to-s3'], self.__get_image_tag_or_latest()])
        context['efs_point_root'] = self.site_item['efs_id'] + "/" + self.query['siteId']

        # Build Env
        env = [
            "AWS_ACCESS_KEY_ID=" + self.app_config['awscreds']['s3sync']['access_key'],
            "AWS_SECRET_ACCESS_KEY=" + self.app_config['awscreds']['s3sync']['secret_access_key'],
            "S3_REGION=" + self.site_item['s3_region'],
            "S3_BUCKET=" + target_buckets[self.query['action']],
            "SITE_ID=" + self.query['siteId'],
            "SERVICE_NAME=" + self.query['sessionid'],
            "DYNAMODB_TABLE=" + self.app_config['dynamo_settings']['site_table']
        ]

        if self.query['action'] in ['deletePublicContents', 'deleteArtifact']:
            env.extend(delete_options)

        if 'artifactId' in self.query:
            env.append('ARTIFACT_ID=' + str(self.query['artifactId']))

        env.append('SNS_TOPIC_ARN=' + self.app_config['sns_arns']['to_delete'])
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
            "DYNAMO_TABLE=" + self.app_config['dynamo_settings']['site_table'],
            'SNS_TOPIC_ARN=' + self.app_config['sns_arns']['to_delete']
        ]

        context['envvars'] = self.__prepare_envs_for_pystache(env)

        logger.info(context)
        return context

    def build_context_docker_s3to_netlify(self):
        context = {}
        context['service_name'] = self.query['sessionid']
        context['service_id'] = self.query['siteId']
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

        if 'artifactId' in self.query:
            env.append('ARTIFACT_ID=' + str(self.query['artifactId']))

        env.append('SNS_TOPIC_ARN=' + self.app_config['sns_arns']['to_delete'])
        context['envvars'] = self.__prepare_envs_for_pystache(env)

        logger.info(context)
        return context

    def build_context_sync_s3_to_s3(self):
        context = self.__set_service_context()
        tag = self.__get_image_tag_or_latest()

        context['image_string'] = ':'.join([self.app_config['docker_images']['sync-s3-to-s3'], tag])

        # Build Env
        artifact_bucket = self.app_config['s3_settings']['artifacts_bucket'] + '/' + self.query['artifactId']
        public_bucket = self.app_config['s3_settings']['public_bucket'] + '/' + self.query['siteId']
        target_buckets = {
            'createArtifact': {'from': public_bucket, 'to': artifact_bucket},
            'restoreArtifact': {'from': artifact_bucket, 'to': public_bucket}
        }
        env = [
            "AWS_ACCESS_KEY_ID=" + self.app_config['awscreds']['s3sync']['access_key'],
            "AWS_SECRET_ACCESS_KEY=" + self.app_config['awscreds']['s3sync']['secret_access_key'],
            "S3_REGION=" + self.app_config['s3_settings']['region'],
            "S3_FROM=" + target_buckets[self.query['action']]['from'],
            "S3_TO=" + target_buckets[self.query['action']]['to'],
            "SERVICE_NAME=" + self.query['sessionid'],
            "SNS_TOPIC_ARN=" + self.app_config['sns_arns']['to_delete']
        ]

        if self.query['action'] == 'restoreArtifact':
            env.append("CF_DIST_ID=" + self.site_item['cf_id'])

        context['envvars'] = self.__prepare_envs_for_pystache(env)

        logger.info(context)
        return context

    def build_context_wordpress_worker2(self):
        def __get_service_type_or_default():
            return self.query['serviceType'] if 'serviceType' in self.query else 'edit-wordpress'

        def __get_php_version_or_latest():
            php_var_from_query = self.query['phpVersion'] if 'phpVersion' in self.query else ''
            return php_var_from_query or self.site_item.get('php_version', False) or 'latest'

        context = {}
        context['service_name'] = self.query['siteId']
        context['service_type'] = __get_service_type_or_default()
        context['image_string'] = ':'.join([self.app_config['docker_images']['wordpress-worker2'], __get_php_version_or_latest()])
        context['publish_port1'] = int(self.query['pubPort'])
        context['efs_point_web'] = self.site_item['efs_id'] + "/" + self.query['siteId'] + "/web"

        # Build Env
        notification_url = self.s3client.createNotificationUrl(self.query['notificationId'])
        notification_error_url = self.s3client.createNotificationErrorUrl(self.query['notificationId'])
        env = [
            "SERVICE_PORT=" + str(self.query['pubPort']),
            "SERVICE_TYPE=" + __get_service_type_or_default(),
            "SITE_ID=" + self.query['siteId'],
            "SERVICE_DOMAIN=" + self.app_config['service_domain'],
            "NOTIFICATION_URL=" + base64.b64encode(notification_url.encode('utf-8')).decode(),
            "NOTIFICATION_ERROR_URL=" + base64.b64encode(notification_error_url.encode('utf-8')).decode(),
            "CF_DOMAIN=" + self.site_item['access_url'],
            "SNS_TOPIC_ARN=" + self.app_config['sns_arns']['to_delete']
        ]

        if 'domain' in self.site_item and self.site_item['domain'].strip() and self.site_item['domain'] != 'null':
            env.append('SHIFTER_DOMAIN=' + self.site_item['domain'])

        if self.site_item['user_database']:
            rds = self.site_item['user_database']
            raw_passwd = self.kms_client.decrypt(CiphertextBlob=base64.b64decode(rds['enc_passwd']))
            ob_passwd = base64.b64encode((self.app_config['mgword'] + raw_passwd['Plaintext'].decode()).encode('utf-8'))
            env.append('RDB_ENDPOINT=' + rds['endpoint'])
            env.append('RDB_USER=' + rds['role'])
            env.append('RDB_PASSWD=' + ob_passwd.decode())
        else:
            raise ShifterInvalidSiteItem('RDS information could not be found.')

        if context['service_type'] in ['create-archive']:
            self.__add_aws_access_key_to_envvars(env, 'create-archive', ('SHIFTER_TOKEN=' + self.query['shifterToken']))
        elif context['service_type'] in ['import-archive']:
            # ToDo
            self.__add_aws_access_key_to_envvars(env, 'import-archive')

        context['envvars'] = self.__prepare_envs_for_pystache(env)

        logger.info(context)
        return context

    def __get_image_tag_or_latest(self):
        return self.query['image_tag'] if 'image_tag' in self.query else 'latest'

    def __set_service_context(self):
        return {
            'service_name': self.query['sessionid'],
            'service_id': self.query['siteId']
        }

    def __add_aws_access_key_to_envvars(self, env, key='create-archive', *options):
        token_gen = STSTokenGenerator(self.app_config)
        tokens = token_gen.generateToken(key, 'uiless_wp')
        env.append('AWS_ACCESS_KEY_ID=' + tokens['AccessKeyId'])
        env.append('AWS_SECRET_ACCESS_KEY=' + tokens['SecretAccessKey'])
        env.append('AWS_SESSION_TOKEN=' + tokens['SessionToken'])
        for extra_envvar in options:
            env.append(extra_envvar)
        return env
