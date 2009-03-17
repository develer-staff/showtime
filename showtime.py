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


## CGI modules
import cgi
import cgitb
cgitb.enable()

## Django modules needed for the template
from django.conf import settings
from django.template import Template, Context

## XML parsing modules
from xml.etree import ElementTree as ET
from xml.parsers.expat import ExpatError


########################################
## Definition of the needed constants ##
########################################

MONTHS = (
    (1, "Gennaio"),
    (2, "Febbraio"),
    (3, "Marzo"),
    (4, "Aprile"),
    (5, "Maggio"), 
    (6, "Giugno"),
    (7, "Luglio"),
    (8, "Agosto"),
    (9, "Settembre"),
    (10, "Ottobre"),
    (11, "Novembre"),
    (12, "Dicembre"),
)

YEARS = (
    2005,
    2006,
    2007,
    2008,
    2009,
)

USER = "duplo"
PASSWORD = "duplo"
ACHIEVOURI = "http://localhost/achievo/"

########################################



##################################
## Achievo response XML parsers ##
##################################

## Needed only if you extract the parson module
#from xml.etree import ElementTree as ET
#import datetime

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

##################################



###########################################
## Achievo remote interface (from pyuac) ##
###########################################

import urllib, urllib2, urlparse
## Needed only if you extract the module
#from xml.etree import ElementTree as ET
#from xml.parsers.expat import ExpatError

ACHIEVO_ENCODING = "ISO-8859-15"

class RemoteTimereg:
    """
    RemoteTimereg si interfaccia (in modo sincrono) con il modulo Achievo "remote".
    Sia server che client sono fondamentalmente stateles, l'unico stato è
    l'aver fatto login, condizione obbligatoria per compiere qualsiasi funzione.
    I metodi accettano parametri standard e restituiscono un oggetto ElementTree.
    """

    actions = {"login": "Log into an Achievo server (uri, user, pwd)",
               "query": "Search the project matching the smartquery",
               "whoami": "Returns login info",
               "timereg": "Register worked time",
               "delete": "Delete the timered by id",
               "timereport": "Report time registered in the provided date[s]"}

    def __init__(self):
        self._projects = ET.fromstring("<response />")
        self._login_done = False
        self._auth_done = False

    def login(self, achievouri, user, password):
        """
        Classe di interfaccia per il modulo Achievo "remote"
        Fornire la path di achievo, username e password
        Restituisce il nome utente e rinfresca la sessione di Achievo
        """
        self.user = user
        self.userid = 0
        self.version = None
        self.password = password
        self._achievouri = achievouri
        self._loginurl = urllib.basejoin(self._achievouri, "index.php")
        self._dispatchurl = urllib.basejoin(self._achievouri, "dispatch.php")
        self._keepalive()
        self._login_done = True
        return self.whoami()

    def _keepalive(self):
        """
        Restituisce il nome utente e rinfresca la sessione di Achievo
        """
        # Renew Achievo login to keep the session alive
        auth = urllib.urlencode({"auth_user": self.user,
                                 "auth_pw": self.password})
        if not self._auth_done:
            self._setupAuth()
        # refresh Achievo session
        urllib2.urlopen(self._loginurl, auth).read()

    def _setupAuth(self):
        """
        Imposta l'autenticazione http e la gestione dei cookies
        """
        passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
        # WARN: basic-auth using a URI which is not a pure hostname is
        # broken in Python 2.4.[0123]. This patch fixed it:
        # http://svn.python.org/view/python/trunk/Lib/urllib2.py?rev=45815&r1=43556&r2=45815
        host = urlparse.urlparse(self._achievouri)[1]
        passman.add_password(None, host, self.user, self.password)
        auth_handler = urllib2.HTTPBasicAuthHandler(passman)
        cookie_handler = urllib2.HTTPCookieProcessor()
        opener = urllib2.build_opener(auth_handler, cookie_handler)
        urllib2.install_opener(opener)
        self._auth_done = True

    def _urlDispatch(self, node, action="search", **kwargs):
        """
        Invoca il dispatch.php di Achievo
        """
        params = {"atknodetype": "remote.%s" % node,
                  "atkaction": action}
        # This is the way PHP accepts arrays,
        # without [] it gets only the last value.
        for key, val in kwargs.items():
            if type(val) == list:
                del kwargs[key]
                kwargs[key+"[]"] = [v.encode(ACHIEVO_ENCODING, "replace") for v in val]
            else:
                kwargs[key] = val.encode(ACHIEVO_ENCODING, "replace")
        qstring = urllib.urlencode(params.items() + kwargs.items(), doseq=True)
        page = urllib2.urlopen(self._dispatchurl, qstring).read().strip()
        try:
            return ET.fromstring(page)
        except ExpatError:
            print page.decode(ACHIEVO_ENCODING)
            raise ExpatError, page.decode(ACHIEVO_ENCODING)

    def whoami(self):
        """
        Restituisce il nome utente della sessione attiva
        """
        elogin = self._urlDispatch("whoami")
        if self.userid == 0:
            self.userid = elogin[0].get("id")
        if self.version == None:
            self.version = elogin[0].get("version", "1.2.1")
        return elogin
    
    def projects(self):
        projects = self._urlDispatch("report")
        return projects
    
    def hours(self, projectid, from_date=None, to_date=None):
        params = {}
        params["projectid"] = projectid
        if from_date:
            params["from_date"] = from_date
        if to_date:
            params["to_date"] = to_date
        hours = self._urlDispatch("report", **params)
        return hours

###########################################



#########################
## Template definition ##
#########################

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

#########################


###################
## Main function ##
###################

def main():
    settings.configure(TEMPLATE_DEBUG = True)
    remote = RemoteTimereg()
    remote.login(ACHIEVOURI, USER, PASSWORD)
    form = cgi.FieldStorage()
    projects = parseProjects(remote.projects())
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
        hours, total_time = parseHours(remote.hours(form["projectid"].value,
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

###################



if __name__ == '__main__':
    main()
