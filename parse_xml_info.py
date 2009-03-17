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

import datetime

def parseProjects(etree):
    projects = {}
    for element in etree:
        projects[element.get("id")] = element.get("name")
    return projects

def parseHours(etree):
    hours = []
    total_time = 0
    for element in etree:
        hours.append(
            {
                "date": element.get("date"),
                "time": "%d:%s" %(int(element.get("time")) / 60, datetime.time(minute=int(element.get("time")) % 60).strftime("%M")),
                "remark": element.get("remark"),
                "activity": element.get("activity"),
                "phase": element.get("phase"),
                "user": element.get("user"),
            }
        )
        total_time += int(element.get("time"))
    return hours, "%d:%s" % (total_time / 60, datetime.time(minute=total_time % 60).strftime("%M"))
