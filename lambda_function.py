from __future__ import print_function
import urllib
import urllib2
import json
import base64
import random
import uuid
import logging
#logger = logging.getLogger()
#logger.setLevel(logging.DEBUG)
import boto3


print('Loading function')
def lambda_handler(event, context):
    if not 'action' in event:
        raise Exception( "params 'action' not found." )

    ctr = DockerCtr()
    if ( event["action"] == "getAllServices" ):
        result = ctr.getServices()
    else:
        if not 'siteId' in event:
            raise Exception( "params 'siteId' not found." )
        if ( event["action"] == "getTheService" ):
            result = ctr.getTheService(event['siteId'])
        elif ( event["action"] == "deleteTheService" ):
            result = ctr.deleteTheService(event['siteId'])
        elif ( event["action"] == "createNewService" ):
            if not 'fsId' in event:
                raise Exception( "params 'fsId' not found.")
            result = ctr.createNewService( event )
        elif ( event["action"] == 'syncEfsToS3' ):
            if not 'fsId' in event:
                raise Exception( "params 'fsId' not found.")
            result = ctr.createNewService( event )
        else:
            raise Exception( event["action"] + 'is unregistered action type' )
    return result

class DynamoDB:
    def __init__(self):
        self.client = boto3.client('dynamodb')

    def __getSiteTableName(self):
        return 'Site'

    def deleteWpadminUrl(self, serviceName ):
        res = self.client.update_item(
            TableName=self.__getSiteTableName(),
            Key={
                'ID': { 'S': serviceName}
            },
            UpdateExpression='SET docker_url=:docker_url',
            ExpressionAttributeValues={
                ':docker_url': { 'NULL': True }
            }
        )
        return res

    def updateItem(self, docker_url, serviceName ):
        res = self.client.update_item(
            TableName=self.__getSiteTableName(),
            Key={
                'ID': { 'S': serviceName}
            },
            UpdateExpression='SET docker_url=:docker_url,stock_state=:stock_state',
            ExpressionAttributeValues={
                ':docker_url': { 'S': docker_url },
                ':stock_state': { 'S': 'inuse' }
            }
        )
        return res

