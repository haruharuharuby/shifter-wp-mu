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
import requests
import traceback
from ShifterExceptions import *
from DynamoDB import *
from ServiceBuilder import *
from ResponseBuilder import *
from S3 import *

logger = logging.getLogger()
logger.setLevel(logging.INFO)


if __name__ == '__main__':
    print('module')


class DockerCtr:
    """
    Docker関連のAPI
    上の方にディスパッチャから呼ばれるメソッドを置く
    RAWはDockerの内部情報が沢山入っているので取扱注意のAPI
    """

    def __init__(self, app_config, event):
        self.event = event
        self.app_config = app_config
        self.dockerapi_config = app_config['dockerapi']
        self.sessionid = uuid.uuid4().hex
        self.event['sessionid'] = self.sessionid
        self.docker_session = self.buildDockerSession()
        # http://docs.python-requests.org/en/master/user/advanced/#timeouts
        self.timeout_opts = (5.0, 15.0)
        self.notificationId = self.sessionid

    def buildDockerSession(self):
        session = requests.Session()
        session.auth = (self.dockerapi_config['authuser'], self.dockerapi_config['authpass'])
        session.mount("http://", requests.adapters.HTTPAdapter(max_retries=3))
        session.mount("https://", requests.adapters.HTTPAdapter(max_retries=3))
        return session

    """ RAW APIs"""
    def getServices(self):
        res = self.docker_session.get(self.dockerapi_config['endpoint'] + 'services', timeout=self.timeout_opts)
        logger.info(res.status_code)
        result = res.json()

        return result

    def getTheService(self, siteId):
        res = self.docker_session.get(self.dockerapi_config['endpoint'] + 'services/' + siteId, timeout=self.timeout_opts)
        logger.info(res.status_code)
        result = res.json()
        result['status'] = res.status_code

        if (self.__hasDockerPublishedPort(result)):
            port = str(result['Endpoint']['Spec']['Ports'][0]['PublishedPort'])
            result['DockerUrl'] = 'https://' + self.app_config['service_domain'] + ':' + port
        return result

    """ Wrapped APIs"""
    def createNewService(self):
        query = self.event
        if not (self.__isAvailablePortNum()):
            error = {
                'status': 400,
                'message': 'available port not found.',
                'siteId': query['siteId']
            }
            return error
        else:
            res = self.__createNewService(query)
            if isinstance(res, urllib2.URLError):
                read = res.read()
                result = json.loads(read)
                result['status'] = 500
                result['siteId'] = query['siteId']
                return result
            else:
                return res

    def deleteTheService(self, siteId):
        """ 404 のレスポンスはほぼ無加工でOKだけど一応Wrap """
        res = self.docker_session.delete(self.dockerapi_config['endpoint'] + 'services/' + siteId, timeout=self.timeout_opts)
        logger.info(res.status_code)
        if res.ok:
            message = "service: " + siteId + " is deleted."
        elif res.status_code == 404:
            message = str(res.json()['message'])
        else:
            res.raise_for_status()

        self.__deleteServiceHookDynamo(siteId)
        return ResponseBuilder.buildResponse(
                status=res.status_code,
                message=message,
                serviceId=siteId,
                logs_to=None
        )

    def deleteServiceByServiceId(self, query):
        return self.deleteTheService(query['serviceId'])

    """ Priveate Methods"""
    def __getXRegistryAuth(self):
        try:
            ecr = boto3.client('ecr')
            res = ecr.get_authorization_token()
            raw_token = res['authorizationData'][0]['authorizationToken']
            usertoken = base64.b64decode(raw_token).split(':')
            jsondata = {}
            jsondata['username'] = usertoken[0]
            jsondata['password'] = usertoken[1]
            jsondata['email'] = 'none'
            auth_string = base64.b64encode(json.dumps(jsondata))
        except:
            auth_string = 'failed_to_get_token'
        return auth_string

    def __convertToJson(self, param):
        return json.dumps(param)

    def __getPortNum(self):
        num = random.randint(10000, 30000)
        return num

    def __countRunningService(self):
        services = self.getServices()
        return len(services)

    def __isAvailablePortNum(self):
        portNum = self.__countRunningService()
        portLimit = self.app_config['limits']['max_ports']
        if (portNum > portLimit):
            return False
        else:
            return True

    def __getCreateImageBody(self, query):
        query['notificationId'] = self.notificationId
        if (query["action"] == 'syncEfsToS3'):
            body = self.__getSyncEfsToS3ImageBody(query)
        elif (query["action"] == 'createNewService'):
            body = self.__getWpServiceImageBody(query)
            if 'serviceType' in query:
                body['Labels']['Service'] = query['serviceType']
                # if ( query['serviceType'] == 'generator' ):
            else:
                body['Labels']['Service'] = 'edit-wordpress'
                query['serviceType'] = 'edit-wordpress'
        return body

    def __hasDockerPublishedPort(self, docker):
        if 'Endpoint' in docker:
            if 'Spec' in docker['Endpoint']:
                if 'Ports' in docker['Endpoint']['Spec']:
                    if 'PublishedPort' in docker['Endpoint']['Spec']['Ports'][0]:
                        return True
        return False

    def __createNewServiceInfo(self, query, result):
        message = {
            'status': 200,
            'docker_url': 'https://' + self.app_config['service_domain'] + ':' + str(query['pubPort']),
            'serviceName': query['siteId'],
            'notificationId': self.notificationId
        }
        if 'ID' in result:
            message['serviceId'] = result['ID']
        if 'serviceType' in query:
            if (query['serviceType'] == 'generator'):
                message['stock_state'] = 'ingenerate'
            elif (query['serviceType'] == 'edit-wordpress'):
                message['stock_state'] = 'inservice'
            else:
                message['stock_state'] = 'inuse'
        else:
            message['stock_state'] = 'inuse'
        return message

    def __saveToDynamoDB(self, message):
        dynamo = DynamoDB(self.app_config)
        dynamo.updateSiteState(message)

    def __canCreateNewService(self, Item, query):
        if (Item['stock_state'] == 'ingenerate'):
            message = {
                "status": 409,
                "name": "website now generating",
                "message": "site id:" + query['siteId'] + " is now generating.Please wait finished it."
            }
            return message
        elif (Item['stock_state'] == 'inservice'):
            message = {
                "status": 409,
                "name": "website already running",
                "message": "site id:" + query['siteId'] + " is already running"
            }
            return message
        message = {
            "status": 200
        }
        return message

    def __createNewService(self, query):
        SiteItem = False
        dynamodb = DynamoDB(self.app_config)
        SiteItem = dynamodb.getServiceById(query['siteId'])
        result = self.__canCreateNewService(SiteItem, query)
        if (result['status'] > 400):
            return result
        query['pubPort'] = self.__getPortNum()
        body = self.__getCreateImageBody(query)
        body_json = self.__convertToJson(body)

        self.docker_session.headers.update({'X-Registry-Auth': self.__getXRegistryAuth()})
        self.docker_session.headers.update({'Content-Type': 'application/json'})

        res = self.docker_session.post(
                self.dockerapi_config['endpoint'] + 'services/create',
                data=body_json,
                timeout=self.timeout_opts
              )
        logger.info(res.status_code)
        if res.ok:
            result = res.json()
        else:
            res.raise_for_status()

        if (query["action"] == 'createNewService'):
            message = self.__createNewServiceInfo(query, result)
            self.__saveToDynamoDB(message)
            return message
        elif (query["action"] == 'syncEfsToS3'):
            message = {
                'status': 200,
                'message': "service " + self.sessionid + ' started',
                'serviceName': self.sessionid
            }
            if 'ID' in result:
                message['serviceId'] = result['ID']
            return message

    def __deleteServiceHookDynamo(self, siteId):
        dynamo = DynamoDB(self.app_config)
        dynamo.resetSiteItem(siteId)
        return None

    def __getSyncEfsToS3ImageBody(self, query):
        builder = ServiceBuilder(self.app_config, query)
        service_spec = builder.buildServiceDef('sync-efs-to-s3')
        return service_spec

    def __getWpServiceImageBody(self, query):
        builder = ServiceBuilder(self.app_config, query)
        service_spec = builder.buildServiceDef('wordpress-worker')
        return service_spec
