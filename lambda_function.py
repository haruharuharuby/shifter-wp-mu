from __future__ import print_function
import urllib
import urllib2
import json
import logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

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
            result = ctr.deleteTheService( event )
        elif ( event["action"] == "createNewService" ):
            if not 'pubPort' in event:
                raise Exception( "params 'pubPort' not found." )
            if not 'fsId' in event:
                raise Exception( "params 'fsId' not found.")
            result = ctr.createNewService( event )
        else:
            raise Exception( event["action"] + 'is unregistered action type' )
    return result

class DockerCtr:

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
        request.add_header('Content-Type', 'application/json')

        if method != 'GET' :
            request.get_method = lambda: method

        try:
            res = urllib2.urlopen( request )
            return res
        except urllib2.URLError, e:
            return e

    def __getCreateImageBody( self, query ):
        body = {
                "Name": query['siteId'],
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

    def getTheService( self, param ):
        endpoint = self.__getEndpoint()
        url = endpoint + 'services/' + param['siteId']
        res = self.__connect( url )
        read = json.loads( res.read() )
        return read

    def getServices( self ):
        endpoint = self.__getEndpoint()
        url = endpoint + 'services'
        res = self.__connect( url )
        read = json.loads( res.read() )
        return read

    def createNewService( self, query ):
        endpoint = self.__getEndpoint()
        url = endpoint + 'services/create'
        body = self.__getCreateImageBody( query )
        body_json = self.__convertToJson( body )
        res = self.__connect( url, 'POST', body_json )
        read = res.read()
        return json.loads( read )

    def deleteTheService( self, param ):
        endpoint = self.__getEndpoint()
        url = endpoint + 'services/' + param['siteId']
        res = self.__connect( url, 'DELETE' )
        read = res.read()
        return read
