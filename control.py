#!/usr/bin/env python
# -*- coding: utf-8 -*-
import urllib
import urllib2
import json

class DockerCtr:
    #def __init__(self):

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
        req = urllib2.Request( url )
        print method
        req.get__method = lambda: method

        try:
            if body != None :
                print body
                print url
                res = urllib2.urlopen( req, body )
            else:
                res = urllib2.urlopen( req )
            return res
        except urllib2.URLError, e:
            return e

    def __getCreateImageBody( self,siteId, pubPort ):
        body = {
                "Name": siteId,
                "TaskTemplate": {
                    "ContainerSpec": {
                        "Image": self.__getImage(),
                        "Args": ["--with-registry-auth"],
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
                            "PublishedPort": pubPort,
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
        return json.loads( res.read() )

    def deleteTheService( self, siteId ):
        endpoint = self.__getEndpoint()
        url = endpoint + 'services'
        res = self.__connect( url, 'DELETE' )
        read = json.loads( res.read() )
        return read



siteId = 'site0009'
pubPort = 30020
ctr = DockerCtr()
#print ctr.getServices()
#print ctr.getTheService('global-dd-agent')
print ctr.createNewService( siteId, pubPort )
#print ctr.deleteTheService(siteId)
#print ctr.getTheService(siteId)
