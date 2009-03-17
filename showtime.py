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

import datetime

import cgi
import cgitb
cgitb.enable()

import libRemoteTimereg
import parse_xml_info

from django.conf import settings
from django.template import Template, Context

from const import *

def main():
    settings.configure(TEMPLATE_DEBUG = True)
    remote = libRemoteTimereg.RemoteTimereg()
    remote.login(ACHIEVOURI, USER, PASSWORD)
    form = cgi.FieldStorage()
    projects = parse_xml_info.parseProjects(remote.projects())
    if 'projectid' in form:
        selected_project = form['projectid'].value
    else:
        selected_project = None
    if 'projectid' in form and 'month' in form and 'year' in form:
        show_table = True
        selected_month = int(form["month"].value)
        selected_year = int(form["year"].value)
        from_date = datetime.date(int(form["year"].value), int(form["month"].value), 1)
        to_date = from_date + datetime.timedelta(days=31)
        to_date = to_date - datetime.timedelta(days=to_date.day+1)
        hours, total_time = parse_xml_info.parseHours(remote.hours(form["projectid"].value,
            from_date.strftime("%Y-%m-%d"), to_date.strftime("%Y-%m-%d")))
    else:
        show_table = False
        selected_month = datetime.date.today().month
        selected_year = datetime.date.today().year
        hours = None
        total_time = None
    tpl = Template(TPL)
    ctx = Context({
        'projects': projects,
        'selected_project': selected_project,
        'selected_month': selected_month,
        'selected_year': selected_year,
        'months': MONTHS,
        'years': YEARS,
        'hours': hours,
        'total_time': total_time,
        'show_table': show_table,
    })
    print "Content-Type: text/html"     # HTML is following
    print                               # blank line, end of headers    
    print tpl.render(ctx)
    return

TPL = """
<html>
<head>
    <title>Project hours registration report</title>
</head>
<body>
    <img src="http://www.develer.com/website/images/develer-logo-white-2.png" />
    <form method='post' action='showtime.py'>
        <select name='projectid'>
        {% for pid, pname in projects.items %}
            <option value="{{ pid }}" {% ifequal pid selected_project %}selected="selected"{% endifequal %}>{{ pname }}</option>
        {% endfor %}
        </select>
        <br />
        <select name="month">
        {% for month in months %}
            <option value='{{ month.0 }}'{% ifequal month.0 selected_month %} selected{% endifequal %}>{{ month.1 }}</option>
        {% endfor %}
        </select>
        <select name="year">
        {% for year in years %}
            <option value='{{ year }}'{% ifequal year selected_year %} selected{% endifequal %}>{{ year }}</option>
        {% endfor %}
        </select>
        <br />
        <input type='submit' value='Refresh'>
    </form>
    {% if show_table %}
        <table>
            <tr class="header_row"><th>Data</th><th>Utente</th><th>Descrizione</th><th>Ore</th></tr>
            {% for hour in hours %}
            <tr class="{% cycle 'row1' 'row2' %}"><td>{{ hour.date }}</td><td>{{ hour.user }}</td><td>{{ hour.remark }}</td><td>{{ hour.time }}</td></tr>
            {% endfor %}
            <tr class="total_row"><th colspan=3>Totale</th><td>{{ total_time }}</td></tr>
        </table>
    {% endif %}
</body>
</html>
"""

if __name__ == '__main__':
    main()

