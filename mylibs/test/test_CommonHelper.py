# -*- coding: utf-8 -*-
'''
Testing common helpers Class
'''

from ..CommonHelper import *


def test_code_by_plan_id():
    '''
    returns code as string
    '''

    plans = {
        'atier_02_month': '000',
        'free': '001',
        'tier_01_month': '100',
        'tier_02_month': '200',
        'tier_05_year': '500',
        'custom_00_month': '900',
    }

    for x, y in plans.items():
        assert code_by_plan_id(x) == y
