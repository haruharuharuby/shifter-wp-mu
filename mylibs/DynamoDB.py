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
from boto3.dynamodb.conditions import Key, Attr
import botocore


class DynamoDB:
    def __init__(self, app_config):
        client = boto3.resource('dynamodb')
        self.sitetable = client.Table(app_config['dynamo_settings']['site_table'])

    def getServiceById(self, serviceName):
        res = self.sitetable.query(
            KeyConditionExpression=Key('ID').eq(serviceName)
        )
        return res

    def resetSiteItem(self, serviceName):
        res = self.sitetable.update_item(
            Key={
                'ID': serviceName
            },
            UpdateExpression='SET docker_url=:docker_url,stock_state=:stock_state',
            ExpressionAttributeValues={
                ':docker_url': None,
                ':stock_state': 'inuse'
            },
            ReturnValues="ALL_NEW"
        )
        return res

    def updateSiteState(self, message):
        res = self.sitetable.update_item(
            Key={
                'ID': message['serviceName']
            },
            UpdateExpression='SET docker_url=:docker_url,stock_state=:stock_state',
            ExpressionAttributeValues={
                ':docker_url': message['docker_url'],
                ':stock_state': message['stock_state']
            },
            ReturnValues="ALL_NEW"
        )
        return res
