#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import unicode_literals
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def createBadRequestMessage(event, error_text):
    message = {
        "status": 400,
        "message": error_text,
        "request": event
    }
    logger.warning(message)
    return message
