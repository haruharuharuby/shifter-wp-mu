# -*- coding: utf-8 -*-
'''
Testing ServiceBuilder Class
'''

import os
import pytest
from unittest.mock import Mock
import yaml
from ..ServiceBuilder import ServiceBuilder
from ..ShifterExceptions import *

app_config = yaml.load(open('./config/appconfig.yml', 'r'))['development']


def test_ServiceBuilder():
    from aws_xray_sdk.core import xray_recorder
    xray_recorder.begin_segment('test_ServiceBuilder')

    '''
    Test constructor
    '''

    ServiceBuilder._ServiceBuilder__fetchDynamoSiteItem = Mock()

    '''
    SiteId specified. site_item attribute generates.
    '''
    query = {
        "siteId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "action": "createArtifact",
        "artifactId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd"
    }
    result = ServiceBuilder(app_config, query)
    print(result)
    assert result
    assert result.site_item

    '''
    SiteID doesn't specified. site_item attribute doesn't generates.
    '''
    query = {
        "action": "createArtifact",
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
        "artifactId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd"
    }
    result = ServiceBuilder(app_config, query)
    print(result)
    assert result
    assert result.site_item

    xray_recorder.end_segment()


def test_build_context_sync_efs_to_s3():
    from aws_xray_sdk.core import xray_recorder
    xray_recorder.begin_segment('test_ServiceBuilder')

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
        "s3_bucket": "to.getshifter.io",
        "s3_region": "us-east-1",
        "site_name": "null",
        "site_owner": "null",
        "stock_state": "ready",
        "phpVersion": "7.0",
        "user_database": {
            "role": "test_role",
            "enc_passwd": "test_pass",
            "endpoint": "end"
        }

    }
    ServiceBuilder._ServiceBuilder__fetchDynamoSiteItem = Mock(return_value=test_site_item)

    '''
    Action syncEfsToS3.
    if artifact id specified, ARTIFACT_ID will generate in envvars.
    if pj_version does not spedfied, PJ_VERSION generate 1 in envvars.
    '''
    query = {
        "siteId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "action": "syncEfsToS3",
        "artifactId": "aaaaaaaa-b578-9da9-2126-4bdc13fcaccd",
        "sessionid": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd"
    }
    instance = ServiceBuilder(app_config, query)
    context = instance.build_context_sync_efs_to_s3()
    print(context)
    assert context == {
        'service_name': '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd',
        'service_id': '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd',
        'image_string': '027273742350.dkr.ecr.us-east-1.amazonaws.com/docker-s3sync:latest',
        'efs_point_root': 'fs-2308c16a/5d5a3d8c-b578-9da9-2126-4bdc13fcaccd',
        'envvars': [
            {'envvar': 'AWS_ACCESS_KEY_ID=AKIAIXELICZZAPYVYELA'},
            {'envvar': 'AWS_SECRET_ACCESS_KEY=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'},
            {'envvar': 'S3_REGION=us-east-1'},
            {'envvar': 'S3_BUCKET=artifact.getshifter.io'},
            {'envvar': 'SITE_ID=5d5a3d8c-b578-9da9-2126-4bdc13fcaccd'},
            {'envvar': 'SERVICE_NAME=5d5a3d8c-b578-9da9-2126-4bdc13fcaccd'},
            {'envvar': 'DYNAMODB_TABLE=Site-development'},
            {'envvar': 'ARTIFACT_ID=aaaaaaaa-b578-9da9-2126-4bdc13fcaccd'},
            {'envvar': 'SNS_TOPIC_ARN=arn:aws:sns:us-east-1:027273742350:site-gen-sync-s3-finished-development'},
            {'envvar': 'PJ_VERSION=1'},
        ]
    }

    '''
    Action syncEfsToS3.
    if artifact id specified, ARTIFACT_ID will generate in envvars.
    if pj_version does not spedfied, but exists in site_item version is used from site_item.
    '''
    query = {
        "siteId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "action": "syncEfsToS3",
        "artifactId": "aaaaaaaa-b578-9da9-2126-4bdc13fcaccd",
        "sessionid": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd"
    }
    test_site_item['version'] = "2"
    instance = ServiceBuilder(app_config, query)
    context = instance.build_context_sync_efs_to_s3()
    print(context)
    assert context == {
        'service_name': '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd',
        'service_id': '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd',
        'image_string': '027273742350.dkr.ecr.us-east-1.amazonaws.com/docker-s3sync:latest',
        'efs_point_root': 'fs-2308c16a/5d5a3d8c-b578-9da9-2126-4bdc13fcaccd',
        'envvars': [
            {'envvar': 'AWS_ACCESS_KEY_ID=AKIAIXELICZZAPYVYELA'},
            {'envvar': 'AWS_SECRET_ACCESS_KEY=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'},
            {'envvar': 'S3_REGION=us-east-1'},
            {'envvar': 'S3_BUCKET=artifact.getshifter.io'},
            {'envvar': 'SITE_ID=5d5a3d8c-b578-9da9-2126-4bdc13fcaccd'},
            {'envvar': 'SERVICE_NAME=5d5a3d8c-b578-9da9-2126-4bdc13fcaccd'},
            {'envvar': 'DYNAMODB_TABLE=Site-development'},
            {'envvar': 'ARTIFACT_ID=aaaaaaaa-b578-9da9-2126-4bdc13fcaccd'},
            {'envvar': 'SNS_TOPIC_ARN=arn:aws:sns:us-east-1:027273742350:site-gen-sync-s3-finished-development'},
            {'envvar': 'PJ_VERSION=2'},
        ]
    }
    test_site_item['version'] = ''

    '''
    Action syncEfsToS3.
    if artifact id specified, ARTIFACT_ID will generate in envvars.
    if SHIFTER_ENV==development specified, use develop as tag
    if pj_version does not spedfied, but exists in site_item version is used from site_item.
    '''
    query = {
        "siteId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "action": "syncEfsToS3",
        "artifactId": "aaaaaaaa-b578-9da9-2126-4bdc13fcaccd",
        "sessionid": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd"
    }
    test_site_item['version'] = "2"
    os.environ["SHIFTER_ENV"] = "development"
    instance = ServiceBuilder(app_config, query)
    context = instance.build_context_sync_efs_to_s3()
    print(context)
    assert context == {
        'service_name': '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd',
        'service_id': '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd',
        'image_string': '027273742350.dkr.ecr.us-east-1.amazonaws.com/docker-s3sync:develop',
        'efs_point_root': 'fs-2308c16a/5d5a3d8c-b578-9da9-2126-4bdc13fcaccd',
        'envvars': [
            {'envvar': 'AWS_ACCESS_KEY_ID=AKIAIXELICZZAPYVYELA'},
            {'envvar': 'AWS_SECRET_ACCESS_KEY=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'},
            {'envvar': 'S3_REGION=us-east-1'},
            {'envvar': 'S3_BUCKET=artifact.getshifter.io'},
            {'envvar': 'SITE_ID=5d5a3d8c-b578-9da9-2126-4bdc13fcaccd'},
            {'envvar': 'SERVICE_NAME=5d5a3d8c-b578-9da9-2126-4bdc13fcaccd'},
            {'envvar': 'DYNAMODB_TABLE=Site-development'},
            {'envvar': 'ARTIFACT_ID=aaaaaaaa-b578-9da9-2126-4bdc13fcaccd'},
            {'envvar': 'SNS_TOPIC_ARN=arn:aws:sns:us-east-1:027273742350:site-gen-sync-s3-finished-development'},
            {'envvar': 'PJ_VERSION=2'},
        ]
    }
    test_site_item['version'] = ''
    del os.environ["SHIFTER_ENV"]

    '''
    Action deletePublicContents.
    if artifact id does not specified, ARTIFACT_ID won't generate in envvars.
    if pj_version specified(and version in site_item exists), PJ_VERSION generate query's value in envvars.
    '''
    query = {
        "siteId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "action": "deletePublicContents",
        "sessionid": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "pjVersion": "2"
    }
    test_site_item['version'] = "1"
    instance = ServiceBuilder(app_config, query)
    context = instance.build_context_sync_efs_to_s3()
    assert context
    assert context == {
        'service_name': '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd',
        'service_id': '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd',
        'image_string': '027273742350.dkr.ecr.us-east-1.amazonaws.com/docker-s3sync:latest',
        'efs_point_root': 'fs-2308c16a/5d5a3d8c-b578-9da9-2126-4bdc13fcaccd',
        'envvars': [
            {'envvar': 'AWS_ACCESS_KEY_ID=AKIAIXELICZZAPYVYELA'},
            {'envvar': 'AWS_SECRET_ACCESS_KEY=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'},
            {'envvar': 'S3_REGION=us-east-1'},
            {'envvar': 'S3_BUCKET=on.getshifter.io'},
            {'envvar': 'SITE_ID=5d5a3d8c-b578-9da9-2126-4bdc13fcaccd'},
            {'envvar': 'SERVICE_NAME=5d5a3d8c-b578-9da9-2126-4bdc13fcaccd'},
            {'envvar': 'DYNAMODB_TABLE=Site-development'},
            {'envvar': 'DELETE_MODE=TRUE'},
            {'envvar': 'CF_DIST_ID=E2XDOVHUH57BXZ'},
            {'envvar': 'SNS_TOPIC_ARN=arn:aws:sns:us-east-1:027273742350:site-gen-sync-s3-finished-development'},
            {'envvar': 'PJ_VERSION=2'},
        ]
    }

    '''
    Action deleteArtifact. if artifact id does not specified, ARTIFACT_ID won't generate in envvars.
    if pj_version does not specified and version in site_item is empty, PJ_VERSION generate default(=1).
    '''
    query = {
        "siteId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "action": "deleteArtifact",
        "sessionid": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd"
    }
    instance = ServiceBuilder(app_config, query)
    test_site_item['version'] = ""
    context = instance.build_context_sync_efs_to_s3()
    assert context
    assert context == {
        'service_name': '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd',
        'service_id': '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd',
        'image_string': '027273742350.dkr.ecr.us-east-1.amazonaws.com/docker-s3sync:latest',
        'efs_point_root': 'fs-2308c16a/5d5a3d8c-b578-9da9-2126-4bdc13fcaccd',
        'envvars': [
            {'envvar': 'AWS_ACCESS_KEY_ID=AKIAIXELICZZAPYVYELA'},
            {'envvar': 'AWS_SECRET_ACCESS_KEY=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'},
            {'envvar': 'S3_REGION=us-east-1'},
            {'envvar': 'S3_BUCKET=artifact.getshifter.io'},
            {'envvar': 'SITE_ID=5d5a3d8c-b578-9da9-2126-4bdc13fcaccd'},
            {'envvar': 'SERVICE_NAME=5d5a3d8c-b578-9da9-2126-4bdc13fcaccd'},
            {'envvar': 'DYNAMODB_TABLE=Site-development'},
            {'envvar': 'DELETE_MODE=TRUE'},
            {'envvar': 'CF_DIST_ID=E2XDOVHUH57BXZ'},
            {'envvar': 'SNS_TOPIC_ARN=arn:aws:sns:us-east-1:027273742350:site-gen-sync-s3-finished-development'},
            {'envvar': 'PJ_VERSION=1'},
        ]
    }

    xray_recorder.end_segment()


