from __future__ import print_function
import urllib
import urllib2
import json
import logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

print('Loading function')
def lambda_handler(event, context):
    ctr = DockerCtr()
    if ( event["action"] == "getAllServices" ):
        result = ctr.getServices()
    else:
        print("value1 = " + event['siteId'])
        print("value2 = " + event['pubPort'])
        has_vars( event )
        if ( event["action"] == "getTheService" ):
            result = ctr.getTheService(event['siteId'])
        elif ( event["action"] == "createNewService" ):
            result = ctr.createNewService( event['siteId'], event['pubPort'] )
        else:
            raise Exception( event["action"] + 'is unregistered action type' )
    return result

def has_vars( params ):
    if not 'siteId' in params:
        raise Exception( "params 'siteId' not found." )
    if not 'pubPort' in params:
        raise Exception( "params 'pubPort' not found." )
    if not 'action' in params:
        raise Exception( "params 'action' not found." )

class DockerCtr:

    def __getBasicAuthPass(self):
        return 'presspress'

    def __getBasicAuthUsername(self):
        return 'static'

    def __getEndpoint(self):
        return 'http://docker-rc1-custom1-elb-15225947.us-east-1.elb.amazonaws.com:8080/'

    def __getImage(self):
        return '905740997296.dkr.ecr.us-west-2.amazonaws.com/docker-wordpressadmin001:latest'

    def __getFsId(self):
        return 'fs-7a66a533'

    def __convertToJson( self, param ):
        return json.dumps( param )

    def __connect( self, url, method = 'GET', body = None ):
        password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
        password_mgr.add_password( None, url, self.__getBasicAuthUsername(), self.__getBasicAuthPass())
        handler = urllib2.HTTPBasicAuthHandler( password_mgr )
        opener = urllib2.build_opener( handler )
        urllib2.install_opener( opener )

        try:
            if body != None :
                logger.debug( body )
                logger.debug( url )
                res = urllib2.urlopen( url, body )
            else:
                res = urllib2.urlopen( url )
            return res
        except urllib2.URLError, e:
            return e

    def __getCreateImageBody( self,siteId, pubPort ):
        body = {
                "Name": siteId,
                "TaskTemplate": {
                    "ContainerSpec": {
                        "Image": self.__getImage(),
                        "Mounts": [{
                        "Type": "volume",
                        "Target": "/mnt/userdata",
                        "Source": self.__getFsId() + "/" + siteId,
                        "VolumeOptions": {
                            "DriverConfig": {
                            "Name": "efs"
                            }
                        }
                        }]
                    }
                },
                "EndpointSpec": {
                    "Ports": [
                        {
                            "Protocol": "tcp",
                            "PublishedPort": int( pubPort ),
                            "TargetPort": 8080
                        }
                    ]
                }
            }
        return body

    def getTheService( self,service_name ):
        endpoint = self.__getEndpoint()
        url = endpoint + 'services/' + service_name
        res = self.__connect( url )
        read = json.loads( res.read() )
        return read

    def getServices( self ):
        endpoint = self.__getEndpoint()
        url = endpoint + 'services'
        res = self.__connect( url )
        read = json.loads( res.read() )
        return read

    def createNewService( self,siteId, pubPort ):
        endpoint = self.__getEndpoint()
        url = endpoint + 'services/create'
        body = self.__getCreateImageBody( siteId, pubPort )
        body_json = self.__convertToJson( body )
        res = self.__connect( url, 'POST', body_json )
        read = res.read()
        return json.loads( read )

    def deleteTheService( self, siteId ):
        endpoint = self.__getEndpoint()
        url = endpoint + 'services'
        res = self.__connect( url, 'DELETE' )
        read = json.loads( res.read() )
        return read
