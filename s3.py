from __future__ import print_function
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
import boto3

class S3:
    def __init__(self):
        self.client = boto3.client('s3')

    def createWpArchiceUrl( self, wpArchiveId ):
        logger.info(wpArchiveId)
        return 'hoge'
