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


"""This module checks, for each date from 2012-01-01 until now, whether all scrapers have gathered as much articles as expected for that date.

The expected amounts of articles are generated by expected_articles.py 

If a scraper has not gathered enough articles at a given date, it is re-executed.
After that, the set is deduplicated (for that date)."""


#ranges: {<scraper>:[(1,3),(2,4)... for each day in the week starting monday

from amcat.models.article import Article
from amcat.scripts.script import Script
from amcat.scripts.maintenance.deduplicate import DeduplicateScript

from datetime import date,timedelta

import logging; log = logging.getLogger(__name__)

def days(start,end):
    if start>end:
        raise ValueError("start must be before end")
    
    while start<=end:
        yield end
        end -= timedelta(days=1)

from amcat.models.scraper import Scraper

class OmniScraper(Script):

    def run(self,input):    
        start = date(2012,01,01);end=date.today() - timedelta(days=1)
        for day in reversed(sorted(days(start,end))):
            log.info("running checks and retries for {day}".format(**locals()))
            for scraper in Scraper.objects.all():

                log.debug("getting amount of articles of scraper {scraper} day {day}".format(**locals()))
                n_articles = self.get_n_articles(scraper,day)
                (lower,upper) = scraper.statistics[day.weekday()]
                log.debug("n_articles: {n_articles}, lower: {lower}, upper: {upper}".format(n_articles,lower,upper))
                if n_articles < lower:
                    s_instance = scraper.get_scraper(date=day)

                    log.info("running scraper {s_instance} for date {day}".format(**locals()))
                    s_instance.run(None)

                    log.info("deduplicating articleset {scraper.articleset_id} for date {day}".format(**locals()))
                    self.deduplicate(scraper.articleset_id, day)
                           

    def get_n_articles(self, scraper, day):
        n_articles = Article.objects.filter(
            articlesetarticle__articleset = scraper.articleset_id,
            date = day
            ).count()
        return n_articles


    def deduplicate(self, articleset_id, day):
        options = {
            'first_date' : day,
            'last_date' : day,
            'articleset' : articleset_id,
            'recycle_bin_project' : 1
            }
        DeduplicateScript(**options).run(None)
        


if __name__ == '__main__':
    from amcat.scripts.tools import cli
    from amcat.tools import amcatlogging
    amcatlogging.debug_module("amcat.scripts.maintenance.deduplicate")
    amcatlogging.debug_module(__name__)
    amcatlogging.info_module("amcat.scraping.scraper")
    amcatlogging.debug_module("amcat.scraping.controller")
    cli.run_cli(OmniScraper)
    
