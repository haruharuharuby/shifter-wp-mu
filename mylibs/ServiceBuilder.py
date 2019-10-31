#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base64
import json
import logging
import os
import hashlib
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
from .CommonHelper import *

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
        service_spec_base = yaml.safe_load(service_spec_rendered)
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

    def build_context_sync_efs_to_s3(self):
        target_buckets = {
            'syncEfsToS3': self.app_config['s3_settings']['artifacts_bucket'],
            'deletePublicContents': self.app_config['s3_settings']['public_bucket']
        }

        delete_options = [
            "DELETE_MODE=TRUE",
            "CF_DIST_ID=" + self.site_item['cf_id']
        ]

        def __get_pj_version():
            if 'pjVersion' in self.query:
                version = self.query['pjVersion']
            elif self.site_item.get('version'):
                version = self.site_item['version']
            else:
                version = "1"
            return version

        context = {}
        context['service_name'] = self.query['sessionid']
        context['service_id'] = self.query['siteId']
        context['image_string'] = ':'.join([self.app_config['docker_images']['sync-efs-to-s3'], self.__get_image_tag_or_latest_or_dev()])
        context['efs_point_root'] = self.site_item['efs_id'] + "/" + self.query['siteId']
        context['efs_point_web'] = self.site_item['efs_id'] + "/" + self.query['siteId'] + "/web"

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

        if self.query['action'] in ['deletePublicContents']:
            env.extend(delete_options)

        if 'artifactId' in self.query:
            env.append('ARTIFACT_ID=' + str(self.query['artifactId']))

        env.append('SNS_TOPIC_ARN=' + self.app_config['sns_arns']['to_delete'])
        env.append("PJ_VERSION=" + __get_pj_version())
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
            # return php_var_from_query or self.site_item.get('php_version', False) or 'latest'
            shifter_env = os.getenv("SHIFTER_ENV", 'development')
            tagname = php_var_from_query or self.site_item.get('php_version', False) or 'latest'

            if shifter_env == 'development':
                if not tagname.count('image'):
                    tagname = tagname + '_develop'

            return tagname

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

        if __get_service_type_or_default() == 'edit-wordpress':
            login_token = self.random_login_token()
            self.s3client.putLoginToken(self.query['siteId'], login_token)
            env.append("SHIFTER_LOGIN_TOKEN=" + login_token)

            if self.query.get('refreshToken') and self.query.get('accessToken'):
                env.append("SHIFTER_ACCESS_TOKEN=" + self.query['accessToken'])
                env.append("SHIFTER_REFRESH_TOKEN=" + self.query['refreshToken'])
                env.append("SHIFTER_API_URL_V1=" + os.environ.get('SHIFTER_API_URL_V1'))
                env.append("SHIFTER_API_URL_V2=" + os.environ.get('SHIFTER_API_URL_V2'))
                env.append("SHIFTER_USER_EMAIL=" + self.query.get('email', ''))
            else:
                raise ShifterRequestError('when edit-wordpress, RefreshToken and AccessToken are required.')

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

        # Safemode
        if self.query.get('opts_cleanup_plugins'):
            env.append('SHIFTEROPTS_CLEANUP_PLUGINS=TRUE')
        if self.query.get('opts_cleanup_themes'):
            env.append('SHIFTEROPTS_CLEANUP_THEMES=TRUE')

        # Emerge mode
        if self.query.get('opts_emerge_admin'):
            env.append('SHIFTEROPTS_EMERGE_ADMIN=' + str(self.query['opts_emerge_admin']))

        # # media cdn
        if self.site_item.get('enable_media_cdn', None):
            env = self.__add_mediacdn_access_key_to_envvars(env)

        # set plan_code
        if self.site_item.get('plan_id'):
            plan_code = code_by_plan_id(self.site_item['plan_id'])
            env.append('SHIFTER_PLAN_CODE=' + plan_code)
        elif self.site_item.get('trial'):
            # as free plan
            env.append('SHIFTER_PLAN_CODE=001')

        if context['service_type'] in ['generator'] and ('plan_code' in locals()):
            # ToDo generate archive urls and set
            enable_ai1wm_backup = self.site_item.get('enable_ai1wm_backup', None)
            artifact_id = self.query.get('artifactId', 'fallbacked_dummyid')

            if enable_ai1wm_backup and (int(plan_code) >= 100):
                archive_url = self.s3client.createBackupUrl(self.query['siteId'], artifact_id)
                archive_error_url = self.s3client.createBackupErrorUrl(self.query['siteId'], artifact_id)
                env.append("ARCIHVE_URL=" + base64.b64encode(archive_url.encode('utf-8')).decode())
                env.append("ARCIHVE_ERR_URL=" + base64.b64encode(archive_error_url.encode('utf-8')).decode())

        context['envvars'] = self.__prepare_envs_for_pystache(env)

        logger.info(context)
        return context

    def random_login_token(self):
        # without __ prefix to create mock
        return hashlib.sha256(os.urandom(32)).hexdigest()

    def __get_image_tag_or_latest(self):
        return self.query['image_tag'] if 'image_tag' in self.query else 'latest'

    def __get_image_tag_or_latest_or_dev(self):
        environ = os.getenv("SHIFTER_ENV", None)
        if 'image_tag' in self.query:
            tag = self.query['image_tag']
        elif environ == 'development':
            tag = 'develop'
        else:
            tag = 'latest'
        return tag

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

    def __add_mediacdn_access_key_to_envvars(self, env, key='media_cdn', *options):
        id_hash = hashlib.sha1(self.query['siteId'].encode('utf-8')).hexdigest()
        uploads_bucket = self.app_config['s3_settings']['mediacdn_bucket'] + '/' + id_hash
        uploads_bucket_url = self.app_config['s3_settings']['mediacdn_cf'] + '/' + id_hash

        env.append('SHIFTER_S3_UPLOADS=' + 'true')
        env.append('SHIFTER_S3_UPLOADS_BUCKET=' + uploads_bucket)
        env.append('SHIFTER_S3_UPLOADS_REGION=' + 'us-east-1')
        env.append('SHIFTER_S3_UPLOADS_BUCKET_URL=' + uploads_bucket_url)

        token_gen = STSTokenGenerator(self.app_config, self.query)
        tokens = token_gen.generateToken(key, 'media_cdn')
        env.append('SHIFTER_S3_UPLOADS_KEY=' + tokens['AccessKeyId'])
        env.append('SHIFTER_S3_UPLOADS_SECRET=' + tokens['SecretAccessKey'])
        env.append('SHIFTER_S3_UPLOADS_TOKEN=' + tokens['SessionToken'])

        for extra_envvar in options:
            env.append(extra_envvar)
        return env
