# -*- coding: utf-8 -*-
'''
Testing ServiceBuilder Class
'''

import pytest
from unittest.mock import Mock
import yaml
from ..ServiceBuilder import ServiceBuilder
from ..ShifterExceptions import *

app_config = yaml.load(open('./config/appconfig.yml', 'r'))['development']


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
        ]
    }

    query = {
        "siteId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "action": "deletePublicContents",
        'artifactId': '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd',
        "sessionid": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd"
    }
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
            {'envvar': 'ARTIFACT_ID=5d5a3d8c-b578-9da9-2126-4bdc13fcaccd'},
            {'envvar': 'SNS_TOPIC_ARN=arn:aws:sns:us-east-1:027273742350:site-gen-sync-s3-finished-development'},
        ]
    }

    query = {
        "siteId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "artifactId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "action": "deleteArtifact",
        "sessionid": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd"
    }
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
            {'envvar': 'S3_BUCKET=artifact.getshifter.io'},
            {'envvar': 'SITE_ID=5d5a3d8c-b578-9da9-2126-4bdc13fcaccd'},
            {'envvar': 'SERVICE_NAME=5d5a3d8c-b578-9da9-2126-4bdc13fcaccd'},
            {'envvar': 'DYNAMODB_TABLE=Site-development'},
            {'envvar': 'DELETE_MODE=TRUE'},
            {'envvar': 'CF_DIST_ID=E2XDOVHUH57BXZ'},
            {'envvar': 'ARTIFACT_ID=5d5a3d8c-b578-9da9-2126-4bdc13fcaccd'},
            {'envvar': 'SNS_TOPIC_ARN=arn:aws:sns:us-east-1:027273742350:site-gen-sync-s3-finished-development'},
        ]
    }


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
    image_tag not specfied, it generates context for using latest image.
    '''
    query = {
        "siteId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "action": "createArtifact",
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
            {'envvar': 'S3_FROM=on.getshifter.io/5d5a3d8c-b578-9da9-2126-4bdc13fcaccd'},
            {'envvar': 'S3_TO=artifact.getshifter.io/aaaaaaaa-b578-9da9-2126-4bdc13fcaccd'},
            {'envvar': 'SERVICE_NAME=5d5a3d8cb5789da921264bdc13fcaccd'},
            {'envvar': 'SNS_TOPIC_ARN=arn:aws:sns:us-east-1:027273742350:site-gen-sync-s3-finished-development'}
        ]
    }

    '''
    image_tag not specfied, it generates context for using latest image.
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


def test_build_context_wordpress_worker2():
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
    '''
    default context build.
    '''
    query = {
        "siteId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "action": "createNewService2",
        "serviceType": 'generator',
        "sessionid": "5d5a3d8cb5789da921264bdc13fcaccd",
        "artifactId": "aaaaaaaa-b578-9da9-2126-4bdc13fcaccd",
        "pubPort": 12345,
        "notificationId": "5d5a3d8cb5789da921264bdc13fcaccd"
    }

    instance = ServiceBuilder(app_config, query)
    mock_instance(instance)
    context = instance.build_context_wordpress_worker2()
    assert context
    assert context == {
        'service_name': '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd',
        'service_type': 'generator',
        'image_string': '027273742350.dkr.ecr.us-east-1.amazonaws.com/shifter-base:latest',
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
            {'envvar': 'SHIFTER_DOMAIN=test.shifterdomain'},
            {'envvar': 'RDB_ENDPOINT=test.rdbendpoint'},
            {'envvar': 'RDB_USER=test_role'},
            {'envvar': 'RDB_PASSWD=U0hBXzFSMUpCVkVWQlIwRkpUZ3Rlc3RfcGFzcw=='}
        ]
    }

    '''
    site domain is 'null'. envvar SHIFTER_DOMAIN does not generate.
    '''
    query = {
        "siteId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "action": "createNewService2",
        "serviceType": 'generator',
        "sessionid": "5d5a3d8cb5789da921264bdc13fcaccd",
        "artifactId": "aaaaaaaa-b578-9da9-2126-4bdc13fcaccd",
        "pubPort": 12345,
        "notificationId": "5d5a3d8cb5789da921264bdc13fcaccd"
    }

    instance = ServiceBuilder(app_config, query)
    mock_instance(instance)
    test_site_item['domain'] = 'null'
    context = instance.build_context_wordpress_worker2()
    assert context
    assert context == {
        'service_name': '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd',
        'service_type': 'generator',
        'image_string': '027273742350.dkr.ecr.us-east-1.amazonaws.com/shifter-base:latest',
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
    ServiceType does not specfied. Use default 'edit-wordpress'.
    '''
    query = {
        "siteId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "action": "createNewService2",
        "sessionid": "5d5a3d8cb5789da921264bdc13fcaccd",
        "artifactId": "aaaaaaaa-b578-9da9-2126-4bdc13fcaccd",
        "pubPort": 12345,
        "notificationId": "5d5a3d8cb5789da921264bdc13fcaccd"
    }

    instance = ServiceBuilder(app_config, query)
    mock_instance(instance)
    test_site_item['domain'] = 'null'
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
            {'envvar': 'RDB_ENDPOINT=test.rdbendpoint'},
            {'envvar': 'RDB_USER=test_role'},
            {'envvar': 'RDB_PASSWD=U0hBXzFSMUpCVkVWQlIwRkpUZ3Rlc3RfcGFzcw=='}
        ]
    }

    '''
    raise exception if nothing is found RDS information.
    '''
    query = {
        "siteId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "action": "createNewService2",
        "serviceType": 'edit-wordpress',
        "sessionid": "5d5a3d8cb5789da921264bdc13fcaccd",
        "artifactId": "aaaaaaaa-b578-9da9-2126-4bdc13fcaccd",
        "pubPort": 12345,
        "notificationId": "5d5a3d8cb5789da921264bdc13fcaccd"
    }

    instance = ServiceBuilder(app_config, query)
    mock_instance(instance)
    test_site_item['user_database'] = {}
    with pytest.raises(ShifterInvalidSiteItem):
        instance.build_context_wordpress_worker2()
