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
from DynamoDB import *
from S3 import *

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class DockerCtr:

    def __init__(self, app_config):
        self.app_config = app_config
        self.dockerapi_config = app_config['dockerapi']
        self.uuid = ''
        self.docker_session = buildDockerSession()
        self.notificationId = uuid.uuid4().hex

    def buildDockerSession(self):
        session = requests.Session()
        session.auth = (dockerapi_config['authuser'], dockerapi_config['authpass'])
        return session

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

    def __getImage(self, imageType, phpVersion='7.0'):
        if imageType == 'wordpress-worker':
            return '027273742350.dkr.ecr.us-east-1.amazonaws.com/docker-php-with-mysql:' + phpVersion
        elif imageType == 'sync-efs-to-s3':
            return '027273742350.dkr.ecr.us-east-1.amazonaws.com/docker-s3sync:latest'

    def __convertToJson(self, param):
        return json.dumps(param)

    def __getPortNum(self):
        num = random.randint(10000, 30000)
        return num

    def __connect(self, url, method='GET', body=None):
        password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
        password_mgr.add_password(None, url, self.dockerapi_config['authuser'], self.dockerapi_config['authpass'])
        handler = urllib2.HTTPBasicAuthHandler(password_mgr)
        opener = urllib2.build_opener(handler)
        urllib2.install_opener(opener)

        if body is None:
            request = urllib2.Request(url)
        else:
            request = urllib2.Request(url, body)
            request.add_header('X-Registry-Auth', self.__getXRegistryAuth())
        request.add_header('Content-Type', 'application/json')

        if method != 'GET':
            request.get_method = lambda: method

        try:
            res = urllib2.urlopen(request)
            return res
        except urllib2.URLError, e:
            return e

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

    def __getSyncEfsToS3ImageBody(self, query):
        self.uuid = uuid.uuid4().hex
        dynamodb = DynamoDB()
        dbData = dynamodb.getServiceById(query['siteId'])
        dbItem = False
        if 'Items' in dbData:
            if (dbData['Count'] > 0):
                dbItem = dbData['Items'][0]
        if dbItem is False:
            dbItem = {
                's3_bucket': {'S': ''},
                's3_region': {'S': ''},
            }

        body = {
                "Name": self.uuid,
                "Labels": {
                    "Name": "sync-efs-to-s3"
                },
                "TaskTemplate": {
                    "RestartPolicy": {
                        "Condition": "on-failure",
                        "Delay": 5000,
                        "MaxAttempts": 3,
                    },
                    "ContainerSpec": {
                        "Image": self.__getImage('sync-efs-to-s3'),
                        "Env": [
                            "AWS_ACCESS_KEY_ID=" + self.app_config['awscreds']['access_key'],
                            "AWS_SECRET_ACCESS_KEY=" + self.app_config['awscreds']['secret_access_key'],
                            "S3_REGION=" + dbItem['s3_region']['S'],
                            "S3_BUCKET=" + dbItem['s3_bucket']['S'],
                            "SITE_ID=" + query['siteId'],
                            "SERVICE_NAME=" + self.uuid
                        ],
                        "Mounts": [{
                            "Type": "volume",
                            "Target": "/opt/efs/",
                            "Source": query['fsId'] + "/" + query['siteId'],
                            "VolumeOptions": {
                                "DriverConfig": {
                                    "Name": "efs"
                                }
                            }
                        }]
                    },
                    "Placement": {
                        "Constraints": ["node.labels.type == efs-worker"]
                    },
                }
            }
        return body

    def __getWpServiceImageBody(self, query):
        if 'phpVersion' not in query:
            query['phpVersion'] = '7.0'
        s3 = S3(self.app_config)
        notification_url = s3.createNotificationUrl(self.notificationId)
        env = [
            "SERVICE_PORT=" + str(query['pubPort']),
            "SITE_ID=" + query['siteId'],
            "SERVICE_DOMAIN=" + self.app_config['service_domain'],
            "EFS_ID=" + query['fsId'],
            "NOTIFICATION_URL=" + base64.b64encode(notification_url)
        ]
        if 'wpArchiveId' in query:
            archiveUrl = s3.createWpArchiceUrl(query['wpArchiveId'])
            if archiveUrl is not False:
                env.append('ARCHIVE_URL=' + base64.b64encode(archiveUrl))
        body = {
                "Name": query['siteId'],
                "Labels": {
                    "Name": "wordpress-worker"
                },
                "TaskTemplate": {
                    "LogDriver": {
                        "Name": "awslogs",
                        "Options": {
                            "awslogs-region": "us-east-1",
                            "awslogs-group": "dockerlog-services",
                            "awslogs-stream": query['siteId']
                        }
                    },
                    "ContainerSpec": {
                        "Image": self.__getImage('wordpress-worker', query['phpVersion']),
                        "Env": env,
                        "Mounts": [{
                            "Type": "volume",
                            "Target": "/var/www/html",
                            "Source": query['fsId'] + "/" + query['siteId'] + "/web",
                            "VolumeOptions": {
                                "DriverConfig": {
                                    "Name": "efs"
                                }
                            }
                        },
                        {
                            "Type": "volume",
                            "Target": "/var/lib/mysql",
                            "Source": query['fsId'] + "/" + query['siteId'] + "/db",
                            "VolumeOptions": {
                                "DriverConfig": {
                                    "Name": "efs"
                                }
                            }
                        }]
                    },
                    "Placement": {
                        "Constraints": ["node.labels.type == efs-worker"]
                    },
                },
                "EndpointSpec": {
                    "Ports": [
                        {
                            "Protocol": "tcp",
                            "PublishedPort": int(query['pubPort']),
                            "TargetPort": 443
                        }
                    ]
                }
        }
        return body

    def getTheService(self, siteId):
        try:
            res = docker_session.get(dockerapi_config['endpoint'] + 'services/' + siteId)
            result = res.json()
            result['status'] = res.status_code
        except:
            logger.error("JSON ValueError " + body)
            return createBadRequestMessage(event, event["action"] + 'is unregistered action type')

        if (self.__hasDockerPublishedPort(result)):
            port = str(read['Endpoint']['Spec']['Ports'][0]['PublishedPort'])
            result['DockerUrl'] = 'https://' + app_config['service_domain'] + ':' + port
        return result

    def __hasDockerPublishedPort(self, docker):
        if 'Endpoint' in docker:
            if 'Spec' in docker['Endpoint']:
                if 'Ports' in docker['Endpoint']['Spec']:
                    if 'PublishedPort' in docker['Endpoint']['Spec']['Ports'][0]:
                        return True
        return False

    def __getServices(self):
        url = self.dockerapi_config['endpoint'] + 'services'
        res = self.__connect(url)
        return res

    def getServices(self):
        res = self.__getServices()
        read = json.loads(res.read())
        return read

    def __createNewServiceInfo(self, query, res):
        message = {
            'status': 200,
            'docker_url': 'https://' + self.app_config['service_domain'] + ':' + str(query['pubPort']),
            'serviceName': query['siteId'],
            'notificationId': self.notificationId
        }
        read = res.read()
        result = json.loads(read)
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
        dynamo = DynamoDB()
        dynamo.updateItem(message)

    def __canCreateNewService(self, dbData, query):
        if (dbData['Count'] > 0):
            if (dbData['Items'][0]['stock_state']['S'] == 'ingenerate'):
                message = {
                    "status": 409,
                    "name": "website now generating",
                    "message": "site id:" + query['siteId'] + " is now generating.Please wait finished it."
                }
                return message
            elif (dbData['Items'][0]['stock_state']['S'] == 'inservice'):
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
        dbData = False
        if (query["action"] == 'createNewService'):
            dynamodb = DynamoDB()
            dbData = dynamodb.getServiceById(query['siteId'])
            result = self.__canCreateNewService(dbData, query)
            if (result['status'] > 400):
                return result
        url = self.dockerapi_config['endpoint'] + 'services/create'
        query['pubPort'] = self.__getPortNum()
        body = self.__getCreateImageBody(query)
        body_json = self.__convertToJson(body)
        res = self.__connect(url, 'POST', body_json)
        if isinstance(res, urllib2.URLError):
            return res
        elif (query["action"] == 'createNewService'):
            message = self.__createNewServiceInfo(query, res)
            self.__saveToDynamoDB(message)
            return message
        elif (query["action"] == 'syncEfsToS3'):
            message = {
                'status': 200,
                'message': "service " + self.uuid + ' started',
                'serviceName': self.uuid
            }
            read = res.read()
            result = json.loads(read)
            if 'ID' in result:
                message['serviceId'] = result['ID']
            return message

    def createNewService(self, query):
        if (self.__isAvailablePortNum()):
            res = self.__createNewService(query)
            if isinstance(res, urllib2.URLError):
                read = res.read()
                result = json.loads(read)
                result['status'] = 500
                result['siteId'] = query['siteId']
                return result
            else:
                return res
        else:
            error = {
                'status': 400,
                'message': 'available port not found.',
                'siteId': query['siteId']
            }
            return error

    def __deleteTheService(self, siteId):
        url = self.dockerapi_config['endpoint'] + 'services/' + siteId
        res = self.__connect(url, 'DELETE')
        return res

    def deleteTheService(self, siteId):
        res = self.__deleteTheService(siteId)
        read = res.read()
        dynamo = DynamoDB()
        dynamo.deleteWpadminUrl(siteId)
        if (read == ""):
            result = {
                "serviceId": siteId,
                "status": 200,
                "message": "service: " + siteId + " is deleted."
            }
        else:
            read = json.loads(read)
            result = {
                "serviceId": siteId,
                "status": 500,
                "message": read['message']
            }
        return result

    def deleteServiceByServiceId(self, query):
        url = dockerapi_config['endpoint'] + 'services/' + query['serviceId']
        res = self.__connect(url, 'DELETE')
        read = res.read()
        dynamo = DynamoDB()
        dynamo.deleteWpadminUrl(query['siteId'])
        if (read == ""):
            result = {
                "serviceId": query['serviceId'],
                "status": 200,
                "message": "service: " + query['serviceId'] + "is deleted."
            }
        else:
            read = json.loads(read)
            result = {
                "serviceId": query['serviceId'],
                "status": 500,
                "message": read['message']
            }
        return result
