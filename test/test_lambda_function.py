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


def test_lambda_handler():
    '''
    The roll of this function is to dispatch docker action.
    So this testing function do test dispatching docker action propery.
    '''
    query_base = {
        "siteId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "action": "test",
        "sessionid": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "artifactId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "image_tag": "specified-image"
    }

    DockerCtr.sessionid = Mock(return_value='test_session_id')

    '''
    action is 'test', only return fixed text.
    '''
    query = query_base.copy()
    result = lambda_handler(query, {})
    assert result == 'this is test'

    '''
    action is getTheService, return DockerUrl
    '''
    expect = {'status': 200, 'message': 'OK', 'DockerUrl': 'https://5d5a3d8c-b578-9da9-2126-4bdc13fcaccd.appdev.getshifter.io'}
    DockerCtr.getTheService = Mock(return_value=expect)
    query = query_base.copy()
    query['action'] = 'getTheService'
    result = lambda_handler(query, {})
    assert result == {'status': 200, 'message': 'OK', 'DockerUrl': 'https://5d5a3d8c-b578-9da9-2126-4bdc13fcaccd.appdev.getshifter.io'}

    '''
    action is digSiteDirs, return DockerUrl
    '''
    expect = {'status': 200, 'message': 'OK'}
    DockerCtr.createNewService = Mock(return_value=expect)
    query = query_base.copy()
    query['action'] = 'digSiteDirs'
    query['fsId'] = '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd'
    query['pubPort'] = 12345
    result = lambda_handler(query, {})
    assert result == expect

    '''
    action is bulkDelete, return result of deleting services
    '''
    expect = {
        'status': 200,
        'message': 'OK',
        'deleted': '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd',
        'notFound': '5d5a3d8c-b578-9da9-2126-4bdc13fcacce',
        'error': '5d5a3d8c-b578-9da9-2126-4bdc13fcaccf'
    }
    DockerCtr.bulkDelete = Mock(return_value=expect)
    DockerCtr.sessionid = Mock(return_value='test_session_id')
    query = {}
    query['action'] = 'bulkDelete'
    query['serviceIds'] = ['5d5a3d8c-b578-9da9-2126-4bdc13fcaccd', '5d5a3d8c-b578-9da9-2126-4bdc13fcacce', '5d5a3d8c-b578-9da9-2126-4bdc13fcaccf']
    result = lambda_handler(query, {})
    assert result == expect

    '''
    action is createNewService, return result of new services
    '''
    expect = {
        'status': 200,
        'message': 'service 5d5a3d8c-b578-9da9-2126-4bdc13fcaccd started',
        'docker_url': 'https://5d5a3d8c-b578-9da9-2126-4bdc13fcaccd.appdev.getshifter.io:12345',
        'serviceName': '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd',
        'notificationId': 'test_session_id'
    }
    DockerCtr.createNewService = Mock(return_value=expect)
    query = query_base.copy()
    query['action'] = 'createNewService'
    result = lambda_handler(query, {})
    assert result == expect

    '''
    action is syncEfsToS3, return result of creating syncEfsToS3
    '''
    expect = {
        'status': 200,
        'message': 'service test_session_id started',
        'serviceName': 'test_session_id'
    }
    DockerCtr.createNewService = Mock(return_value=expect)
    query = query_base.copy()
    query['action'] = 'syncEfsToS3'
    result = lambda_handler(query, {})
    assert result == expect

    '''
    action is syncS3ToS3, return result of creating syncS3ToS3
    '''
    expect = {
        'status': 200,
        'message': 'service test_session_id started',
        'serviceName': 'test_session_id'
    }
    DockerCtr.createNewService = Mock(return_value=expect)
    query = query_base.copy()
    query['action'] = 'syncS3ToS3'
    result = lambda_handler(query, {})
    assert result == expect

    '''
    action is deployToNetlify, return result of creating deployToNetlify
    '''
    expect = {
        'status': 200,
        'message': 'OK'
    }
    DockerCtr.createNewService = Mock(return_value=expect)
    query = query_base.copy()
    query['action'] = 'syncS3ToS3'
    result = lambda_handler(query, {})
    assert result == expect

    '''
    action is deletePublicContents, return result of creating deletePublicContents
    '''
    expect = {
        'status': 200,
        'message': 'service test_session_id started',
        'serviceName': 'test_session_id'
    }
    DockerCtr.createNewService = Mock(return_value=expect)
    query = query_base.copy()
    query['action'] = 'deletePublicContents'
    result = lambda_handler(query, {})
    assert result == expect

    '''
    action is deleteTheService, return result of deleting service
    '''
    expect = {
        'status': 200,
        'message': 'service test_session_id started',
        'serviceId': 'test_session_id'
    }
    DockerCtr.deleteTheService = Mock(return_value=expect)
    query = query_base.copy()
    query['action'] = 'deleteTheService'
    result = lambda_handler(query, {})
    assert result == expect

    '''
    action is deleteServiceByServiceId, return result of deleting service by id
    '''
    expect = {
        'status': 200,
        'message': 'service test_session_id started',
        'serviceId': 'test_session_id'
    }
    DockerCtr.deleteServiceByServiceId = Mock(return_value=expect)
    query = query_base.copy()
    query['action'] = 'deleteServiceByServiceId'
    query['serviceId'] = '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd'
    result = lambda_handler(query, {})
    assert result == expect


