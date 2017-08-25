# -*- coding: utf-8 -*-
'''
Testing ServiceBuilder Class
'''

from unittest.mock import Mock
import yaml
from ..ServiceBuilder import ServiceBuilder

app_config = yaml.load(open('../config/appconfig.yml', 'r'))['development']


def test_ServiceBuilder():
    '''
    Test constructor
    '''

    ServiceBuilder._ServiceBuilder__fetchDynamoSiteItem = Mock()

    '''
    SiteId specified. site_item attribute generates.
    '''
    query = {
        "siteId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "action": "syncS3ToS3",
        "serviceType": "syncS3ToS3"
    }
    result = ServiceBuilder(app_config, query)
    print(result)
    assert result
    assert result.site_item

    '''
    SiteID doesn't specified. site_item attribute doesn't generates.
    '''
    query = {
        "action": "syncS3ToS3",
        "serviceType": "syncS3ToS3"
    }
    result = ServiceBuilder(app_config, query)
    print(result)
    assert result
    assert not hasattr(result, 'site_item')

    '''
    Invalid action specified. it doesn't raise any error.
    '''
    query = {
        "siteId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "action": "invalidAction",
        "serviceType": "syncS3ToS3"
    }
    result = ServiceBuilder(app_config, query)
    print(result)
    assert result
    assert result.site_item


def test_build_context_sync_efs_to_s3():
    '''
    Test building context of syhcrhonizing from efs to s3
    '''

    test_site_item = {
        "access_url": "tender-ride7316.on.getshifter.io",
        "cf_id": "E2XDOVHUH57BXZ",
        "cf_url": "dw5aj9smo4km0.cloudfront.net",
        "cname_status": "ready",
        "efs_id": "fs-2308c16a",
        "ID": "c48db543-c3d0-27eb-9598-e6c33a2afdb7",
        "s3_bucket": "on.getshifter.io",
        "s3_region": "us-east-1",
        "site_name": "null",
        "site_owner": "null",
        "stock_state": "ready"
    }
    ServiceBuilder._ServiceBuilder__fetchDynamoSiteItem = Mock(return_value=test_site_item)

    query = {
        "siteId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "action": "syncEfsToS3",
        "serviceType": "syncS3ToS3",
        "sessionid": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd"
    }
    instance = ServiceBuilder(app_config, query)
    context = instance.build_context_sync_efs_to_s3()
    print(context)
    assert context


def test_build_context_sync_s3_to_s3():
    '''
    Test building context of syhcrhonizing from s3 to s3
    '''
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

    '''
    image_tag not specfied, it generates context for using latest image.
    '''
    query = {
        "siteId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "action": "syncS3ToS3",
        "sessionid": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "s3_bucket": "from.getshifter.io",
    }

    instance = ServiceBuilder(app_config, query)
    context = instance.build_context_sync_s3_to_s3()
    assert context
    assert context == {
        'service_name': '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd',
        'service_id': '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd',
        'image_string': '027273742350.dkr.ecr.us-east-1.amazonaws.com/docker-s3tos3:latest',
        'envvars': [
            {'envvar': 'AWS_ACCESS_KEY_ID=AKIAIXELICZZAPYVYELA'},
            {'envvar': 'AWS_SECRET_ACCESS_KEY=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'},
            {'envvar': 'S3_REGION=us-east-1'},
            {'envvar': 'S3_BUCKET_FROM=from.getshifter.io'},
            {'envvar': 'S3_BUCKET_TO=to.getshifter.io'},
            {'envvar': 'SITE_ID=5d5a3d8c-b578-9da9-2126-4bdc13fcaccd'},
            {'envvar': 'SERVICE_NAME=5d5a3d8c-b578-9da9-2126-4bdc13fcaccd'},
            {'envvar': 'CF_DIST_ID=E2XDOVHUH57BXZ'},
            {'envvar': 'SNS_TOPIC_ARN=arn:aws:sns:us-east-1:027273742350:site-gen-sync-s3-finished-development'}
        ]
    }

    '''
    Image_tag specfied, it generates context for using specfied image.
    '''
    query = {
        "siteId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "action": "syncS3ToS3",
        "sessionid": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "s3_bucket": "from.getshifter.io",
        "image_tag": "specified-image"
    }

    instance = ServiceBuilder(app_config, query)
    context = instance.build_context_sync_s3_to_s3()
    assert context
    assert context == {
        'service_name': '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd',
        'service_id': '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd',
        'image_string': '027273742350.dkr.ecr.us-east-1.amazonaws.com/docker-s3tos3:specified-image',
        'envvars': [
            {'envvar': 'AWS_ACCESS_KEY_ID=AKIAIXELICZZAPYVYELA'},
            {'envvar': 'AWS_SECRET_ACCESS_KEY=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'},
            {'envvar': 'S3_REGION=us-east-1'},
            {'envvar': 'S3_BUCKET_FROM=from.getshifter.io'},
            {'envvar': 'S3_BUCKET_TO=to.getshifter.io'},
            {'envvar': 'SITE_ID=5d5a3d8c-b578-9da9-2126-4bdc13fcaccd'},
            {'envvar': 'SERVICE_NAME=5d5a3d8c-b578-9da9-2126-4bdc13fcaccd'},
            {'envvar': 'CF_DIST_ID=E2XDOVHUH57BXZ'},
            {'envvar': 'SNS_TOPIC_ARN=arn:aws:sns:us-east-1:027273742350:site-gen-sync-s3-finished-development'}
        ]
    }