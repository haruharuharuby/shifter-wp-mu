# -*- coding: utf-8 -*-
'''
Test DockerCtr Class
'''

import requests
from unittest.mock import Mock
from unittest.mock import patch
import yaml
from ..DockerCtr import DockerCtr
from ..ServiceBuilder import ServiceBuilder

app_config = yaml.load(open('./config/appconfig.yml', 'r'))['development']
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
    "stock_state": "ready"
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
    '''
    Pass to syncS3ToS3, return s3tos3 service_spec
    '''
    ServiceBuilder._ServiceBuilder__loadServiceTemplate = Mock(return_value=(open('./service_specs/sync-s3-to-s3.yml', 'r').read()))

    query = {
        "siteId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "sessionid": "5d5a3d8d-b578-9da9-2126-4bdc13fcaccd",
        "action": "syncS3ToS3",
        "artifactId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd"
    }
    print(query)

    instance = DockerCtr(app_config, query)
    sessionid = instance.sessionid
    result = instance._DockerCtr__getCreateImageBody(query)
    print(result)
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
                    'S3_BUCKET_FROM=on.getshifter.io',
                    'S3_BUCKET_TO=to.getshifter.io',
                    'SITE_ID=5d5a3d8c-b578-9da9-2126-4bdc13fcaccd',
                    'SERVICE_NAME=' + str(sessionid),
                    'CF_DIST_ID=E2XDOVHUH57BXZ',
                    'ARTIFACT_ID=5d5a3d8c-b578-9da9-2126-4bdc13fcaccd',
                    'SNS_TOPIC_ARN=arn:aws:sns:us-east-1:027273742350:site-gen-sync-s3-finished-development'
                ],
                'Image': '027273742350.dkr.ecr.us-east-1.amazonaws.com/docker-s3tos3:latest',
                'Mounts': [
                    {'Target': '/run', 'Type': 'tmpfs'},
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


@patch('time.sleep', lambda x: None)
def test__deleteNetworkIfExist():
    def side_effect_raise_exception():
        raise ValueError('this is test exception')

    ServiceBuilder._ServiceBuilder__loadServiceTemplate = Mock(return_value=(open('./service_specs/sync-s3-to-s3.yml', 'r').read()))
    query = {
        "siteId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "sessionid": "5d5a3d8d-b578-9da9-2126-4bdc13fcaccd",
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
