from __future__ import print_function
import urllib
import urllib2
import json
import base64
import random
import uuid
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
#logger.setLevel(logging.DEBUG)
import boto3
import botocore


print('Loading function')
def lambda_handler(event, context):
    if not 'action' in event:
        return createBadRequestMessage( event, "params 'action' not found." )

    ctr = DockerCtr()
    if ( event["action"] == "test" ):
       return test( event )

    if ( event["action"] == "getAllServices" ):
        result = ctr.getServices()
    else:
        if not 'siteId' in event:
            return createBadRequestMessage( event, "params 'siteId' not found." )
        if ( event["action"] == "getTheService" ):
            result = ctr.getTheService(event['siteId'])
        elif ( event["action"] == "deleteTheService" ):
            result = ctr.deleteTheService(event['siteId'])
        elif ( event["action"] == "createNewService" ):
            if not 'fsId' in event:
                return createBadRequestMessage( event, "params 'fsId' not found.")
            #if not 'serviceType' in event:
                #raise Exception( "params 'serviceType' not found.")
            result = ctr.createNewService( event )
        elif ( event["action"] == 'syncEfsToS3' ):
            if not 'fsId' in event:
                return createBadRequestMessage( event, "params 'fsId' not found.")
            result = ctr.createNewService( event )
        elif ( event["action"] == 'deleteServiceByServiceId' ):
            if not 'serviceId' in event:
                return createBadRequestMessage( event, "params 'serviceId' not found.")
            result = ctr.deleteServiceByServiceId( event )
        else:
            return createBadRequestMessage( event, event["action"] + 'is unregistered action type' )
    return result

def test( event ):
    return 'this is test'

def createBadRequestMessage( event, error_text ):
    message = {
        "status": 400,
        "message": error_text,
        "request": event
    }
    logger.warning( message )
    return message

class DynamoDB:
    def __init__(self):
        self.client = boto3.client('dynamodb')

    def __getSiteTableName(self):
        return 'Site'

    def getServiceById(self,serviceName):
        res = self.client.scan(
            TableName=self.__getSiteTableName(),
            FilterExpression="ID = :id",
            ExpressionAttributeValues={
                ':id': { 'S': serviceName }
            }
         )
        return res

    def deleteWpadminUrl(self, serviceName ):
        res = self.client.update_item(
            TableName=self.__getSiteTableName(),
            Key={
                'ID': { 'S': serviceName}
            },
            UpdateExpression='SET docker_url=:docker_url,stock_state=:stock_state',
            ExpressionAttributeValues={
                ':docker_url': { 'NULL': True },
                ':stock_state': { 'S': 'inuse' }
            }
        )
        return res

    def updateItem(self, message ):
        res = self.client.update_item(
            TableName=self.__getSiteTableName(),
            Key={
                'ID': { 'S': message['serviceName']}
            },
            UpdateExpression='SET docker_url=:docker_url,stock_state=:stock_state',
            ExpressionAttributeValues={
                ':docker_url': { 'S': message['docker_url'] },
                ':stock_state': { 'S': message['stock_state'] }
            }
        )
        return res

