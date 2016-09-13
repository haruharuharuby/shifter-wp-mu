#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class S3:
    def __init__(self):
        self.client = boto3.client('s3')

    def __getWpArchiveBucketName(self):
        return 'wp-archives-files'

    def __getNotificationBucketname(self):
        return 'sys.status.getshifter'

    def __hasObject(self, key):
        try:
            self.client.get_object(
                Bucket=self.__getWpArchiveBucketName(),
                Key=key
            )
            return True
        except botocore.exceptions.ClientError as e:
            logger.info(e)
            return False

    def createNotificationUrl(self, notificationId):
        result = self.client.generate_presigned_url(
            ClientMethod='put_object',
            Params={
                'Bucket': self.__getNotificationBucketname(),
                'Key': notificationId
            },
            ExpiresIn=3600,
            HttpMethod='PUT'
        )
        return result

    def createWpArchiceUrl(self, wpArchiveId):
        if (self.__hasObject(wpArchiveId + '/wordpress.zip')):
            result = self.client.generate_presigned_url(
                ClientMethod='get_object',
                Params={
                    'Bucket': self.__getWpArchiveBucketName(),
                    'Key': wpArchiveId + '/wordpress.zip'
                },
                ExpiresIn=3600,
                HttpMethod='GET'
            )
            return result
        else:
            return False
