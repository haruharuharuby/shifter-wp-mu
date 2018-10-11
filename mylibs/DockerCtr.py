#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import time
import base64
import random
import uuid
import logging
import boto3
import botocore
import requests
import pystache
import traceback
from .ShifterExceptions import *
from .DynamoDB import *
from .ServiceBuilder import *
from .ResponseBuilder import *
from .S3 import *
from aws_xray_sdk.core import xray_recorder

import rollbar

rollbar.init(os.getenv("ROLLBAR_TOKEN"), os.getenv("SHIFTER_ENV", "development"))
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

    PORTLESS_ACTIONS = [
        'syncEfsToS3',
        'deletePublicContents',
        'digSiteDirs',
        'createArtifact',
        'restoreArtifact'
    ]

    def __init__(self, app_config, event):
        self.event = event
        self.svcs = []
        self.app_config = app_config
        self.sessionid = uuid.uuid4().hex
        self.event['sessionid'] = self.sessionid
        # http://docs.python-requests.org/en/master/user/advanced/#timeouts
        self.timeout_opts = (5.0, 15.0)
        self.notificationId = self.sessionid
        self.docker_session = DockerSession(app_config['dockerapi'])

    """ RAW APIs"""
    def getServices(self):
        # return cached list (安定してるようなら毎回とっても良い)
        if len(self.svcs) > 0:
            return self.svcs
        res = self.docker_session.get('services')
        result = res.json()
        self.svcs = result
        return result

    """ Wrapped APIs"""
    def getTheService(self, siteId):
        res = self.docker_session.get('services/' + siteId)
        result = res.json()

        if (self.__hasDockerPublishedPort(result)):
            port = str(result['Endpoint']['Spec']['Ports'][0]['PublishedPort'])
            result['DockerUrl'] = 'https://' + siteId + '.' + self.app_config['service_domain'] + ':' + port

        if (self.__hasDockerLabel(result)):
            result['Labels'] = result['Spec']['Labels']

        # screen Docker response
        for x in ['Spec', 'Endpoint', 'Version', 'ID']:
            try:
                del result[x]
            except KeyError:
                continue

        return ResponseBuilder.buildResponse(
                name=siteId,
                status=res.status_code,
                logs_to=None,
                **result
        )

    def createNewService(self):
        if self.event['action'] not in DockerCtr.PORTLESS_ACTIONS:
            if not (self.__isAvailablePortNum()):
                raise ShifterNoAvaliPorts(exit_code=400, info='available port not found.')

        res = self.__createNewService(self.event)
        return res

    def __deleteNetworkIfExist(self, svc, trial=3):
        res = None
        if 'DockerUrl' in svc:
            port = svc['DockerUrl'].split(':')[-1]
            for times in range(trial):
                try:
                    res = self.docker_session.delete_port(port)
                    if res.status_code == 204:
                        break
                except Exception as e:
                    logger.error("Error occurred during builds Service definition: " + str(type(e)))
                    logger.error(traceback.format_exc())
                time.sleep(2.0)

            if not res or res.status_code != 204:
                rollbar.report_exc_info()

        # ここでエラーがでてもとりあえず無視してよい
        return res

    def deleteTheService(self, siteId):
        """ 専用OverlayNetWorkを削除するため、まずGetする """
        has_network = False
        svc = self.getTheService(siteId)
        if svc['status'] == 404:
            return ResponseBuilder.buildResponse(
                    status=404,
                    message="service: " + siteId + " not found.",
                    serviceId=siteId,
                    logs_to=None
            )
        elif svc['status'] == 200:
            has_network = True
        else:
            raise ShifterUnknownError

        """ 404 のレスポンスはほぼ無加工でOKだけど一応Wrap """
        res = self.docker_session.delete('services/' + siteId)
        if res.ok:
            message = "service: " + siteId + " is deleted."
            if has_network:
                # サービスのダウンがネットワーク削除に間に合わない場合、500で終わる
                time.sleep(0.1)
                self.__deleteNetworkIfExist(svc)
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

    def bulkDelete(self):
        query = self.event
        del_svcs = []
        nf_svcs = []
        err_svcs = []

        for sId in query['serviceIds']:
            try:
                res = self.deleteTheService(sId)
                if res['status'] == 200:
                    del_svcs.append(sId)
                elif res['status'] == 404:
                    nf_svcs.append(sId)
                else:
                    err_svcs.append(sId)
            except:
                err_svcs.append(sId)
                continue

        return ResponseBuilder.buildResponse(
                status=200,
                logs_to=query['serviceIds'],
                deleted=del_svcs,
                notfound=nf_svcs,
                error=err_svcs
        )

    """ Priveate Methods"""
    def __getXRegistryAuth(self):
        try:
            ecr = boto3.client('ecr')
            res = ecr.get_authorization_token()
            raw_token = res['authorizationData'][0]['authorizationToken']
            usertoken = base64.b64decode(raw_token).decode().split(':')
            jsondata = {}
            jsondata['username'] = usertoken[0]
            jsondata['password'] = usertoken[1]
            jsondata['email'] = 'none'
            auth_string = base64.b64encode(json.dumps(jsondata).encode('utf-8')).decode()
        except:
            auth_string = 'failed_to_get_token'
        return auth_string

    def __createNewService(self, query):
        dynamodb = DynamoDB(self.app_config)

        if 'siteId' in query:
            SiteItem = dynamodb.getServiceById(query['siteId'])
            if query['action'] not in DockerCtr.PORTLESS_ACTIONS:
                self.__checkStockStatus(SiteItem, query)
                query['pubPort'] = self.__getPortNum()

        body = self.__getCreateImageBody(query)
        logger.info(body)

        self.docker_session.update_header(self.__getXRegistryAuth())
        # 混戦を避けるため、専用のoverlayネットワークを作成する
        if 'pubPort' in query:
            logger.info('create specific network for service')
            # とりあえず消す、レスポンスは200か404になる
            self.docker_session.delete_port(query['pubPort'])
            # その後作る
            res = self.docker_session.create_network(self.__buildServiceNetworkfromTemplate(query))

        res = self.docker_session.create(body)
        res.raise_for_status()

        info = self.__buildInfoByAction(query)

        return ResponseBuilder.buildResponse(
                status=res.status_code,
                logs_to=query,
                **info
        )

    def __getServiceStateByType(self, sv_type):
        if sv_type == 'generator':
            return 'ingenerate'
        elif sv_type == 'edit-wordpress':
            return 'inservice'
        elif sv_type == 'create-archive':
            return 'intasks'
        elif sv_type == 'deploy-external':
            return 'indeployment'
        elif sv_type == 'import-archive':
            return 'inimport'

        return 'inuse'

    def __buildServiceNetworkfromTemplate(self, query):
        net_template_base = open('./network_specs/shifter_net_user.yml', 'r').read()
        net_spec_rendered = pystache.render(net_template_base, {"publish_port1": query['pubPort']})
        net_spec_base = yaml.load(net_spec_rendered)
        if 'SHIFTER_ENV' in os.environ.keys():
            net_spec = net_spec_base[os.environ['SHIFTER_ENV']]
        else:
            net_spec = net_spec_base['dev']

        logger.info(net_spec)
        return net_spec

    def __getCreateImageBody(self, query):
        query['notificationId'] = self.notificationId
        builder = ServiceBuilder(self.app_config, query)

        if query["action"] in ['syncEfsToS3', 'deletePublicContents', 'deleteArtifact']:
            service_spec = builder.buildServiceDef('sync-efs-to-s3')
        elif query["action"] in ['createArtifact', 'restoreArtifact']:
            service_spec = builder.buildServiceDef('sync-s3-to-s3')
        elif (query["action"] == 'createNewService2'):
            service_spec = builder.buildServiceDef('wordpress-worker2')
        elif (query["action"] == 'digSiteDirs'):
            service_spec = builder.buildServiceDef('docker-efs-dig-dirs')
        return service_spec

    def __buildInfoByAction(self, query):
        if query["action"] in ['createNewService', 'createNewService2']:
            info = {
                'docker_url': 'https://' + query['siteId'] + '.' + self.app_config['service_domain'] + ':' + str(query['pubPort']),
                'serviceName': query['siteId'],
                'message': "service " + query['siteId'] + ' started',
                'notificationId': self.notificationId
            }
            if 'serviceType' in query:
                stock_state = self.__getServiceStateByType(query['serviceType'])
                info['stock_state'] = stock_state

            self.__saveToDynamoDB(info)
        elif query["action"] in ['syncEfsToS3', 'deletePublicContents', 'createArtifact', 'restoreArtifact']:
            info = {
                'message': "service " + self.sessionid + ' started',
                'serviceName': self.sessionid
            }
        else:
            info = {}

        return info

    def __getPortNum(self):
        ports = self.__listUsedPorts()
        # 10回とって、それでもポートが被ったらraise
        for _ in range(10):
            num = random.randint(20000, 60000)
            if num not in ports:
                break
        else:
            raise ShifterConfrictPublishPorts(exit_code=409, info='Error, can not assign published port. Please retry later.')

        return num

    def __listUsedPorts(self):
        services = self.getServices()
        svcs = [x for x in services if self.__hasDockerPublishedPort(x)]
        ports = map(lambda x: x['Endpoint']['Ports'][0]['PublishedPort'], svcs)
        return list(ports)

    def __countRunningService(self):
        services = self.getServices()
        return len([x for x in services if self.__hasDockerPublishedPort(x)])

    def __isAvailablePortNum(self):
        portNum = self.__countRunningService()
        portLimit = self.app_config['limits']['max_ports']
        return portNum < portLimit

    def __hasDockerPublishedPort(self, docker):
        if 'Endpoint' in docker:
            if 'Spec' in docker['Endpoint']:
                if 'Ports' in docker['Endpoint']['Spec']:
                    if 'PublishedPort' in docker['Endpoint']['Spec']['Ports'][0]:
                        return True
        return False

    def __hasDockerLabel(self, docker):
        if 'Spec' in docker:
            if 'Labels' in docker['Spec']:
                return True
        return False

    def __checkStockStatus(self, Item, query):
        if Item['stock_state'] == 'ingenerate':
            raise ShifterConfrictNewService(
                exit_code=409,
                info="site id:" + query['siteId'] + " is now generating.Please wait finished it."
            )
        elif Item['stock_state'] == 'inservice':
            raise ShifterConfrictNewService(
                exit_code=409,
                info="site id:" + query['siteId'] + " is already running"
            )

        return None

    def __saveToDynamoDB(self, message):
        dynamo = DynamoDB(self.app_config)
        dynamo.updateSiteState(message)

    def __deleteServiceHookDynamo(self, siteId):
        dynamo = DynamoDB(self.app_config)
        dynamo.resetSiteItem(siteId)
        return None


