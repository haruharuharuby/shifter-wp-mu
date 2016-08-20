from __future__ import print_function
import urllib
import urllib2
import json
import random
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
                ':docker_url ': { 'NULL': True }
            }
        )
        return res

    def updateItem(self, docker_url, serviceName ):
        res = self.client.update_item(
            TableName=self.__getSiteTableName(),
            Key={
                'ID': { 'S': serviceName}
            },
            UpdateExpression='SET docker_url=:docker_url',
            ExpressionAttributeValues={
                ':docker_url': { 'S': docker_url }
            }
        )
        return res

class DockerCtr:

    def __getPortLimit(self):
        return 95

    def __getXRegistryAuth(self):
        return "IHsKICJ1c2VybmFtZSI6ICJBV1MiLAogInBhc3N3b3JkIjogIkFRRUNBSGh3bTBZYUlTSmVSdEptNW4xRzZ1cWVla1h1b1hYUGU1VUZjZTlScTgvMTR3QUFBdkV3Z2dMdEJna3Foa2lHOXcwQkJ3YWdnZ0xlTUlJQzJnSUJBRENDQXRNR0NTcUdTSWIzRFFFSEFUQWVCZ2xnaGtnQlpRTUVBUzR3RVFRTWZ3eEhSSTVHQ1I3OHZNZmNBZ0VRZ0lJQ3BGaERuTWpLRzg0UXVmY2NmNmlQa09UZW9pd1VieE9UU1FqMEF1NDJRVjlINDYzZmlCWkppMExxTUcrUUt4dGQyMy9rTzExM1FTRXRwOFpIR2xKQ2M1UE1raUNTR0ZBUkxUa0VTU292cTNOVDNVRm8ranBZUDAzUEZ2NFVwQ2FXOGVvK3dKOU0yaENMckxYQkJNUFNuYU1jc2pkYUpPMVNmYU12OTlKaWp1RmVtOHFpaWp2bTE1ZjR2VDJveFExQjAvVUhmTDBoK21sSHphM1V3OFpVT2R3K00za2xidXBUVkV2dFhuZzd2UlNHZnozMHZuakVnVFRkWHBoOFhqV1pMK2pJK2F4WTRmNVVOOE5Ha2RQaUtFVVd6bmtwSVJWSWlLdVltNHJiRDlPMEZ0V0NMNXhrNk1WcThVQlZDQU1UL21iRDlWWjJjbXZHeGgwSDJzSG5wb0NuSXdMRUQ0U0o1MDgwWVUra1JQN1drS2E2SW55dE92aG5NN2Nock5uTExsS2JHSkYxWk1HTUJCOGZySFhoeVJIUjZGbDRDNEhKU0tDZkRBQ3FEYWhKOUp6QjcxN1FnTmU1RTdnT1RhcVJXNDVvbGtVZ2xRMmdZV2dnVG51YXdMRnpOcGo5Qkk5aElQcnl3VXFydlQreGYwOTNReWV1ZWxnT1I0WmhLMy9GYS92QUR4cHEzVU9lU2FyQ3hTWFVsdUdIb0hLT2FrZEpCTFJtOTQ1T2VhV1RIcUFlT3ZXY2VMWVRKT0JDcjM2ckNkQndQWFhVMHRvRkRaQWVFbmIyellIVS9iMVJFZjgxQ2xRV3pPNjlzWVhrSlNBaG1JVVFqdWdCczdxRDJrSWxWZ0krVlcyWnpwSks1QWVwR1JKYjlOOENKM3VnNnRLY2hyemdseERQclFQVXpHUVI5NUpqQnBFUzRQQXFISHd3dUUydTNucWpQakRCZDlaUUNlMHRNdEhObnlqcFJIb2pCSC9OZjdDYkJuVlhnK2p0TFlRaDNTTzFyb0thbFJsdDlTNmo2UEVzYkxneVNDU0dxeCs5TWhNaVZBMk02UFdkd0NjVHVCeHJ0czFueC94b0dIMVl1ZWdmaE5jQ3FiOXhuSlh1amtsME5wQit4aG1kYkk0dk80dFZmUjVjMnArRlh2MDR1c2FDdm9nU3NRcW5aNC9FV01pSDZRNTVmN2M2dHJ5UzNKSSIsCiAiZW1haWwiOiAibm9uZSIsCn0K"

    def __getBasicAuthPass(self):
        return 'presspress'

    def __getBasicAuthUsername(self):
        return 'static'

    def __getEndpoint(self):
        return 'http://app.sp.opsrockin.com:8080/'

    def __getImage(self):
        return '027273742350.dkr.ecr.us-east-1.amazonaws.com/docker-wordpressadmin001:latest'

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
        body = {
                "Name": query['siteId'],
                "Labels": {
                    "Name": "wordpress-worker"
                },
                "TaskTemplate": {
                    "ContainerSpec": {
                        "Image": self.__getImage(),
                        "Mounts": [{
                        "Type": "volume",
                        "Target": "/mnt/userdata",
                        "Source": query['fsId'] + "/" + query['siteId'],
                        "VolumeOptions": {
                            "DriverConfig": {
                            "Name": "efs"
                            }
                        }
                        }]
                    },
                    "Placement": {
                        "Constraints": ["node.role == worker"]
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
        else:
            message = self.__createNewServiceInfo( query )
            self.__saveToDynamoDB( message )
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