class DockerCtr:

    def __init__(self):
        self.uuid = ''
        self.notificationId = uuid.uuid4().hex

    def __getServiceDomain(self):
        return 'app.getshifter.io';

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
        return 'http://app.getshifter.io:8080/'

    def __getTLSEndpoint(self):
        return 'https://app.getshifter.io:8443/'

    def __getAwsSecret4S3(self):
        return 'HpKRfy361drDQ9n7zf1/PL9HDRf424LGB6Rs34/8'

    def __getAwsAccess4S3(self):
        return 'AKIAIXELICZZAPYVYELA'

    def __getS3BucketNameForSync(self):
        return 'generator-s3-sync'

    def __getImage( self, imageType, phpVersion = '7.0' ):
        if imageType == 'wordpress-worker':
            #return '027273742350.dkr.ecr.us-east-1.amazonaws.com/docker-wordpressadmin001:latest'
            return '027273742350.dkr.ecr.us-east-1.amazonaws.com/docker-php-with-mysql:' + phpVersion
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
            if 'serviceType' in query:
                body['Labels']['Service'] = query['serviceType']
                #if ( query['serviceType'] == 'generator' ):
            else:
                body['Labels']['Service'] = 'edit-wordpress'
                query['serviceType'] = 'edit-wordpress'
        return body

    def __getSyncEfsToS3ImageBody( self, query ):
        self.uuid = uuid.uuid4().hex
        dynamodb = DynamoDB()
        dbData = dynamodb.getServiceById( query['siteId'] )
        dbItem = False
        if 'Items' in dbData:
            if ( dbData['Count'] > 0 ):
                dbItem = dbData['Items'][0]
        if ( dbItem == False ):
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
                            "AWS_ACCESS_KEY_ID=" + self.__getAwsAccess4S3(),
                            "AWS_SECRET_ACCESS_KEY=" + self.__getAwsSecret4S3(),
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

    def __getWpServiceImageBody( self, query ):
        if not 'phpVersion' in query:
            query['phpVersion'] = '7.0'
        s3 = S3()
        notification_url = s3.createNotificationUrl( self.notificationId )
        env = [
            "SERVICE_PORT=" + str( query['pubPort'] ),
            "SITE_ID=" + query['siteId'],
            "SERVICE_DOMAIN=" + self.__getServiceDomain(),
            "EFS_ID=" + query['fsId'],
            "NOTIFICATION_URL=" + base64.b64encode( notification_url )
        ]
        if 'wpArchiveId' in query:
            archiveUrl = s3.createWpArchiceUrl( query['wpArchiveId'] )
            if ( archiveUrl != False ):
                env.append( 'ARCHIVE_URL=' + base64.b64encode( archiveUrl ) )
        body = {
                "Name": query['siteId'],
                "Labels": {
                    "Name": "wordpress-worker"
                },
                "TaskTemplate": {
                    "ContainerSpec": {
                        "Image": self.__getImage('wordpress-worker', query['phpVersion'] ),
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
                            "PublishedPort": int( query['pubPort'] ),
                            "TargetPort": 443
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
        endpoint = self.__getEndpoint()
        res = self.__getTheService( siteId )
        read = json.loads( res.read() )
        if 'message' in read:
            read['status'] = 500
        else:
            read['status'] = 200
        if ( self.__hasDockerPublishedPort( read ) ):
            port = str( read['Endpoint']['Spec']['Ports'][0]['PublishedPort'] )
            read['DockerUrl'] = endpoint + port
        return read

    def __hasDockerPublishedPort( self, docker ):
        if 'Endpoint' in docker:
            if 'Spec' in docker['Endpoint']:
                if 'Ports' in docker['Endpoint']['Spec']:
                    if 'PublishedPort' in docker['Endpoint']['Spec']['Ports'][0]:
                        return True
        return False

    def __getServices( self ):
        endpoint = self.__getEndpoint()
        url = endpoint + 'services'
        res = self.__connect( url )
        return res

    def getServices( self ):
        res = self.__getServices()
        read = json.loads( res.read() )
        return read

    def __createNewServiceInfo( self, query, res ):
        endpoint = self.__getTLSEndpoint()
        message = {
            'status': 200,
            'docker_url': endpoint[:-5] + str( query['pubPort'] ),
            'serviceName': query['siteId'],
            'notificationId': self.notificationId
        }
        read = res.read()
        result = json.loads( read )
        if 'ID' in result:
            message['serviceId'] = result['ID']
        if 'serviceType' in query:
            if ( query['serviceType'] == 'generator' ):
                message['stock_state'] = 'ingenerate'
            elif ( query['serviceType'] == 'edit-wordpress' ):
                message['stock_state'] = 'inservice'
            else :
                message['stock_state'] = 'inuse'
        else :
            message['stock_state'] = 'inuse'
        return message

    def __saveToDynamoDB( self, message ):
        dynamo = DynamoDB()
        dynamo.updateItem( message )

    def __canCreateNewService( self, dbData, query ):
        if ( dbData['Count'] > 0 ):
            if ( dbData['Items'][0]['stock_state']['S'] == 'ingenerate' ):
                message = {
                    "status": 409,
                    "name": "website now generating",
                    "message": "site id:" + query['siteId'] + " is now generating.Please wait finished it."
                }
                return message
            elif ( dbData['Items'][0]['stock_state']['S'] == 'inservice' ):
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

    def __createNewService( self, query ):
        dbData = False
        if ( query["action"] == 'createNewService' ):
            dynamodb = DynamoDB()
            dbData = dynamodb.getServiceById( query['siteId'] )
            result = self.__canCreateNewService( dbData, query )
            if ( result['status'] > 400 ):
                return result
        endpoint = self.__getEndpoint()
        url = endpoint + 'services/create'
        query['pubPort'] = self.__getPortNum()
        body = self.__getCreateImageBody( query )
        body_json = self.__convertToJson( body )
        res = self.__connect( url, 'POST', body_json )
        if isinstance( res, urllib2.URLError) :
            return res
        elif ( query["action"] == 'createNewService' ):
            message = self.__createNewServiceInfo( query, res )
            self.__saveToDynamoDB( message )
            return message
        elif ( query["action"] == 'syncEfsToS3' ):
            message = {
                'status': 200,
                'message': "service " + self.uuid + ' started',
                'serviceName': self.uuid
            }
            read = res.read()
            result = json.loads( read )
            if 'ID' in result:
                message['serviceId'] = result['ID']
            return message

    def createNewService( self, query ):
        if ( self.__isAvailablePortNum() ):
            res = self.__createNewService( query )
            if isinstance( res, urllib2.URLError) :
                read = res.read()
                result = json.loads( read )
                result['status'] = 500
                result['siteId'] = query['siteId']
                return result
            else:
                return res
        else :
            error = {
                'status': 400,
                'message': 'available port not found.',
                'siteId': query['siteId']
            }
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
        if ( read == "" ):
            result = {
                "serviceId": siteId,
                "status": 200,
                "message": "service: " + siteId + " is deleted."
            }
        else:
            read = json.loads( read )
            result = {
                "serviceId": siteId,
                "status": 500,
                "message": read['message']
            }
        return result

    def deleteServiceByServiceId( self, query ):
        endpoint = self.__getEndpoint()
        url = endpoint + 'services/' + query['serviceId']
        res = self.__connect( url, 'DELETE' )
        read = res.read()
        dynamo = DynamoDB()
        dynamo.deleteWpadminUrl( query['siteId'] )
        if ( read == "" ):
            result = {
                "serviceId": query['serviceId'],
                "status": 200,
                "message": "service: " + query['serviceId'] + "is deleted."
            }
        else:
            read = json.loads( read )
            result = {
                "serviceId": query['serviceId'],
                "status": 500,
                "message": read['message']
            }
        return result


class S3:
    def __init__(self):
        self.client = boto3.client('s3')

    def __getWpArchiveBucketName(self):
        return 'wp-archives-files'

    def __getNotificationBucketname(self):
        return 'sys.status.getshifter'

    def __hasObject( self, key ):
        try:
            self.client.get_object(
                Bucket = self.__getWpArchiveBucketName(),
                Key = key
            )
            return True
        except botocore.exceptions.ClientError as e:
            logger.info(e)
            return False

    def createNotificationUrl( self, notificationId ):
        result = self.client.generate_presigned_url(
            ClientMethod = 'put_object',
            Params = {
                'Bucket': self.__getNotificationBucketname(),
                'Key': notificationId
            },
            ExpiresIn = 3600,
            HttpMethod = 'PUT'
        )
        return result

    def createWpArchiceUrl( self, wpArchiveId ):
        if ( self.__hasObject( wpArchiveId + '/wordpress.zip' ) ):
            result = self.client.generate_presigned_url(
                ClientMethod = 'get_object',
                Params = {
                    'Bucket': self.__getWpArchiveBucketName(),
                    'Key': wpArchiveId + '/wordpress.zip'
                },
                ExpiresIn = 3600,
                HttpMethod = 'GET'
            )
            return result
        else:
            return False
