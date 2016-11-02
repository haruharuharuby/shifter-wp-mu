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
import traceback
from ShifterExceptions import *

# awscs: https://github.com/cloudtools/awacs
from awacs.aws import Action, Allow, Policy, Statement

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
        self.stsclient = boto3.client('sts')

    def generateToken(self, policy_name, policy_type):
        try:
            policy = getattr(self, 'build_policy_' + policy_type.replace('-', '_'))(policy_name)
            res = self.stsclient.get_federation_token(
                    Name=policy_name,
                    Policy=policy,
                    DurationSeconds=10800
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
