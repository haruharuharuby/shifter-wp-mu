#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import yaml
import base64
import hashlib
import random
import logging
import boto3
from boto3.session import Session
import botocore
import traceback
from .ShifterExceptions import *

# awscs: https://github.com/cloudtools/awacs
from awacs.aws import Action, Allow, Policy, Statement, Condition

# logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger()
logger.setLevel(logging.INFO)


if __name__ == '__main__':
    print('module')


class STSTokenGenerator:
    """
    Type: Module
    Returns IAM Creds via STS GetFederationToken (3h)
    Dict of:
      Str: AccessKeyId
      DateTime: Expiration
      Str: SecretAccessKey
      Str: SessionToken
    """

    def __init__(self, app_config, options={}):
        self.app_config = app_config
        self.options = options
        # 3h + 10min
        self.DurationSeconds = 11400
        session = Session(aws_access_key_id=app_config['awscreds']['s3sync']['access_key'],
                          aws_secret_access_key=app_config['awscreds']['s3sync']['secret_access_key'],
                          region_name='us-east-1')
        self.stsclient = session.client('sts')

    def generateToken(self, policy_name, policy_type):
        try:
            policy = getattr(self, 'build_policy_' + policy_type.replace('-', '_'))(policy_name)
            res = self.stsclient.get_federation_token(
                    Name=policy_name,
                    Policy=policy,
                    DurationSeconds=self.DurationSeconds
                  )
        except Exception as e:
            logger.error("Error occurred during builds IAM policy: " + str(type(e)))
            logger.error(traceback.format_exc())
            raise ShifterUnknownError("Error occurred during calls Backend Service.")

        logger.info(res.get('ResponseMetadata', {}).get('HTTPStatusCode', 400))
        return res['Credentials']

    def build_policy_test(self, name):
        pd = Policy(
                Id=name,
                Statement=[
                    Statement(
                        Effect=Allow,
                        Action=[Action("s3", "*")],
                        Resource=["arn:aws:s3:::my_corporate_bucket/*"],
                    ),
                ],
             )
        logger.debug(pd.to_json())
        return pd.to_json()

    def build_policy_uiless_wp(self, name):
        """
        Allow put id to SNS for delete service by itself.
        """
        pd = Policy(
                Id=name,
                Statement=[
                    Statement(
                        Effect=Allow,
                        Action=[Action("sns", "Publish")],
                        Resource=[
                            "arn:aws:sns:us-east-1:027273742350:site-gen-sync-s3-finished",
                            "arn:aws:sns:us-east-1:027273742350:site-gen-sync-s3-finished-development"
                        ],
                    ),
                ],
             )
        logger.debug(pd.to_json())
        return pd.to_json()

    def build_policy_media_cdn(self, name):
        """
        Allow Access to Media CDN.
        https://github.com/humanmade/S3-Uploads/blob/master/inc/class-s3-uploads-wp-cli-command.php
        """

        # 6h
        self.DurationSeconds = 21600

        bucket = self.app_config['s3_settings']['mediacdn_bucket']
        id_hash = hashlib.sha1(self.options['siteId']).hexdigest()

        pd = Policy(
                Id=name,
                Statement=[
                    Statement(
                        Effect=Allow,
                        Action=[
                            Action("s3", "AbortMultipartUpload"),
                            Action("s3", "DeleteObject"),
                            Action("s3", "GetBucketAcl"),
                            Action("s3", "GetBucketLocation"),
                            Action("s3", "GetBucketPolicy"),
                            Action("s3", "GetObject"),
                            Action("s3", "GetObjectAcl"),
                            Action("s3", "ListBucket"),
                            Action("s3", "ListBucketMultipartUploads"),
                            Action("s3", "ListMultipartUploadParts"),
                            Action("s3", "PutObject"),
                            Action("s3", "PutObjectAcl"),
                        ],
                        Resource=[
                            "arn:aws:s3:::" + bucket + '/' + id_hash + '/*',
                        ],
                    ),
                    Statement(
                        Effect=Allow,
                        Action=[
                            Action("s3", "ListBucket"),
                        ],
                        Resource=[
                            "arn:aws:s3:::" + bucket,
                        ],
                        Condition=Condition(
                            StringLike("s3:prefix", [id_hash + '/*'])
                        )
                    ),
                ],
             )
        logger.debug(pd.to_json())
        return pd.to_json()
