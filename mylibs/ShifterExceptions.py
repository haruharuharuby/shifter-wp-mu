#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import unicode_literals


class ShifterErrorBase(Exception):
    def __init__(self, info="ShifterError"):
        self.info = info
        return None


class ShifterUnknownError(ShifterErrorBase):
    pass


class ShifterRequestError(ShifterErrorBase):
    pass
