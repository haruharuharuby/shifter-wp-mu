# -*- coding: utf-8 -*-
'''
Test lambda_function
'''
import pytest
from unittest.mock import Mock
import yaml

from lambda_function import *
from mylibs.ShifterExceptions import *
from mylibs.ServiceBuilder import ServiceBuilder
from mylibs.DockerCtr import DockerCtr

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
ServiceBuilder._ServiceBuilder__loadServiceTemplate = Mock(return_value=(open('./service_specs/sync-s3-to-s3.yml', 'r').read()))

def test_validate_arguments():

    '''
    action syncS3ToS3, arguments are valid. return True.
    '''
    query = {
        "siteId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "action": "syncS3ToS3",
        "sessionid": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "artifactId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "image_tag": "specified-image"
    }

    result = validate_arguments(query)
    assert result is True

    '''
    action syncEfsToS3, it doesn't check arguments now. return True.
    '''
    query = {
        "siteId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "action": "syncEfsToS3",
        "sessionid": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "artifactId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "image_tag": "specified-image"
    }

    result = validate_arguments(query)
    assert result is True

    '''
    action syncS3ToS3, arguments are invalid. raise ShifterRequestError.
    '''
    query = {
        "siteId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "action": "syncS3ToS3",
        "sessionid": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "image_tag": "specified-image"
    }

    with pytest.raises(ShifterRequestError):
        validate_arguments(query)
