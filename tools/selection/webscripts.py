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

from amcat.tools.selection import forms
import amcat.tools.selection.database
import amcat.tools.selection.solrlib

from django.template.loader import render_to_string
from django.db import connection
    
from django.db.models import Sum, Count
from amcat.tools.table.table3 import DictTable, ObjectColumn, ObjectTable
from amcat.tools.table.tableoutput import yieldtablerows
from amcat.model.medium import Medium

from django.utils import simplejson
import time, calendar, datetime

import logging
log = logging.getLogger(__name__)
#DISPLAY_IN_MAIN_FORM = 'DisplayInMainForm'

TITLE_COLUMN_NAME = '[title]'

def encode_json_medium(obj):
    if isinstance(obj, Medium):
        return "%s - %s" % (obj.id, obj.name)
    raise TypeError("%r is not JSON serializable" % (o,))
    
def get_key(obj):
    if hasattr(obj, 'id'):
        return obj.id
    return obj
    
class WebScript(object):
    name = None # the name of this webscript
    template = None # special markup to display the form
    form = None # fields specific for this webscript
    displayLocation = None # should be (a list of) another WebScript name that is displayed in the main form
    
    def __init__(self, generalForm, ownForm):
        self.generalForm = generalForm
        self.ownForm = ownForm
        self.isIndexSearch = generalForm.cleaned_data['useSolr'] == True
        
    def getArticles(self):
        """ returns an iterable of articles, when Solr is used, including highlighting """
        form = self.generalForm
        if self.isIndexSearch == False: # make database query
            return amcat.tools.selection.database.getQuerySet(**form.cleaned_data)
        else:
            return amcat.tools.selection.solrlib.highlight(form.cleaned_data['query'], filters=amcat.tools.selection.solrlib.createFilters(form.cleaned_data))
        
    def getAggregates(self):
        form = self.generalForm
        ownForm = self.ownForm
        if self.isIndexSearch == False: # make database query
            queryset = amcat.tools.selection.database.getQuerySet(**form.cleaned_data)
            xAxis = ownForm.cleaned_data['xAxis']
            yAxis = ownForm.cleaned_data['yAxis']
            if xAxis == 'date':
                dateInterval = ownForm.cleaned_data['dateInterval']
                dateStrDict = {'day':'YYYY-MM-DD', 'week':'YYYY-WW', 'month':'YYYY-MM', 'quarter':'YYYY-Q', 'year':'YYYY'}
                xSql = "to_char(date, '%s')" % dateStrDict[dateInterval]
            elif xAxis == 'medium':
                xSql = 'medium_id'
            else:
                raise Exception('unsupported xAxis')
                
            if yAxis == 'medium':
                ySql = 'medium_id'
            elif yAxis == 'total':
                ySql = None
            elif yAxis == 'searchTerm':
                raise Exception('searchTerm not supported when not performing a search')
            else:
                raise Exception('unsupported yAxis')
                
            select_data = {"x": xSql}
            vals = ['x']
            if ySql:
                select_data["y"] = ySql
                vals.append('y')

            
            data = queryset.extra(select=select_data).values(*vals).annotate(count=Count('id'))#.order_by('x')
            xDict = {}
            if xAxis == 'medium':
                xDict = Medium.objects.in_bulk(set(row['x'] for row in data))
            yDict = {}
            if yAxis == 'medium':
                yDict = Medium.objects.in_bulk(set(row['y'] for row in data))
            
            table3 = DictTable(0)
            for row in data:
                table3.addValue(xDict.get(row['x'], row['x']), yDict.get(row.get('y', '[total]'), row.get('y', '[total]')), row['count'])
            #log.debug(data)
            return table3
            # cursor = connection.cursor()
            # cursor.execute("SELECT count(%s) FROM articles WHERE projectid IN (%s)", [self.baz])
            # rows = cursor.fetchall()
        else:
            #raise Exception("not implemented yet")
            queries = [x.strip() for x in form.cleaned_data['query'].split('\n') if x.strip()]
            xAxis = ownForm.cleaned_data['xAxis']
            yAxis = ownForm.cleaned_data['yAxis']
            counterType = ownForm.cleaned_data['counterType']
            dateInterval = ownForm.cleaned_data['dateInterval']
            return amcat.tools.selection.solrlib.basicAggregate(queries, xAxis, yAxis, counterType, dateInterval, filters=amcat.tools.selection.solrlib.createFilters(form.cleaned_data))
        
        
    def outputArticleList(self, articles):
        articles = articles[:50] # todo remove limit
        return render_to_string('navigator/selection/articlelist.html', { 'articles': articles })
        
       
    def outputArticleTable(self, articles):
        articles = articles[:50] # todo remove limit
        
        columns = [
            ObjectColumn("id", lambda a: a.id),
            ObjectColumn("headline", lambda a: a.headline),#a.highlightedHeadline[0] if hasattr('a', 'highlightedHeadline') else a.headline), # does not work since gets stripped away later
            ObjectColumn("date", lambda a: a.date.strftime('%Y-%m-%d')),
            ObjectColumn("medium", lambda a: '%s - %s' % (a.medium.id, a.medium.name) ),
            ObjectColumn("length", lambda a: a.length)
        ]
        
        table = ObjectTable(articles, columns)
        tablerows = yieldtablerows(table) # helper function needed since Django does not support function calling in templates with 2 parameters...
        return render_to_string('navigator/selection/articletable.html', { 'table': table, 'tablerows':tablerows })
        
       
        
    
        
    def outputAggregationTable(self, table, title=None):
        #return render_to_string('navigator/selection/table.html', { 'table': table })
        columns = sorted(table.getColumns(), key=lambda x:x.id if hasattr(x,'id') else x)
        columnsJson = simplejson.dumps([{'mDataProp':TITLE_COLUMN_NAME,'sTitle':'', 'sType':'objid', 'sWidth':'100px'}] + 
                                    [{'mDataProp':get_key(col),'sTitle':col, 'sWidth':'70px'} for col in columns], 
                                  default=encode_json_medium)
        dataJson = []
        for row in table.getRows():
            rowJson = {get_key(col):table.getValue(row, col) for col in columns}
            rowJson[TITLE_COLUMN_NAME] = row
            dataJson.append(rowJson)
        dataJson = simplejson.dumps(dataJson, default=encode_json_medium)
        
        ownForm = self.ownForm
        datesDict = {}
        
        if ownForm.cleaned_data['xAxis'] == 'date':
            dates = table.getRows()
            print dates
            interval = ownForm.cleaned_data['dateInterval']
            if interval == 'week':
                for datestr in dates:
                    year = datestr.split('-')[0]
                    week = datestr.split('-')[1]
                    starttime = datetime.datetime.strptime('%s %s 1' % (year, week), '%Y %W %w')
                    endtime = datetime.datetime.strptime('%s %s 0' % (year, week), '%Y %W %w')
                    datesDict[datestr] = [starttime.strftime('%Y-%m-%d'), endtime.strftime('%Y-%m-%d')]
            elif interval == 'month':
                for datestr in dates:
                    year = int(datestr.split('-')[0])
                    month = int(datestr.split('-')[1])
                    endday = calendar.monthrange(year, month)[1]
                    datesDict[datestr] = ['%s-%02d-01' % (year, month), '%s-%02d-%02d' % (year, month, endday) ]
            elif interval == 'quarter':
                for datestr in dates:
                    year = datestr.split('-')[0]
                    quarter = int(datestr.split('-')[1])
                    startmonth = ((quarter - 1) * 3 + 1)
                    endmonth = ((quarter - 1) * 3 + 3)
                    endday = calendar.monthrange(int(year), endmonth)[1]
                    datesDict[datestr] = ['%s-%02d-01' % (year, startmonth), '%s-%02d-%02d' % (year, endmonth, endday)]
                    
        print datesDict
        datesDictJson = simplejson.dumps(datesDict)
        
        return render_to_string('navigator/selection/tableoutput.html', { 'dataJson':dataJson, 'columnsJson':columnsJson, 'title':title, 
                                                                'ownForm':ownForm, 'aggregationType':'article', 'datesDict':datesDictJson})
        
        
    
