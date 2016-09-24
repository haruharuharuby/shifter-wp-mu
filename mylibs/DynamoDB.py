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

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class DynamoDB:
    """
    Basic Rules: 上から優先
    - Hashか`Hash+Range`がわかっているアイテムはget_itemを最優先する、早い
    - indexが存在する場合はID一覧の取得などにindexを使用する
    - indexは作成してもいいが、遅延を考慮してHash+Rangeの2つで済むように。
    - ファントムリードを考慮しなくて良い場合のみ、indexのキーを増やして良い
    - HashかRangeが絡む場合queryをつかう
    - scanは最後の手段、indexを検討する。
    """

    def __init__(self, app_config):
        client = boto3.resource('dynamodb')
        self.sitetable = client.Table(app_config['dynamo_settings']['site_table'])

    def getServiceById(self, serviceName):
        """
        Returns Hash Item or {}.
        - 対象がDynamoのHashキーなので、必ず1つを返すか対象なしの2択。
        """
        res = self.sitetable.get_item(
                Key={'ID': serviceName}
        )
        logger.info(res['ResponseMetadata'])
        if 'Item' in res:
            item = res['Item']
        else:
            item = {}

        return item

    def resetSiteItem(self, serviceName):
        """
        Returns Attributes( updated Item)
        """
        if len(self.getServiceById(serviceName)) == 0:
            return {}
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
        return res['Attributes']

    def updateSiteState(self, message):
        """
        Returns Attributes( updated Item)
        """
        if len(self.getServiceById(message['serviceName'])) == 0:
            return {}

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
        return res['Attributes']
