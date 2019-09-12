# -*- coding: utf-8 -*-
'''
Test DockerCtr Class
'''

import boto3
import requests
from unittest.mock import Mock
from unittest.mock import patch
import yaml
from ..DockerCtr import DockerCtr
from ..ServiceBuilder import ServiceBuilder

boto3.client.decrypt = Mock(return_value='test_pass')

app_config = yaml.safe_load(open('./config/appconfig.yml', 'r'))['development']
test_event_base = {
    "siteId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
    "sessionid": "5d5a3d8d-b578-9da9-2126-4bdc13fcaccd"
}

test_site_item = {
    "access_url": "tender-ride7316.on.getshifter.io",
    "cf_id": "E2XDOVHUH57BXZ",
    "cf_url": "dw5aj9smo4km0.cloudfront.net",
    "cname_status": "ready",
    "efs_id": "fs-2308c16a",
    "ID": "c48db543-c3d0-27eb-9598-e6c33a2afdb7",
    "s3_bucket": "to.getshifter.io",
    "s3_region": "to-us-east-1",
    "site_name": "null",
    "site_owner": "null",
    "stock_state": "ready",
    "user_database": {
        "role": "test_role",
        "enc_passwd": "test_pass",
        "endpoint": "test.rdbendpoint"
    }
}

ServiceBuilder._ServiceBuilder__fetchDynamoSiteItem = Mock(return_value=test_site_item)


class DummyResponse():
    def __init__(self, status_code=200):
        self.status_code = status_code


def test_DockerCtr():
    '''
    Constructor just store arguments to instance variables.
    '''
    result = DockerCtr(app_config, test_event_base)
    print(result)
    assert result


def test__getCreateImageBody():
    from aws_xray_sdk.core import xray_recorder
    xray_recorder.begin_segment('test__getCreateImageBody')

    '''
    Pass to createArtifact, return s3tos3 service_spec
    '''
    ServiceBuilder._ServiceBuilder__loadServiceTemplate = Mock(return_value=(open('./service_specs/sync-s3-to-s3.yml', 'r').read()))

    query = {
        "siteId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "action": "createArtifact",
        "artifactId": "aaaaaaaa-b578-9da9-2126-4bdc13fcaccd"
    }

    instance = DockerCtr(app_config, query)
    sessionid = instance.sessionid
    result = instance._DockerCtr__getCreateImageBody(query)
    assert result == {
        'Labels': {'Name': 'sync-s3-to-s3'},
        'Networks': [{'Target': 'shifter_net_user'}],
        'Name': str(sessionid),
        'TaskTemplate': {
            'ContainerSpec': {
                'Env': [
                    'AWS_ACCESS_KEY_ID=AKIAIXELICZZAPYVYELA',
                    'AWS_SECRET_ACCESS_KEY=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',
                    'S3_REGION=us-east-1',
                    'S3_FROM=on.getshifter.io/5d5a3d8c-b578-9da9-2126-4bdc13fcaccd',
                    'S3_TO=artifact.getshifter.io/aaaaaaaa-b578-9da9-2126-4bdc13fcaccd',
                    'SERVICE_NAME=' + str(sessionid),
                    'SNS_TOPIC_ARN=arn:aws:sns:us-east-1:027273742350:site-gen-sync-s3-finished-development'
                ],
                'Image': '027273742350.dkr.ecr.us-east-1.amazonaws.com/docker-s3tos3:latest',
                'Mounts': [
                    {'Target': '/tmp', 'Type': 'tmpfs'}
                ]
            },
            'LogDriver': {
                'Name': 'awslogs', 'Options': {
                    'awslogs-group': 'dockerlog-services-development',
                    'awslogs-region': 'us-east-1',
                    'awslogs-stream': '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd-s3tos3'
                }
            },
            'Placement': {
                'Constraints': [
                    'node.labels.type == efs-worker'
                ]
            },
            'RestartPolicy': {
                'Condition': 'on-failure', 'Delay': 5000, 'MaxAttempts': 3
            }
        }
    }

    '''
    Pass to createNewService2 and editing wordpless. return wordpress-worker2 service_spec
    '''
    ServiceBuilder._ServiceBuilder__loadServiceTemplate = Mock(return_value=(open('./service_specs/wordpress-worker2.yml', 'r').read()))
    org_build_context_wordpress_worker2 = ServiceBuilder.build_context_wordpress_worker2
    ServiceBuilder.build_context_wordpress_worker2 = Mock(return_value='true')
    query = {
        "siteId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "action": "createNewService2",
        "serviceType": "edit-wordpress"
    }
    instance = DockerCtr(app_config, query)
    sessionid = instance.sessionid
    result = instance._DockerCtr__getCreateImageBody(query)
    print(result)
    assert result == {
        'EndpointSpec': {'Ports': [{'Protocol': 'tcp', 'PublishedPort': None, 'TargetPort': 443}]},
        'Labels': {'Name': 'wordpress-worker2', 'Service': None},
        'Networks': [{'Target': 'shifter_net_user-'}],
        'Name': None,
        'TaskTemplate': {
            'ContainerSpec': {
                'Env': ['DUMMY_ENV=True'],
                'Image': None,
                'Mounts': [
                    {'Source': None, 'Target': '/var/www/html/web/wp/wp-content', 'Type': 'volume', 'VolumeOptions': {'DriverConfig': {'Name': 'efs'}}},
                    {'Target': '/tmp', 'Type': 'tmpfs'},
                    {'Target': '/var/www/html/upgrade', 'Type': 'tmpfs'}
                ]
            },
            'LogDriver': {
                'Name': 'awslogs',
                'Options': {'awslogs-group': 'dockerlog-services-development', 'awslogs-region': 'us-east-1', 'awslogs-stream': None}
            },
            'Placement': {'Constraints': ['node.labels.type == efs-worker']}
        }
    }
    ServiceBuilder.build_context_wordpress_worker2 = org_build_context_wordpress_worker2
    xray_recorder.end_segment()