def test_build_context_sync_s3_to_s3():
    from aws_xray_sdk.core import xray_recorder
    xray_recorder.begin_segment('test_ServiceBuilder')

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
        "s3_region": "us-east-1",
        "site_name": "null",
        "site_owner": "null",
        "stock_state": "ready",
        "phpVersion": "7.0",
        "user_database": {
            "role": "test_role",
            "enc_passwd": "test_pass",
            "endpoint": "end"
        }

    }
    ServiceBuilder._ServiceBuilder__fetchDynamoSiteItem = Mock(return_value=test_site_item)

    '''
    image_tag not specified, it generates context for using latest image.
    '''
    query = {
        "siteId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "action": "createArtifact",
        "sessionid": "5d5a3d8cb5789da921264bdc13fcaccd",
        "artifactId": "aaaaaaaa-b578-9da9-2126-4bdc13fcaccd",
    }

    instance = ServiceBuilder(app_config, query)
    context = instance.build_context_sync_s3_to_s3()
    assert context
    assert context == {
        'service_name': '5d5a3d8cb5789da921264bdc13fcaccd',
        'service_id': '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd',
        'image_string': '027273742350.dkr.ecr.us-east-1.amazonaws.com/docker-s3tos3:latest',
        'envvars': [
            {'envvar': 'AWS_ACCESS_KEY_ID=AKIAIXELICZZAPYVYELA'},
            {'envvar': 'AWS_SECRET_ACCESS_KEY=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'},
            {'envvar': 'S3_REGION=us-east-1'},
            {'envvar': 'S3_FROM=on.getshifter.io/5d5a3d8c-b578-9da9-2126-4bdc13fcaccd'},
            {'envvar': 'S3_TO=artifact.getshifter.io/aaaaaaaa-b578-9da9-2126-4bdc13fcaccd'},
            {'envvar': 'SERVICE_NAME=5d5a3d8cb5789da921264bdc13fcaccd'},
            {'envvar': 'SNS_TOPIC_ARN=arn:aws:sns:us-east-1:027273742350:site-gen-sync-s3-finished-development'}
        ]
    }

    '''
    image_tag not specified, it generates context for using latest image.
    '''
    query = {
        "siteId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "action": "restoreArtifact",
        "sessionid": "5d5a3d8cb5789da921264bdc13fcaccd",
        "artifactId": "aaaaaaaa-b578-9da9-2126-4bdc13fcaccd"
    }

    instance = ServiceBuilder(app_config, query)
    context = instance.build_context_sync_s3_to_s3()
    assert context
    assert context == {
        'service_name': '5d5a3d8cb5789da921264bdc13fcaccd',
        'service_id': '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd',
        'image_string': '027273742350.dkr.ecr.us-east-1.amazonaws.com/docker-s3tos3:latest',
        'envvars': [
            {'envvar': 'AWS_ACCESS_KEY_ID=AKIAIXELICZZAPYVYELA'},
            {'envvar': 'AWS_SECRET_ACCESS_KEY=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'},
            {'envvar': 'S3_REGION=us-east-1'},
            {'envvar': 'S3_FROM=artifact.getshifter.io/aaaaaaaa-b578-9da9-2126-4bdc13fcaccd'},
            {'envvar': 'S3_TO=on.getshifter.io/5d5a3d8c-b578-9da9-2126-4bdc13fcaccd'},
            {'envvar': 'SERVICE_NAME=5d5a3d8cb5789da921264bdc13fcaccd'},
            {'envvar': 'SNS_TOPIC_ARN=arn:aws:sns:us-east-1:027273742350:site-gen-sync-s3-finished-development'},
            {'envvar': 'CF_DIST_ID=E2XDOVHUH57BXZ'}
        ]
    }

    xray_recorder.end_segment()


