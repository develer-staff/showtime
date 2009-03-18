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

from datetime import datetime, date, timedelta
import base64


## CGI modules
import os
import cgi
import cgitb
cgitb.enable()

## Django modules needed for the template
from django.conf import settings
from django.template import Template, Context

## XML parsing modules
from xml.etree import ElementTree as ET
from xml.parsers.expat import ExpatError

## modules for work with csv
import csv
import cStringIO as StringIO

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
    for element in etree:
        hours.append(
            {
                "date": datetime.strptime(element.get("date"), "%Y-%m-%d"),
                "time": timedelta(minutes = int(element.get("time"))),
                "remark": element.get("remark"),
                "activity": element.get("activity"),
                "phase": element.get("phase"),
                "user": element.get("user"),
            }
        )
    return hours

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

TPL = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" lang="it">
<head>
    <title>Report delle ore registrate</title>
    <style>
        tr.header_row {
            background-color: #4169e1;
            color: white;
        }
        tr.row1 {
            background-color: #EEEEEE;
        }
        tr.row2 {
            background-color: #cccccc;
        }
        #header {
            margin-bottom: 20px;
        }
        form {
            margin-bottom: 20px;
            width: 640px;        
        }        
        form div {
            margin: 5px 0;
        }
        label {
            font-weight: bold;
        }
        div.form-controls {
            text-align: right;
            margin-top: 15px;
        }
        td {
            padding: 3px;
        }
        th {
            text-align: left;
        }
        .total_row th {
            text-align: right;
        }
        tr.total_row td {
            background-color: #f4a460
        }
        table.hours {
            width: 640px;
        }
        .c-data {
            width: 8em
        }
        .c-user, .c-time {
            width: 90px;
        }
        .logged-user {
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div id="header">
        <img src="https://www.develer.com/pics/develer_logo.png" alt="develer" />
    </div>
    <form method="get" action="showtime.py">
        <table>
            <tr>
                <td class="logged-user">Utente:</td>
                <td>{{ user }}</td>
            </tr>
            <tr>
                <td>
                    <label for="project">Progetto:</label>
                </td>
                <td>
                    <select name="projectid" id="project">
                    {% for pid, pname in projects.items %}
                        <option value="{{ pid }}"{% ifequal pid selected_project %} selected="selected"{% endifequal %}>{{ pname }}</option>
                    {% endfor %}
                    </select>
                </td>
            </tr>
            <tr>
                <td>
                    <label for="year">Anno:</label>
                </td>
                <td>
                    <select name="year" id="year">
                    {% for year in years %}
                        <option value="{{ year }}"{% ifequal year selected_year %} selected="selected"{% endifequal %}>{{ year }}</option>
                    {% endfor %}
                    </select>
                </td>
            </tr>
            <tr>
                <td>
                    <label for="month">Mese:</label>
                </td>
                <td>
                    <select name="month" id="month">
                    {% for month in months %}
                        <option value="{{ month.0 }}"{% ifequal month.0 selected_month %} selected="selected"{% endifequal %}>{{ month.1 }}</option>
                    {% endfor %}
                    </select>
                </td>
            </tr>
            <tr>
                <td colspan="2">
                    <div class="form-controls">
                        <input type="submit" name="action" value="Refresh" />
                        <input type="submit" name="action" value="CSV" />
                    </div>
                </td>
            </tr>
        </table>
    </form>
    {% if hours %}
        <table class="hours">
            <tr class="header_row">
                <th>Data</th>
                <th>Utente</th>
                <th>Descrizione</th>
                <th>Ore</th>
            </tr>
            {% for hour in hours %}
            <tr class="{% cycle "row1" "row2" %}">
                <td class="c-data">{{ hour.date|date:"d b Y" }}</td>
                <td class="c-user">{{ hour.user }}</td>
                <td class="c-remark">{{ hour.remark }}</td>
                <td class="c-time">{% if hour.time.hours %}{{ hour.time.hours }}h {% endif %}{% if hour.time.minutes %}{{ hour.time.minutes }}m{% endif %}</td>
            </tr>
            {% endfor %}
            <tr class="total_row"><th colspan="3">Totale</th><td>{% if total_time.hours %}{{ total_time.hours }}h {% endif %}{% if total_time.minutes %}{{ total_time.minutes }}m{% endif %}</td></tr>
        </table>
    {% endif %}
</body>
</html>
"""

#########################


###################
## Main function ##
###################

def p(msg):
    if isinstance(msg, unicode):
        msg = msg.encode('utf-8')
    print msg

def main():
    # lo standard CGI prevede che il server possa omettere l'header
    # HTTP_AUTHORIZATION se lo desidera, ovviamente Apache lo desidera :) Per
    # avere acesso alla password dell'utente è necessario ricorrere ad un
    # "trucco" riportato in vari siti e che coinvolge mod_rewrite; il trucco
    # consiste nel usare una regola di rewriting che non altera il path ma che
    # aggiunge una variabile di ambiente alla richiesta, ovviamente il valore
    # della variabile d'ambiente è copiato da HTTP_AUTHORIZATION.
    # Esempio:
    # RewriteEngine on
	# RewriteCond %{HTTP:Authorization} (.+)
	# RewriteRule showtime.py$ - [E=HTTP_CGI_AUTH:%1]	
    try:
        USER, PASSWORD = base64.b64decode(os.environ['HTTP_CGI_AUTH'][6:]).split(':')
    except KeyError:
        print "Content-Type: text/html; charset=utf-8"
        print # blank line, end of headers
        p(u"Il web server non è configurato correttamente. Propagare le informazioni di autenticazione nella variabile HTTP_CGI_AUTH")
        return
    except ValueError:
        print "Content-Type: text/html; charset=utf-8"
        print # blank line, end of headers
        p(u"Header di autenticazione malformato. L'applicazione gestisce solo l'autenticazione basic.")
        return
        
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
        selected_month = int(form["month"].value)
        selected_year = int(form["year"].value)
    else:
        selected_month = date.today().month
        selected_year = date.today().year

    if selected_project and selected_month and selected_year:
        from_date = date(selected_year, selected_month, 1)
        to_date = from_date + timedelta(days=31)
        to_date = to_date - timedelta(days=to_date.day)
        hours = parseHours(remote.hours(form["projectid"].value,
            from_date.strftime("%Y-%m-%d"), to_date.strftime("%Y-%m-%d")))
        total_time = timedelta(seconds = 0)
        def ctime(t):
            secs = t.days * 3600 * 24 + t.seconds
            return { 'hours': secs / 3600, 'minutes': (secs / 60) % 60 }
        for h in hours:
            total_time += h['time']
            h['time'] = ctime(h['time'])
        total_time = ctime(total_time)
    else:
        hours = None
        total_time = None

    if 'action' in form and form['action'].value == "CSV":
        string = StringIO.StringIO()
        writer = csv.writer(string)
        writer.writerow(["Data", "Utente", "Descrizione", "Ore"])
        for hour in hours:
            time = ""
            if hour["time"]["hours"] > 0:
                time += "%dh" % hour["time"]["hours"]
            if hour["time"]["minutes"] > 0:
                if len(time) > 0:
                    time += " "
                time += "%dm" % hour["time"]["minutes"]
            writer.writerow([hour["date"].strftime("%d %b %Y"), hour["user"], hour["remark"], time])
        print "Content-Type: text/csv; charset=utf-8"
        print "Content-Disposition: attachment; filename=\"develer-%s-%s.csv\"" % (projects[selected_project],from_date.strftime("%b-%Y"))
        print # blank line, end of headers
        print string.getvalue()
    else:
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
            'user': USER,
        })
        print "Content-Type: text/html; charset=utf-8"
        print # blank line, end of headers
        p(tpl.render(ctx))

###################



if __name__ == '__main__':
    main()