def test_validate_arguments():
    query_base = {
        "siteId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "action": "syncS3ToS3",
        "sessionid": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "artifactId": "5d5a3d8c-b578-9da9-2126-4bdc13fcaccd",
        "image_tag": "specified-image"
    }

    '''
    it does not contain 'action' in the parameter, raise
    '''
    query = query_base.copy()
    query.pop('action')
    with pytest.raises(ShifterRequestError):
        result = validate_arguments(query)

    '''
    action is test, nothing arguments for checking
    '''
    query = query_base.copy()
    query['action'] = 'test'
    result = validate_arguments(query)
    assert result is True

    '''
    action is getTheService, return True if siteId provided
    '''
    query = query_base.copy()
    query['action'] = 'getTheService'
    result = validate_arguments(query)
    assert result is True

    '''
    action is getTheService, raise if siteId does not provided
    '''
    query = query_base.copy()
    query['action'] = 'getTheService'
    query.pop('siteId')
    with pytest.raises(ShifterRequestError):
        result = validate_arguments(query)

    '''
    action is digSiteDirs, True if fsId provided.
    '''
    query = query_base.copy()
    query['action'] = 'digSiteDirs'
    query['fsId'] = '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd'
    result = validate_arguments(query)
    assert result is True

    '''
    action is digSiteDirs, raise if sessionid does not provided.
    '''
    query = query_base.copy()
    query['action'] = 'digSiteDirs'
    query['fsId'] = '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd'
    query.pop('sessionid')
    with pytest.raises(ShifterRequestError):
        result = validate_arguments(query)

    '''
    action is digSiteDirs, raise if fsId does not provided.
    '''
    query = query_base.copy()
    query['action'] = 'digSiteDirs'
    with pytest.raises(ShifterRequestError):
        result = validate_arguments(query)

    '''
    action is bulkDelete, True if serviceIds provided.
    '''
    query = query_base.copy()
    query['action'] = 'bulkDelete'
    query['serviceIds'] = ['aaa', 'bbb', 'ccc']
    result = validate_arguments(query)
    assert result is True

    '''
    action is bulkDelete, raise if serviceIds is not list.
    '''
    query = query_base.copy()
    query['action'] = 'bulkDelete'
    query['serviceIds'] = 'aaa'
    with pytest.raises(ShifterRequestError):
        result = validate_arguments(query)

    '''
    action is bulkDelete, raise if serviceIds does not provided.
    '''
    query = query_base.copy()
    query['action'] = 'bulkDelete'
    with pytest.raises(ShifterRequestError):
        result = validate_arguments(query)

    '''
    action is createNewService, True if siteId provided.
    '''
    query = query_base.copy()
    query['action'] = 'createNewService'
    result = validate_arguments(query)
    assert result is True

    '''
    action is createNewService, raise if siteId does not provided.
    '''
    query = query_base.copy()
    query['action'] = 'createNewService'
    query.pop('siteId')
    with pytest.raises(ShifterRequestError):
        result = validate_arguments(query)

    '''
    action is syncEfsToS3, True if siteId provided.
    '''
    query = query_base.copy()
    query['action'] = 'syncEfsToS3'
    result = validate_arguments(query)
    assert result is True

    '''
    action is syncEfsToS3, raise if siteId does not provided.
    '''
    query = query_base.copy()
    query['action'] = 'syncEfsToS3'
    query.pop('siteId')
    with pytest.raises(ShifterRequestError):
        result = validate_arguments(query)

    '''
    action is syncEfsToS3, raise if sessionid does not provided.
    '''
    query = query_base.copy()
    query['action'] = 'syncEfsToS3'
    query.pop('sessionid')
    with pytest.raises(ShifterRequestError):
        result = validate_arguments(query)

    '''
    action is syncS3ToS3, True if siteId provided.
    '''
    query = query_base.copy()
    query['action'] = 'syncS3ToS3'
    result = validate_arguments(query)
    assert result is True

    '''
    action is syncS3ToS3, raise if siteId does not provided.
    '''
    query = query_base.copy()
    query['action'] = 'syncS3ToS3'
    query.pop('siteId')
    with pytest.raises(ShifterRequestError):
        result = validate_arguments(query)

    '''
    action is syncS3ToS3, raise if sessionid does not provided.
    '''
    query = query_base.copy()
    query['action'] = 'syncS3ToS3'
    query.pop('sessionid')
    with pytest.raises(ShifterRequestError):
        result = validate_arguments(query)

    '''
    action is syncS3ToS3, raise if artifactId does not provided.
    '''
    query = query_base.copy()
    query['action'] = 'syncS3ToS3'
    query.pop('artifactId')
    with pytest.raises(ShifterRequestError):
        result = validate_arguments(query)

    '''
    action is deletePublicContents, True if siteId provided.
    '''
    query = query_base.copy()
    query['action'] = 'deletePublicContents'
    result = validate_arguments(query)
    assert result is True

    '''
    action is deletePublicContents, raise if siteId does not provided.
    '''
    query = query_base.copy()
    query['action'] = 'deletePublicContents'
    query.pop('siteId')
    with pytest.raises(ShifterRequestError):
        result = validate_arguments(query)

    '''
    action is deleteTheService, True if siteId provided.
    '''
    query = query_base.copy()
    query['action'] = 'deleteTheService'
    result = validate_arguments(query)
    assert result is True

    '''
    action is deleteTheService, raise if siteId does not provided.
    '''
    query = query_base.copy()
    query['action'] = 'deleteTheService'
    query.pop('siteId')
    with pytest.raises(ShifterRequestError):
        result = validate_arguments(query)

    '''
    action is deleteServiceByServiceId, True if serviceId provided.
    '''
    query = query_base.copy()
    query['action'] = 'deleteServiceByServiceId'
    query['serviceId'] = '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd'
    result = validate_arguments(query)
    assert result is True

    '''
    action is deleteServiceByServiceId, raise if siteId does not provided.
    '''
    query = query_base.copy()
    query['action'] = 'deleteServiceByServiceId'
    query['serviceId'] = '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd'
    query.pop('siteId')
    with pytest.raises(ShifterRequestError):
        result = validate_arguments(query)

    '''
    action is deleteServiceByServiceId, raise if serviceId does not provided.
    '''
    query = query_base.copy()
    query['action'] = 'deleteServiceByServiceId'
    query['siteId'] = '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd'
    with pytest.raises(ShifterRequestError):
        result = validate_arguments(query)

    '''
    action is deployToNetlify, True if siteId provided.
    '''
    query = query_base.copy()
    query['action'] = 'deployToNetlify'
    query['nf_siteID'] = '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd'
    query['nf_token'] = '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd'
    result = validate_arguments(query)
    assert result is True

    '''
    action is deployToNetlify, raise if siteId does not provided.
    '''
    query = query_base.copy()
    query['action'] = 'deployToNetlify'
    query['nf_siteID'] = '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd'
    query['nf_token'] = '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd'
    query.pop('siteId')
    with pytest.raises(ShifterRequestError):
        result = validate_arguments(query)

    '''
    action is deployToNetlify, raise if sessionid does not provided.
    '''
    query = query_base.copy()
    query['action'] = 'deployToNetlify'
    query['nf_siteID'] = '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd'
    query['nf_token'] = '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd'
    query.pop('sessionid')
    with pytest.raises(ShifterRequestError):
        result = validate_arguments(query)

    '''
    action is deployToNetlify, raise if nf_siteID does not provided.
    '''
    query = query_base.copy()
    query['action'] = 'deployToNetlify'
    query['nf_token'] = '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd'
    with pytest.raises(ShifterRequestError):
        result = validate_arguments(query)

    '''
    action is deployToNetlify, raise if nf_token does not provided.
    '''
    query = query_base.copy()
    query['action'] = 'deployToNetlify'
    query['nf_siteID'] = '5d5a3d8c-b578-9da9-2126-4bdc13fcaccd'
    with pytest.raises(ShifterRequestError):
        result = validate_arguments(query)
