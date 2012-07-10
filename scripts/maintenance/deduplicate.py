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


from django import forms

from amcat.scripts.script import Script
from amcat.scripts.tools import cli

from amcat.models.article import Article
from amcat.models.articleset import ArticleSet, ArticleSetArticle
import logging; log = logging.getLogger(__name__)
from amcat.tools import amcatlogging

class DeduplicateForm(forms.Form):
    """Form for DeduplicateScript"""
    articleset = forms.ModelChoiceField(queryset=ArticleSet.objects.all())

class DeduplicateScript(Script):
    options_form = DeduplicateForm

    def run(self, _input):
        """
        Takes an articleset as input and removes all duplicated articles from that set
        """
        asid = self.options['articleset'] # articleset id
        articles = Article.objects.filter( articlesetarticle__articleset = asid ) # articles in the articleset
        urlDict, urls = {}, set()
        for article in articles:
            url = article.url
            if url:
                url = str(url)
                if not url in urls:
                    urlDict[url] = []
                urlDict[url].append(article.id)
                urls.add(url)

        removable_ids = []
        for ids in urlDict.itervalues():
            if len(ids) > 1:
                removable_ids.extend(ids[1:])
        articles.filter(id__in = removable_ids).update(project = 2) #trash project
        ArticleSetArticle.objects.filter(article__in = removable_ids).delete() #delete from article set
        log.info("Moved %s duplicated articles to trash project" % len(removable_ids))


if __name__ == '__main__':
    cli.run_cli()

###########################################################################  
#                          U N I T   T E S T S                            #  
###########################################################################

from amcat.tools import amcattest    

class TestDeduplicateScript(amcattest.PolicyTestCase):
    def test_deduplicate(self):
        """One article should be deleted from artset and added to project 2"""
        p = amcattest.create_test_project()
        art1 = amcattest.create_test_article( url='blaat1', project=p)
        art2 = amcattest.create_test_article( url='blaat2', project=p)
        art3 = amcattest.create_test_article( url='blaat1', project=p)
        artset = amcattest.create_test_set(articles=[art1, art2, art3])
        d = DeduplicateScript(articleset = artset.id)
        d.run( None )
        self.assertEqual(len(artset.articles.all()), 2)
        self.assertEqual(len(Article.objects.filter(project = 2)), 1)