class DockerSession:
    '''
    Request to Docker API.
    Trace activities on X-Ray
    '''
    def __init__(self, config):
        self.config = config
        self.session = self.buildDockerSession()
        self.timeout_opts = (5.0, 15.0)

    def buildDockerSession(self):
        session = requests.Session()
        session.auth = (self.config['authuser'], self.config['authpass'])
        session.mount("http://", requests.adapters.HTTPAdapter(max_retries=3))
        session.mount("https://", requests.adapters.HTTPAdapter(max_retries=3))
        return session

    @xray_recorder.capture('DockerSession_get')
    def get(self, path):
        res = self.session.get(self.config['endpoint'] + path, timeout=self.timeout_opts)
        logger.info(res.status_code)
        return res

    @xray_recorder.capture('DockerSession_delete_port')
    def delete_port(self, port):
        logger.info("deleting network for " + str(port))
        res = self.delete('networks/shifter_net_user-' + str(port))
        logger.info(res.status_code)
        return res

    @xray_recorder.capture('DockerSession_delete')
    def delete(self, path):
        res = self.session.delete(self.config['endpoint'] + path, timeout=self.timeout_opts)
        logger.info(res.status_code)
        return res

    def update_header(self, authentication_header):
        self.session.headers.update({'X-Registry-Auth': authentication_header})
        self.session.headers.update({'Content-Type': 'application/json'})

    @xray_recorder.capture('DockerSession_create_network')
    def create_network(self, body):
        res = self.session.post(self.config['endpoint'] + 'networks/create', json=body, timeout=self.timeout_opts)
        logger.info(res.status_code)
        return res

    @xray_recorder.capture('DockerSession_create')
    def create(self, body):
        res = self.session.post(self.config['endpoint'] + 'services/create', json=body, timeout=self.timeout_opts)
        logger.info(res.status_code)
        return res
