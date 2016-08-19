#!/usr/bin/env python
# -*- coding: utf-8 -*-
import urllib
import urllib2
import json

class DockerCtr:

    def __getPortLimit(self):
        return 95

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

    def getTheService( self,service_name ):
        res = self.__getTheService( service_name )
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

    def __createNewService( self, query ):
        endpoint = self.__getEndpoint()
        url = endpoint + 'services/create'
        body = self.__getCreateImageBody( query )
        body_json = self.__convertToJson( body )
        res = self.__connect( url, 'POST', body_json )
        return res

    def createNewService( self, query ):
        if ( self.__isAvailablePortNum() ):
            res = self.__createNewService( query )
            read = res.read()
            return json.loads( read )
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
        return read


siteId = 'site0021'
param = {
  'siteId': siteId,
  'pubPort': '30021',
  'fsId': "fs-88d311c1"
}
print param
ctr = DockerCtr()
#print ctr.getServices()
#print ctr.getTheService('global-dd-agent')
print ctr.createNewService( param )
#print ctr.getTheService(siteId)
#print ctr.deleteTheService(siteId)
#print ctr.getTheService(siteId)
