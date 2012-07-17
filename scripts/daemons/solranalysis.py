#!/usr/bin/python
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
Solr plugin
"""

# todo this could be generalized to run an arbitrary analysis

import logging
log = logging.getLogger(__name__)

from amcat.models.analysis import Analysis, AnalysisArticle
from amcat.scripts import script
from amcat.tools.amcatsolr import Solr

from collections import defaultdict

import logging; log = logging.getLogger(__name__)

class SolrAnalysis(script.Script):
    """
    This script takes an iterable holding AnalysisArticle's. It adds
    and removes the articles from solr as needed.

    Refer to script.deamons.preprocessing for more information.
    """
    input_type = AnalysisArticle
    output_type = None
    options_form = None

    def run(self, _input):
        assert(all(isinstance(a, AnalysisArticle) for a in _input))

        articles = set(_input)
        deleting = {a for a in articles if a.delete}
        adding = articles - deleting

        Solr().delete_articles([a.article for a in deleting])
        Solr().add_articles([a.article for a in adding])

        log.info("Solr: added {} and deleted {} articles".format(
            len(adding), len(deleting))
        )

        print("Solr: added {} and delete {} articles".format(
            len(adding), len(deleting))
        )

if __name__ == "__main__":
    from amcat.tools import amcatlogging
    amcatlogging.debug_module()
    from amcat.scripts.tools.cli import run_cli
    run_cli()
