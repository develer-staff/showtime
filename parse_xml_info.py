#!/usr/bin/env python
# encoding: utf-8
#
# Copyright 2009 Develer S.r.l. (http://www.develer.com/)
# All rights reserved.
#
# $Id:$
#
# Author: Lorenzo Berni <duplo@develer.com>
#

from xml.etree import ElementTree as ET

def parse_projects(etree):
    projects = {}
    for element in etree:
        projects[element.get("id")] = element.get("name")
    return projects

def parse_hours(etree):
    hours = []
    for element in etree:
        hours.append(
            {
                "date": element.get("date"),
                "time": element.get("time"),
                "remark": element.get("remark"),
                "activity": element.get("activity"),
                "phase": element.get("phase"),
                "user": element.get("user"),
            }
        )
    return hours
