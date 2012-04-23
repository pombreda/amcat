###########################################################################
#          (C) Vrije Universiteit, Amsterdam (the Netherlands)            #
#                                                                         #
# This file is part of AmCAT - The Amsterdam Content Analysis Toolkit     #
#                                                                         #
# AmCAT is free software: you can redistribute it and/or modify it under  #
# the terms of the GNU Affero General Public License as published by the  #
# Free Software Foundation, either version 3 of the License, or (at your  #
# option) any later version.                                              #
#                                                                         #
# AmCAT is distributed in the hope that it will be useful, but WITHOUT    #
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or   #
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public     #
# License for more details.                                               #
#                                                                         #
# You should have received a copy of the GNU Affero General Public        #
# License along with AmCAT.  If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################

"""
Script to be run daily for data input (scraping, preprocessing etc.
"""

from datetime import date
from django import forms

import logging; log = logging.getLogger(__name__)

from amcat.scripts.script import Script
from amcat.scripts.tools import cli

from amcat.scraping.controller import ThreadedController, scrape_logged, RobustController
from amcat.scraping.scraper import DateForm
from amcat.models.scraper import get_scrapers
from amcat.models.project import Project

from amcat.tools import amcatlogging, toolkit, sendmail

from amcat.tools.table.table3 import ListTable
from amcat.tools.table.tableoutput import table2html

MAIL_HTML = """<h3>Report for daily scraping on {datestr}</h3>

<p>The following scrapers were run:</p>
{table}

<h3>Log Details</h3>
<pre>
{messages}
</pre>"""


MAIL_ASCII = MAIL_HTML
for tag in ["h3", "p", "pre"]:
    MAIL_ASCII = MAIL_ASCII.replace("<%s>"%tag, "").replace("</%s>"%tag, "")

EMAIL = "amcat-scraping@googlegroups.com"

def send_email(count, messages):
    counts = [(s.__class__.__name__, n) for (s,n) in count.items()]
    n = sum(count.values())
    counts.append(("Total", n))
    t = ListTable(counts, colnames=["Scraper", "#Articles"])
    counts_ascii = t.output(useunicode=False, box=False)
    counts_html = table2html(t, printRowNames=False)

    datestr = toolkit.writeDate(date.today())

    mail_ascii = MAIL_ASCII.format(table=counts_ascii, **locals())
    mail_html = MAIL_HTML.format(table=counts_html, **locals())

    subject = "Daily scraping for {datestr}: {n} articles".format(**locals())

    sendmail.sendmail("wouter@vanatteveldt.com", EMAIL, subject, mail_html, mail_ascii)

class DailyForm(DateForm):
    project = forms.ModelChoiceField(queryset=Project.objects.all(), required=False)
    noemail = forms.BooleanField(initial=False,required=False)

class DailyScript(Script):
    options_form = DailyForm

    def run(self, _input):
        date = self.options['date']

        amcatlogging.info_module("amcat.scraping.scraper")
        amcatlogging.info_module("amcat.scraping.controller")

        scrapers = list(get_scrapers(date=date))
        log.info("Starting scraping with {} scrapers: {}".format(
                len(scrapers), [s.__class__.__name__ for s in scrapers]))

        count, messages =  scrape_logged(RobustController(), scrapers)

        log.info("Sending email...")

        if not self.options['noemail']:
            send_email(count, messages)

        log.info("Done")

if __name__ == '__main__':
    cli.run_cli()