def test_build_context_wordpress_worker2():
    from aws_xray_sdk.core import xray_recorder
    xray_recorder.begin_segment('test_ServiceBuilder')

    '''
    Test building context for wordpress worker2
    '''
    test_site_item = {
        "access_url": "tender-ride7316.on.getshifter.io",
        "cf_id": "E2XDOVHUH57BXZ",
        "cf_url": "dw5aj9smo4km0.cloudfront.net",
        "cname_status": "ready",
        "efs_id": "fs-2308c16a",
        "ID": "c48db543-c3d0-27eb-9598-e6c33a2afdb7",
        "s3_bucket": "to.getshifter.io",
        "s3_region": "us-east-1",
        "site_name": "null",
        "site_owner": "null",
        "stock_state": "ready",
        "domain": "test.shifterdomain",
        "phpVersion": "7.0",
        "user_database": {
            "role": "test_role",
            "enc_passwd": "test_pass",
            "endpoint": "test.rdbendpoint"
        }
    }

    def mock_instance(obj):
        obj.kms_client.decrypt = Mock(return_value={'Plaintext': b'test_pass'})
        obj.s3client.createNotificationUrl = Mock(return_value='test.notification_url')
        obj.s3client.createNotificationErrorUrl = Mock(return_value='test.notificationerror_url')

    ServiceBuilder._ServiceBuilder__fetchDynamoSiteItem = Mock(return_value=test_site_item)
    query = {
        "siteId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "action": "createNewService2",
        "sessionid": "5d5a3d8cb5789da921264bdc13fcaccd",
        "artifactId": "aaaaaaaa-b578-9da9-2126-4bdc13fcaccd",
        "pubPort": 12345,
        "notificationId": "5d5a3d8cb5789da921264bdc13fcaccd",
        "accessToken": "accesstoken",
        "refreshToken": "refreshtoken",
        "email": "email"
    }

    os.environ['SHIFTER_API_URL_V1'] = 'V1'
    os.environ['SHIFTER_API_URL_V2'] = 'V2'

    '''
    default context build.
    '''
    instance = ServiceBuilder(app_config, query)
    mock_instance(instance)
    context = instance.build_context_wordpress_worker2()
    assert context
    assert context == {
        'service_name': '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd',
        'service_type': 'edit-wordpress',
        'image_string': '027273742350.dkr.ecr.us-east-1.amazonaws.com/shifter-base:latest_develop',
        'publish_port1': 12345,
        'efs_point_web': 'fs-2308c16a/5d5a3d8c-b578-9da9-2126-4bdc13fcaccd/web',
        'envvars': [
            {'envvar': 'SERVICE_PORT=12345'},
            {'envvar': 'SERVICE_TYPE=edit-wordpress'},
            {'envvar': 'SITE_ID=5d5a3d8c-b578-9da9-2126-4bdc13fcaccd'},
            {'envvar': 'SERVICE_DOMAIN=appdev.getshifter.io'},
            {'envvar': 'NOTIFICATION_URL=dGVzdC5ub3RpZmljYXRpb25fdXJs'},
            {'envvar': 'NOTIFICATION_ERROR_URL=dGVzdC5ub3RpZmljYXRpb25lcnJvcl91cmw='},
            {'envvar': 'CF_DOMAIN=tender-ride7316.on.getshifter.io'},
            {'envvar': 'SNS_TOPIC_ARN=arn:aws:sns:us-east-1:027273742350:site-gen-sync-s3-finished-development'},
            {'envvar': 'SHIFTER_ACCESS_TOKEN=accesstoken'},
            {'envvar': 'SHIFTER_REFRESH_TOKEN=refreshtoken'},
            {'envvar': 'SHIFTER_API_URL_V1=V1'},
            {'envvar': 'SHIFTER_API_URL_V2=V2'},
            {'envvar': 'SHIFTER_USER_EMAIL=email'},
            {'envvar': 'SHIFTER_DOMAIN=test.shifterdomain'},
            {'envvar': 'RDB_ENDPOINT=test.rdbendpoint'},
            {'envvar': 'RDB_USER=test_role'},
            {'envvar': 'RDB_PASSWD=U0hBXzFSMUpCVkVWQlIwRkpUZ3Rlc3RfcGFzcw=='}
        ]
    }

    '''
    default context build for production.
    '''
    os.environ["SHIFTER_ENV"] = "production"
    instance = ServiceBuilder(app_config, query)
    mock_instance(instance)
    context = instance.build_context_wordpress_worker2()
    assert context
    assert context == {
        'service_name': '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd',
        'service_type': 'edit-wordpress',
        'image_string': '027273742350.dkr.ecr.us-east-1.amazonaws.com/shifter-base:latest',
        'publish_port1': 12345,
        'efs_point_web': 'fs-2308c16a/5d5a3d8c-b578-9da9-2126-4bdc13fcaccd/web',
        'envvars': [
            {'envvar': 'SERVICE_PORT=12345'},
            {'envvar': 'SERVICE_TYPE=edit-wordpress'},
            {'envvar': 'SITE_ID=5d5a3d8c-b578-9da9-2126-4bdc13fcaccd'},
            {'envvar': 'SERVICE_DOMAIN=appdev.getshifter.io'},
            {'envvar': 'NOTIFICATION_URL=dGVzdC5ub3RpZmljYXRpb25fdXJs'},
            {'envvar': 'NOTIFICATION_ERROR_URL=dGVzdC5ub3RpZmljYXRpb25lcnJvcl91cmw='},
            {'envvar': 'CF_DOMAIN=tender-ride7316.on.getshifter.io'},
            {'envvar': 'SNS_TOPIC_ARN=arn:aws:sns:us-east-1:027273742350:site-gen-sync-s3-finished-development'},
            {'envvar': 'SHIFTER_ACCESS_TOKEN=accesstoken'},
            {'envvar': 'SHIFTER_REFRESH_TOKEN=refreshtoken'},
            {'envvar': 'SHIFTER_API_URL_V1=V1'},
            {'envvar': 'SHIFTER_API_URL_V2=V2'},
            {'envvar': 'SHIFTER_USER_EMAIL=email'},
            {'envvar': 'SHIFTER_DOMAIN=test.shifterdomain'},
            {'envvar': 'RDB_ENDPOINT=test.rdbendpoint'},
            {'envvar': 'RDB_USER=test_role'},
            {'envvar': 'RDB_PASSWD=U0hBXzFSMUpCVkVWQlIwRkpUZ3Rlc3RfcGFzcw=='}
        ]
    }
    del os.environ["SHIFTER_ENV"]

    '''
    enable safemode.
    '''
    q = query.copy()
    q['opts_cleanup_plugins'] = True
    q['opts_cleanup_themes'] = True
    instance = ServiceBuilder(app_config, q)
    mock_instance(instance)
    context = instance.build_context_wordpress_worker2()
    assert context
    assert context == {
        'service_name': '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd',
        'service_type': 'edit-wordpress',
        'image_string': '027273742350.dkr.ecr.us-east-1.amazonaws.com/shifter-base:latest_develop',
        'publish_port1': 12345,
        'efs_point_web': 'fs-2308c16a/5d5a3d8c-b578-9da9-2126-4bdc13fcaccd/web',
        'envvars': [
            {'envvar': 'SERVICE_PORT=12345'},
            {'envvar': 'SERVICE_TYPE=edit-wordpress'},
            {'envvar': 'SITE_ID=5d5a3d8c-b578-9da9-2126-4bdc13fcaccd'},
            {'envvar': 'SERVICE_DOMAIN=appdev.getshifter.io'},
            {'envvar': 'NOTIFICATION_URL=dGVzdC5ub3RpZmljYXRpb25fdXJs'},
            {'envvar': 'NOTIFICATION_ERROR_URL=dGVzdC5ub3RpZmljYXRpb25lcnJvcl91cmw='},
            {'envvar': 'CF_DOMAIN=tender-ride7316.on.getshifter.io'},
            {'envvar': 'SNS_TOPIC_ARN=arn:aws:sns:us-east-1:027273742350:site-gen-sync-s3-finished-development'},
            {'envvar': 'SHIFTER_ACCESS_TOKEN=accesstoken'},
            {'envvar': 'SHIFTER_REFRESH_TOKEN=refreshtoken'},
            {'envvar': 'SHIFTER_API_URL_V1=V1'},
            {'envvar': 'SHIFTER_API_URL_V2=V2'},
            {'envvar': 'SHIFTER_USER_EMAIL=email'},
            {'envvar': 'SHIFTER_DOMAIN=test.shifterdomain'},
            {'envvar': 'RDB_ENDPOINT=test.rdbendpoint'},
            {'envvar': 'RDB_USER=test_role'},
            {'envvar': 'RDB_PASSWD=U0hBXzFSMUpCVkVWQlIwRkpUZ3Rlc3RfcGFzcw=='},
            {'envvar': 'SHIFTEROPTS_CLEANUP_PLUGINS=TRUE'},
            {'envvar': 'SHIFTEROPTS_CLEANUP_THEMES=TRUE'},
        ]
    }

    '''
    enable Emerge mode.
    '''
    q = query.copy()
    q['opts_emerge_admin'] = "foobarpassword"
    instance = ServiceBuilder(app_config, q)
    mock_instance(instance)
    context = instance.build_context_wordpress_worker2()
    assert context
    assert context == {
        'service_name': '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd',
        'service_type': 'edit-wordpress',
        'image_string': '027273742350.dkr.ecr.us-east-1.amazonaws.com/shifter-base:latest_develop',
        'publish_port1': 12345,
        'efs_point_web': 'fs-2308c16a/5d5a3d8c-b578-9da9-2126-4bdc13fcaccd/web',
        'envvars': [
            {'envvar': 'SERVICE_PORT=12345'},
            {'envvar': 'SERVICE_TYPE=edit-wordpress'},
            {'envvar': 'SITE_ID=5d5a3d8c-b578-9da9-2126-4bdc13fcaccd'},
            {'envvar': 'SERVICE_DOMAIN=appdev.getshifter.io'},
            {'envvar': 'NOTIFICATION_URL=dGVzdC5ub3RpZmljYXRpb25fdXJs'},
            {'envvar': 'NOTIFICATION_ERROR_URL=dGVzdC5ub3RpZmljYXRpb25lcnJvcl91cmw='},
            {'envvar': 'CF_DOMAIN=tender-ride7316.on.getshifter.io'},
            {'envvar': 'SNS_TOPIC_ARN=arn:aws:sns:us-east-1:027273742350:site-gen-sync-s3-finished-development'},
            {'envvar': 'SHIFTER_ACCESS_TOKEN=accesstoken'},
            {'envvar': 'SHIFTER_REFRESH_TOKEN=refreshtoken'},
            {'envvar': 'SHIFTER_API_URL_V1=V1'},
            {'envvar': 'SHIFTER_API_URL_V2=V2'},
            {'envvar': 'SHIFTER_USER_EMAIL=email'},
            {'envvar': 'SHIFTER_DOMAIN=test.shifterdomain'},
            {'envvar': 'RDB_ENDPOINT=test.rdbendpoint'},
            {'envvar': 'RDB_USER=test_role'},
            {'envvar': 'RDB_PASSWD=U0hBXzFSMUpCVkVWQlIwRkpUZ3Rlc3RfcGFzcw=='},
            {'envvar': 'SHIFTEROPTS_EMERGE_ADMIN=foobarpassword'},
        ]
    }

    '''
    site domain is 'null'. envvar SHIFTER_DOMAIN does not generate.
    '''
    instance = ServiceBuilder(app_config, query)
    mock_instance(instance)
    test_site_item['domain'] = 'null'
    context = instance.build_context_wordpress_worker2()
    assert context
    assert context == {
        'service_name': '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd',
        'service_type': 'edit-wordpress',
        'image_string': '027273742350.dkr.ecr.us-east-1.amazonaws.com/shifter-base:latest_develop',
        'publish_port1': 12345,
        'efs_point_web': 'fs-2308c16a/5d5a3d8c-b578-9da9-2126-4bdc13fcaccd/web',
        'envvars': [
            {'envvar': 'SERVICE_PORT=12345'},
            {'envvar': 'SERVICE_TYPE=edit-wordpress'},
            {'envvar': 'SITE_ID=5d5a3d8c-b578-9da9-2126-4bdc13fcaccd'},
            {'envvar': 'SERVICE_DOMAIN=appdev.getshifter.io'},
            {'envvar': 'NOTIFICATION_URL=dGVzdC5ub3RpZmljYXRpb25fdXJs'},
            {'envvar': 'NOTIFICATION_ERROR_URL=dGVzdC5ub3RpZmljYXRpb25lcnJvcl91cmw='},
            {'envvar': 'CF_DOMAIN=tender-ride7316.on.getshifter.io'},
            {'envvar': 'SNS_TOPIC_ARN=arn:aws:sns:us-east-1:027273742350:site-gen-sync-s3-finished-development'},
            {'envvar': 'SHIFTER_ACCESS_TOKEN=accesstoken'},
            {'envvar': 'SHIFTER_REFRESH_TOKEN=refreshtoken'},
            {'envvar': 'SHIFTER_API_URL_V1=V1'},
            {'envvar': 'SHIFTER_API_URL_V2=V2'},
            {'envvar': 'SHIFTER_USER_EMAIL=email'},
            {'envvar': 'RDB_ENDPOINT=test.rdbendpoint'},
            {'envvar': 'RDB_USER=test_role'},
            {'envvar': 'RDB_PASSWD=U0hBXzFSMUpCVkVWQlIwRkpUZ3Rlc3RfcGFzcw=='}
        ]
    }

    '''
    email is 'null'. envvar SHIFTER_USER_EMAIL is set to null.
    '''
    q = query.copy()
    q.pop('email')
    instance = ServiceBuilder(app_config, q)
    mock_instance(instance)
    test_site_item['domain'] = 'null'
    query['email'] = 'null'
    context = instance.build_context_wordpress_worker2()
    assert context
    assert context == {
        'service_name': '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd',
        'service_type': 'edit-wordpress',
        'image_string': '027273742350.dkr.ecr.us-east-1.amazonaws.com/shifter-base:latest_develop',
        'publish_port1': 12345,
        'efs_point_web': 'fs-2308c16a/5d5a3d8c-b578-9da9-2126-4bdc13fcaccd/web',
        'envvars': [
            {'envvar': 'SERVICE_PORT=12345'},
            {'envvar': 'SERVICE_TYPE=edit-wordpress'},
            {'envvar': 'SITE_ID=5d5a3d8c-b578-9da9-2126-4bdc13fcaccd'},
            {'envvar': 'SERVICE_DOMAIN=appdev.getshifter.io'},
            {'envvar': 'NOTIFICATION_URL=dGVzdC5ub3RpZmljYXRpb25fdXJs'},
            {'envvar': 'NOTIFICATION_ERROR_URL=dGVzdC5ub3RpZmljYXRpb25lcnJvcl91cmw='},
            {'envvar': 'CF_DOMAIN=tender-ride7316.on.getshifter.io'},
            {'envvar': 'SNS_TOPIC_ARN=arn:aws:sns:us-east-1:027273742350:site-gen-sync-s3-finished-development'},
            {'envvar': 'SHIFTER_ACCESS_TOKEN=accesstoken'},
            {'envvar': 'SHIFTER_REFRESH_TOKEN=refreshtoken'},
            {'envvar': 'SHIFTER_API_URL_V1=V1'},
            {'envvar': 'SHIFTER_API_URL_V2=V2'},
            {'envvar': 'SHIFTER_USER_EMAIL='},
            {'envvar': 'RDB_ENDPOINT=test.rdbendpoint'},
            {'envvar': 'RDB_USER=test_role'},
            {'envvar': 'RDB_PASSWD=U0hBXzFSMUpCVkVWQlIwRkpUZ3Rlc3RfcGFzcw=='}
        ]
    }

    '''
    ServiceType specified 'generator'. generator context is published
    '''
    q = query.copy()
    q['serviceType'] = 'generator'
    instance = ServiceBuilder(app_config, q)
    mock_instance(instance)
    test_site_item['domain'] = 'null'
    test_site_item['serviceType'] = 'edit-wordpress'
    context = instance.build_context_wordpress_worker2()
    assert context
    assert context == {
        'service_name': '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd',
        'service_type': 'generator',
        'image_string': '027273742350.dkr.ecr.us-east-1.amazonaws.com/shifter-base:latest_develop',
        'publish_port1': 12345,
        'efs_point_web': 'fs-2308c16a/5d5a3d8c-b578-9da9-2126-4bdc13fcaccd/web',
        'envvars': [
            {'envvar': 'SERVICE_PORT=12345'},
            {'envvar': 'SERVICE_TYPE=generator'},
            {'envvar': 'SITE_ID=5d5a3d8c-b578-9da9-2126-4bdc13fcaccd'},
            {'envvar': 'SERVICE_DOMAIN=appdev.getshifter.io'},
            {'envvar': 'NOTIFICATION_URL=dGVzdC5ub3RpZmljYXRpb25fdXJs'},
            {'envvar': 'NOTIFICATION_ERROR_URL=dGVzdC5ub3RpZmljYXRpb25lcnJvcl91cmw='},
            {'envvar': 'CF_DOMAIN=tender-ride7316.on.getshifter.io'},
            {'envvar': 'SNS_TOPIC_ARN=arn:aws:sns:us-east-1:027273742350:site-gen-sync-s3-finished-development'},
            {'envvar': 'RDB_ENDPOINT=test.rdbendpoint'},
            {'envvar': 'RDB_USER=test_role'},
            {'envvar': 'RDB_PASSWD=U0hBXzFSMUpCVkVWQlIwRkpUZ3Rlc3RfcGFzcw=='}
        ]
    }

    '''
    raise exception if tokens is not supplyed on 'edit-wordpress' type.
    '''
    q = query.copy()
    q['serviceType'] = 'edit-wordpress'
    q.pop('accessToken')
    instance = ServiceBuilder(app_config, q)
    mock_instance(instance)
    test_site_item['domain'] = 'null'
    test_site_item['serviceType'] = 'edit-wordpress'
    with pytest.raises(ShifterRequestError):
        instance.build_context_wordpress_worker2()

    '''
    raise exception if nothing is found RDS information.
    '''
    instance = ServiceBuilder(app_config, query)
    mock_instance(instance)
    test_site_item['user_database'] = {}
    with pytest.raises(ShifterInvalidSiteItem):
        instance.build_context_wordpress_worker2()

    del os.environ['SHIFTER_API_URL_V1']
    del os.environ['SHIFTER_API_URL_V2']

    xray_recorder.end_segment()
