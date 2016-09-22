#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import unicode_literals
import json
import logging

# logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger()
logger.setLevel(logging.INFO)


class ResponceBuilder:
    """
    Type: Module
    Build JSON Response for Frontend and Generator
    Basic Structure:
      res['status'] = int, like HTTP Status.
      res['message'] = "Additional Message"
      res[*opts] = parameters to use by other services.
    """
    def __init__(self):
        return None

    @classmethod
    def buildResponce(self, status=200, message='OK', logs_to={}, **opts):
        # create default message
        default = {
            'status': status,
            'message': message
        }

        if logs_to != {}:
            logger.warning(str(logs_to))

        # merge opts without logs
        response = dict(default, **opts)

        return response
