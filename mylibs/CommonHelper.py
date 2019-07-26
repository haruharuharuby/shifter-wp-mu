#!/usr/bin/env python
# -*- coding: utf-8 -*-


def code_by_plan_id(plan_id):
    if plan_id == 'free':
        return '001'

    if plan_id.find('custom_') == 0:
        return '900'

    if plan_id.find('tier_') == 0:
        a, b, c = plan_id.split('_')
        str(int(b) * 100)
        return str(int(b) * 100)

    return '000'
