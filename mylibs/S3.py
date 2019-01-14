#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import base64
import random
import uuid
import logging
import boto3
import botocore
from aws_xray_sdk.core import xray_recorder

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class S3:
    def __init__(self, app_config):
        self.client = boto3.client('s3')
        self.resource = boto3.resource('s3')
        self.archives_bucket = app_config['s3_settings']['archives_bucket']
        self.notification_bucket = app_config['s3_settings']['notification_bucket']
        return None

    @xray_recorder.capture('S3___hasObject')
    def __hasObject(self, key):
        try:
            self.client.get_object(
                Bucket=self.archives_bucket,
                Key=key
            )
            return True
        except botocore.exceptions.ClientError as e:
            logger.info(e)
            return False

    @xray_recorder.capture('S3_createNotificationUrl')
    def createNotificationUrl(self, notificationId):
        result = self.client.generate_presigned_url(
            ClientMethod='put_object',
            Params={
                'Bucket': self.notification_bucket,
                'Key': notificationId
            },
            ExpiresIn=3600,
            HttpMethod='PUT'
        )
        return result

    @xray_recorder.capture('S3_createNotificationErrorUrl')
    def createNotificationErrorUrl(self, notificationId):
        result = self.createNotificationUrl(notificationId + '/errors')
        return result

    @xray_recorder.capture('S3_putLoginToken')
    def putLoginToken(self, siteId, login_token):
        obj = self.resource.Object(self.notification_bucket, siteId + '/token')
        result = obj.put(Body=login_token)
        return result

    @xray_recorder.capture('S3_createWpArchiceUrl')
    def createWpArchiceUrl(self, wpArchiveId):
        if (self.__hasObject(wpArchiveId + '/wordpress.zip')):
            result = self.client.generate_presigned_url(
                ClientMethod='get_object',
                Params={
                    'Bucket': self.archives_bucket,
                    'Key': wpArchiveId + '/wordpress.zip'
                },
                ExpiresIn=3600,
                HttpMethod='GET'
            )
            return result
        else:
            return False
