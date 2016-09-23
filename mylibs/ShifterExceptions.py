#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import unicode_literals


class ShifterErrorBase(Exception):
    def __init__(self, info="ShifterError", exit_code=None):
        self.info = info
        self.exit_code = exit_code
        return None


class ShifterUnknownError(ShifterErrorBase):
    pass


class ShifterRequestError(ShifterErrorBase):
    pass


class ShifterNoAvaliPorts(ShifterErrorBase):
    pass


class ShifterConfrictNewService(ShifterErrorBase):
    pass


class ShifterConfrictPublishPorts(ShifterErrorBase):
    pass
