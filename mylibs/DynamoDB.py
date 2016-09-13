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


class DynamoDB:
    def __init__(self):
        self.client = boto3.client('dynamodb')

    def __getSiteTableName(self):
        return 'Site'

    def getServiceById(self, serviceName):
        res = self.client.scan(
            TableName=self.__getSiteTableName(),
            FilterExpression="ID = :id",
            ExpressionAttributeValues={
                ':id': {'S': serviceName}
            }
        )
        return res

    def deleteWpadminUrl(self, serviceName):
        res = self.client.update_item(
            TableName=self.__getSiteTableName(),
            Key={
                'ID': {'S': serviceName}
            },
            UpdateExpression='SET docker_url=:docker_url,stock_state=:stock_state',
            ExpressionAttributeValues={
                ':docker_url': {'NULL': True},
                ':stock_state': {'S': 'inuse'}
            }
        )
        return res

    def updateItem(self, message):
        res = self.client.update_item(
            TableName=self.__getSiteTableName(),
            Key={
                'ID': {'S': message['serviceName']}
            },
            UpdateExpression='SET docker_url=:docker_url,stock_state=:stock_state',
            ExpressionAttributeValues={
                ':docker_url': {'S': message['docker_url']},
                ':stock_state': {'S': message['stock_state']}
            }
        )
        return res
