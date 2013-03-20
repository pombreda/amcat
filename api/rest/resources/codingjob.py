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
from amcat.tools.caching import cached_named
from amcat.models import CodingJob 
from amcat.models.coding import coding

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers

from api.rest.resources.amcatresource import AmCATResource
from api.rest.serializer import AmCATModelSerializer

from django.db.models import Count
from django.db import transaction, connection, DatabaseError

import logging; log = logging.getLogger(__name__)

STATUS_DONE = (coding.STATUS_COMPLETE, coding.STATUS_IRRELEVANT)

def exec_without_seqscan(func):
    """
    Execute this function with (Postgres) seqscan disabled. This
    forces Postgres to use its indices. Its purpose is to correct
    the behaviour of postgres' query-planner, when retrieving the
    amount of articles of a codingjob.

    Because these amounts are small compared to the vast amount of
    articles in 'normal' articlesets, the planner mistakenly estimates
    that >= 5% of the total amount of entries in the db will be
    touched. Because of this, it decides to use a sequential scan
    which should be faster. (But since its estimates are wrong, it
    is - in reality - a lot slower.)
    """
    def wrapped(self):
        try:
            with transaction.commit_on_success():
                cursor = connection.cursor()
                cursor.execute("set enable_seqscan=false;")
                log.info("blaat")
                return func(self)
        except DatabaseError as e:
            log.exception("Could not disable sequential scan!")

        return func(self)
    return wrapped

class CodingJobSerializer(AmCATModelSerializer):
    """
    This serializer for codingjob includes the amount of total jobs
    and done jobs. Because it would be wholly inefficient to calculate
    the values per codingjob, we ask the database to aggregate for us
    in one query.
    """
    n_articles = serializers.SerializerMethodField('get_n_articles')
    n_codings_done = serializers.SerializerMethodField('get_n_done_jobs')

    @property
    def qs(self):
        # Reset distinct on specific field (not supported with annotate())
        return self.context['view'].object_list.qs.distinct()

    @cached_named("done_jobs")
    @exec_without_seqscan
    def _get_n_done_jobs(self):
        return dict(
            self.qs.filter(codings__status__in=STATUS_DONE)
            .annotate(Count("codings")).values_list("id", "codings__count")
        )

    @cached_named("article_count")
    @exec_without_seqscan
    def _get_n_articles(self):
        return dict(self.qs.annotate(n=Count("articleset__articles")).values_list("id", "n"))

    def get_n_articles(self, obj):
        return self._get_n_articles().get(obj.id, 0)

    def get_n_done_jobs(self, obj):
        return self._get_n_done_jobs().get(obj.id, 0)

    class Meta:
        model = CodingJob

class CodingJobResource(AmCATResource):
    model = CodingJob
    serializer_class = CodingJobSerializer

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest
from api.rest.apitestcase import ApiTestCase
from django.test.client import RequestFactory

class TestCodingJobResource(ApiTestCase):
    def setUp(self):
        super(TestCodingJobResource, self).setUp()
        self.factory = RequestFactory()

    def _test_caching(self):
        """DISABLED: Queries not registered??"""
        from django.core.urlresolvers import reverse
        from django.db import connection

        cj = amcattest.create_test_job()
        req = self.factory.get(reverse("api-v4-codingjob"))

        with self.checkMaxQueries(1):
            res = CodingJobResource().dispatch(req)

    def test_api(self):
        from amcat.models import CodingStatus

        cj = amcattest.create_test_job()

        # Test empty codingjob
        res = self.get(CodingJobResource)['results'][0]
        self.assertTrue("n_codings_done" in res)
        self.assertTrue("n_articles" in res)
        self.assertEquals(1, res["n_articles"])
        self.assertEquals(0, res["n_codings_done"])

        # Add two codings
        cj.codings.add(amcattest.create_test_coding(), amcattest.create_test_coding())
        res = self.get(CodingJobResource)['results'][0]
        self.assertEquals(1, res["n_articles"])
        self.assertEquals(0, res["n_codings_done"])

        # Set one coding to done
        cd= cj.codings.all()[0]
        cd.status = CodingStatus.objects.get(id=coding.STATUS_COMPLETE)
        cd.save()

        res = self.get(CodingJobResource)['results'][0]
        self.assertEquals(1, res["n_codings_done"])

        cd.status = CodingStatus.objects.get(id=coding.STATUS_IRRELEVANT)
        cd.save()

        res = self.get(CodingJobResource)['results'][0]
        self.assertEquals(1, res["n_codings_done"])