def test__buildInfoByAction():
    '''
    This is test to make response from query.
    '''

    '''
    createArtifact action
    '''
    query = {
        "siteId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "action": "createArtifact",
    }
    instance = DockerCtr(app_config, query)
    result = instance._DockerCtr__buildInfoByAction(query)
    sessionid = instance.sessionid
    expect = {
        "message": ("service %s started" % (sessionid)),
        "serviceName": str(sessionid)
    }
    assert result == expect

    '''
    createNewService2 action. Service Type does not specfied. stock_state won't generate.
    '''
    query = {
        "siteId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "action": "createNewService2",
        "pubPort": 12345
    }
    instance = DockerCtr(app_config, query)
    instance._DockerCtr__saveToDynamoDB = Mock(return_value=True)
    result = instance._DockerCtr__buildInfoByAction(query)
    sessionid = instance.sessionid

    expect = {
        "message": "service 5d5a3d8c-b578-9da9-2126-4bdc13fcaccd started",
        "docker_url": "https://5d5a3d8c-b578-9da9-2126-4bdc13fcaccd.appdev.getshifter.io:12345",
        'notificationId': str(sessionid),
        'serviceName': '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd'
    }
    assert result == expect

    '''
    createNewService2 action. Service Type specfied. stock_state will generate(ingenerate).
    '''
    query = {
        "siteId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "action": "createNewService2",
        "serviceType": 'generator',
        "pubPort": 12345
    }
    instance = DockerCtr(app_config, query)
    instance._DockerCtr__saveToDynamoDB = Mock(return_value=True)
    result = instance._DockerCtr__buildInfoByAction(query)
    sessionid = instance.sessionid

    expect = {
        "message": "service 5d5a3d8c-b578-9da9-2126-4bdc13fcaccd started",
        "docker_url": "https://5d5a3d8c-b578-9da9-2126-4bdc13fcaccd.appdev.getshifter.io:12345",
        'notificationId': str(sessionid),
        'serviceName': '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd',
        'stock_state': 'ingenerate'
    }
    assert result == expect

    '''
    createNewService2 action. Service Type 'edit-wordpress'. stock_state will generate(inservice).
    '''
    query = {
        "siteId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "action": "createNewService2",
        "serviceType": 'edit-wordpress',
        "pubPort": 12345
    }
    instance = DockerCtr(app_config, query)
    instance._DockerCtr__saveToDynamoDB = Mock(return_value=True)
    result = instance._DockerCtr__buildInfoByAction(query)
    sessionid = instance.sessionid

    expect = {
        "message": "service 5d5a3d8c-b578-9da9-2126-4bdc13fcaccd started",
        "docker_url": "https://5d5a3d8c-b578-9da9-2126-4bdc13fcaccd.appdev.getshifter.io:12345",
        'notificationId': str(sessionid),
        'serviceName': '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd',
        'stock_state': 'inservice'
    }
    assert result == expect