class ShowSummary(WebScript):
    name = "Summary"
    template = None
    form = forms.EmptyForm
    #displayLocation = DISPLAY_IN_MAIN_FORM
    
    def run(self):
        articles = self.getArticles()
        return self.outputArticleList(articles)
        
    
class ShowArticleTable(WebScript):
    name = "Article Table"
    template = None
    form = forms.ListForm
    #displayLocation = DISPLAY_IN_MAIN_FORM
    
    def run(self):
        articles = self.getArticles()
        return self.outputArticleTable(articles)
        
        
class ShowAggregation(WebScript):
    name = "Aggregation"
    template = "navigator/selection/tableform.html"
    form = forms.AggregationForm
    #displayLocation = DISPLAY_IN_MAIN_FORM
    
    def run(self):
        aggregateTable = self.getAggregates()
        title = None
        if self.isIndexSearch == False:
            title = 'Article count'
        return self.outputAggregationTable(aggregateTable, title)
    
    
        
class ShowGraph(WebScript):
    name = "Show graph"
    template = "navigator/selection/tableform.html"
    form = forms.AggregationForm
    #displayLocation = DISPLAY_IN_MAIN_FORM
    
    def run(self):
        aggregateTable = self.getAggregates()
        return self.outputGraph(aggregateTable)
    
    
        


class SaveAsSet(WebScript):
    name = "Save as set"
    template = None
    form = forms.SaveAsSetForm
    displayLocation = 'ShowTable'
    
    def run(self):
        pass
    