class DockerCtr:

    def __init__(self):
        self.uuid = ''

    def __getServiceDomain(self):
        return 'app.sp.opsrockin.com';

    def __getPortLimit(self):
        return 95

    def __getXRegistryAuth(self):
        try:
            ecr = boto3.client('ecr')
            res = ecr.get_authorization_token()
            raw_token = res['authorizationData'][0]['authorizationToken']
            usertoken = base64.b64decode( raw_token ).split(':')
            jsondata = {}
            jsondata['username'] = usertoken[0]
            jsondata['password'] = usertoken[1]
            jsondata['email'] = 'none'
            auth_string = base64.b64encode(json.dumps(jsondata))
        except:
            auth_string = 'failed_to_get_token'
        return auth_string

    def __getBasicAuthPass(self):
        return 'presspress'

    def __getBasicAuthUsername(self):
        return 'static'

    def __getEndpoint(self):
        return 'http://app.sp.opsrockin.com:8080/'

    def __getAwsSecret4S3(self):
        return 'HpKRfy361drDQ9n7zf1/PL9HDRf424LGB6Rs34/8'

    def __getAwsAccess4S3(self):
        return 'AKIAIXELICZZAPYVYELA'

    def __getS3BucketNameForSync(self):
        return 'generator-s3-sync'

    def __getImage(self,imageType ):
        if imageType == 'wordpress-worker':
            return '027273742350.dkr.ecr.us-east-1.amazonaws.com/docker-wordpressadmin001:latest'
        elif imageType == 'sync-efs-to-s3':
            return '027273742350.dkr.ecr.us-east-1.amazonaws.com/docker-s3sync:latest'

    def __convertToJson( self, param ):
        return json.dumps( param )

    def __getPortNum( self ):
        num = random.randint( 10000,30000 )
        return num

    def __connect( self, url, method = 'GET', body = None ):
        password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
        password_mgr.add_password( None, url, self.__getBasicAuthUsername(), self.__getBasicAuthPass())
        handler = urllib2.HTTPBasicAuthHandler( password_mgr )
        opener = urllib2.build_opener( handler )
        urllib2.install_opener( opener )

        if body == None :
            request = urllib2.Request( url )
        else :
            request = urllib2.Request( url, body )
            request.add_header( 'X-Registry-Auth', self.__getXRegistryAuth() )
        request.add_header('Content-Type', 'application/json')

        if method != 'GET' :
            request.get_method = lambda: method

        try:
            res = urllib2.urlopen( request )
            return res
        except urllib2.URLError, e:
            return e

    def __countRunningService( self ):
        services = self.getServices()
        return len(services)

    def __isAvailablePortNum( self ):
        portNum = self.__countRunningService()
        portLimit = self.__getPortLimit()
        if ( portNum > portLimit ):
            return False
        else :
            return True

    def __getCreateImageBody( self, query ):
        if ( query["action"] == 'syncEfsToS3' ):
            body = self.__getSyncEfsToS3ImageBody( query )
        elif ( query["action"] == 'createNewService' ):
            body = self.__getWpServiceImageBody( query )
        return body

    def __getSyncEfsToS3ImageBody( self, query ):
        self.uuid = uuid.uuid4().hex
        body = {
                "Name": self.uuid,
                "Labels": {
                    "Name": "sync-efs-to-s3"
                },
                "TaskTemplate": {
                    "RestartPolicy": {
                        "Condition": "on-failure",
                        "Delay": 5,
                        "Attempts": 3,
                    },
                    "ContainerSpec": {
                        "Image": self.__getImage('sync-efs-to-s3'),
                        "Env": [
                            "AWS_ACCESS_KEY_ID=" + self.__getAwsAccess4S3(),
                            "AWS_SECRET_ACCESS_KEY=" + self.__getAwsSecret4S3(),
                            "SITE_ID=" + query['siteId'],
                            "SERVICE_NAME=" + self.uuid
                        ],
                        "Mounts": [{
                            "Type": "volume",
                            "Target": "/opt/efs/",
                            "Source": query['fsId'] + "/" + query['siteId'] + "/web",
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

    def __getWpServiceImageBody( self, query ):
        body = {
                "Name": query['siteId'],
                "Labels": {
                    "Name": "wordpress-worker"
                },
                "TaskTemplate": {
                    "ContainerSpec": {
                        "Image": self.__getImage('wordpress-worker'),
                        "Env": [
                            "SERVICE_PORT=" + str( query['pubPort'] ),
                            "SITE_ID=" + query['siteId'],
                            "SERVICE_DOMAIN=" + self.__getServiceDomain(),
                            "EFS_ID=" + query['fsId']
                        ],
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
                            "PublishedPort": int( query['pubPort'] ),
                            "TargetPort": 8080
                        }
                    ]
                }
            }
        return body


    def __getTheService( self,service_name ):
        endpoint = self.__getEndpoint()
        url = endpoint + 'services/' + service_name
        res = self.__connect( url )
        return res

    def getTheService( self,siteId ):
        res = self.__getTheService( siteId )
        read = json.loads( res.read() )
        return read

    def __getServices( self ):
        endpoint = self.__getEndpoint()
        url = endpoint + 'services'
        res = self.__connect( url )
        return res

    def getServices( self ):
        res = self.__getServices()
        read = json.loads( res.read() )
        return read

    def __createNewServiceInfo( self, query ):
        endpoint = self.__getEndpoint()
        message = {
            'docker_url': endpoint[:-5] + str( query['pubPort'] ),
            'serviceName': query['siteId']
        }
        return message

    def __saveToDynamoDB( self, message ):
        dynamo = DynamoDB()
        dynamo.updateItem( message['docker_url'], message['serviceName'] )

    def __createNewService( self, query ):
        endpoint = self.__getEndpoint()
        url = endpoint + 'services/create'
        query['pubPort'] = self.__getPortNum()
        body = self.__getCreateImageBody( query )
        body_json = self.__convertToJson( body )
        res = self.__connect( url, 'POST', body_json )
        if isinstance( res, urllib2.URLError) :
            return res
        elif ( query["action"] == 'createNewService' ):
            message = self.__createNewServiceInfo( query )
            self.__saveToDynamoDB( message )
            return message
        elif ( query["action"] == 'syncEfsToS3' ):
            message = self.uuid
            return message

    def createNewService( self, query ):
        if ( self.__isAvailablePortNum() ):
            res = self.__createNewService( query )
            if isinstance( res, urllib2.URLError) :
                read = res.read()
                return json.loads( read )
            else:
                return res
        else :
            error = { 'message': 'available port not found.'}
            return error

    def __deleteTheService( self, siteId ):
        endpoint = self.__getEndpoint()
        url = endpoint + 'services/' + siteId
        res = self.__connect( url, 'DELETE' )
        return res

    def deleteTheService( self, siteId ):
        res = self.__deleteTheService( siteId )
        read = res.read()
        dynamo = DynamoDB()
        dynamo.deleteWpadminUrl( siteId )
        return read