@patch('time.sleep', lambda x: None)
def test__deleteNetworkIfExist():
    def side_effect_raise_exception():
        raise ValueError('this is test exception')

    from aws_xray_sdk.core import xray_recorder
    xray_recorder.begin_segment('test__deleteNetworkIfExist')
    ServiceBuilder._ServiceBuilder__loadServiceTemplate = Mock(return_value=(open('./service_specs/sync-s3-to-s3.yml', 'r').read()))
    query = {
        "siteId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "action": "deleteServiceByServiceId",
        "serviceId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd"
    }

    '''
    No retry if removing docker_session succeeded(204).
    '''
    svc = {'status': 200, 'DockerUrl': "test:12345"}
    print(query)
    instance = DockerCtr(app_config, query)
    instance.docker_session.delete = Mock(return_value=DummyResponse(204))
    result = instance._DockerCtr__deleteNetworkIfExist(svc)
    print(result)
    assert result.status_code == 204

    '''
    Retry default(3) times per 2 sec. when removing docker_session is failed by not 200.
    '''
    svc = {'status': 200, 'DockerUrl': "test:12345"}
    print(query)
    instance = DockerCtr(app_config, query)
    instance.docker_session.delete = Mock(return_value=DummyResponse(403))
    result = instance._DockerCtr__deleteNetworkIfExist(svc)
    print(result)
    assert result.status_code != 204

    '''
    Retry default(3) times per 2 sec. when removing docker_session is failed by exception.
    '''
    svc = {'status': 200, 'DockerUrl': "test:12345"}
    print(query)
    instance = DockerCtr(app_config, query)
    instance.docker_session.delete = Mock(side_effect=side_effect_raise_exception)
    result = instance._DockerCtr__deleteNetworkIfExist(svc)
    print(result)
    assert not result

    '''
    Retry 4 times per 2 sec. when removing docker_session is failed by exception.
    '''
    svc = {'status': 200, 'DockerUrl': "test:12345"}
    print(query)
    instance = DockerCtr(app_config, query)
    instance.docker_session.delete = Mock(side_effect=side_effect_raise_exception)
    result = instance._DockerCtr__deleteNetworkIfExist(svc, trial=4)
    print(result)
    assert not result

    xray_recorder.end_segment()


import pytest


# WorkAround for hangup
@pytest.yield_fixture('session', autouse=True)
def fix_xray_threads():
    # TODO: This should be removed after https://github.com/aws/aws-xray-sdk-python/issues/26 is solved
    yield
    import ctypes
    import threading
    main_thread = threading.main_thread()
    for thread in threading.enumerate():
        if thread.daemon or thread == main_thread:
            continue

        ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(thread.ident), ctypes.py_object(SystemExit))
