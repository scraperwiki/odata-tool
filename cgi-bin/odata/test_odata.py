# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import sys
import unittest
import tempfile
import mock
import os
import lxml.html

from collections import OrderedDict
from nose.tools import *
from flask import Response

import odata # this is our Flask script

class GettingTables(unittest.TestCase):

    def setUp(self):
        odata.app.config['TESTING'] = True
        self.app = odata.app.test_client()

    def test_get_tables_calls_sql_endpoint(self):
        url = 'https://server.scraperwiki.com/datasetid/token/sql/meta'
        with mock.patch('requests.get') as requests_get:
            tables = odata.get_tables(url)
            assert requests_get.called
            requests_get.assert_called_with(url)

    def test_get_tables_returns_a_list(self):
        url = 'https://server.scraperwiki.com/datasetid/token/sql/meta'
        tables = odata.get_tables(url)
        print type(tables)
        assert isinstance(tables, list)


class CgiTestCase(unittest.TestCase):

    def setUp(self):
        odata.app.config['TESTING'] = True
        self.app = odata.app.test_client()
        self.get_tables_patcher = mock.patch('odata.get_tables')
        get_tables = self.get_tables_patcher.start()
        get_tables.return_value = ['tweets', '__status']

    def tearDown(self):
        self.get_tables_patcher.stop()

    def test_show_collections_returns_valid_xml(self):
        response = self.app.get('/toolid/token/cgi-bin/odata/')
        dom = lxml.html.fromstring(response.data)
        assert_equal(len(dom.cssselect('workspace')), 1)

    def test_show_collections_returns_the_right_tables(self):
        response = self.app.get('/toolid/token/cgi-bin/odata/')
        dom = lxml.html.fromstring(response.data)
        assert_equal(len(dom.cssselect('collection')), 2)
        assert_equal(dom.cssselect('title')[1].text_content(), 'tweets')
        assert_equal(dom.cssselect('title')[2].text_content(), '__status')

    def test_get_cells_in_row_escapes_columns_names(self):
        row = OrderedDict([
            ("""with spaces""", 1),
            ("""with'punc"tuation""", 2),
            ("""dashes-and_hyphens""", 3),
            ("""0startsWithANumber""", 4),
            ("""xmlAtStart""", 5),
            ("""_underscoreAtStart""", 6)
        ])
        cells = odata.get_cells_in_row(row)
        assert_equals(cells[0]['column'], """with spaces""")
        assert_equals(cells[0]['column_safe'], 'withSpaces')
        assert_equals(cells[1]['column'], """with'punc"tuation""")
        assert_equals(cells[1]['column_safe'], 'withpunctuation')
        assert_equals(cells[2]['column'], """dashes-and_hyphens""")
        assert_equals(cells[2]['column_safe'], 'dashesAndHyphens')
        assert_equals(cells[3]['column'], """0startsWithANumber""")
        assert_equals(cells[3]['column_safe'], 'x0startsWithANumber')
        assert_equals(cells[4]['column'], """xmlAtStart""")
        assert_equals(cells[4]['column_safe'], 'xxmlAtStart')
        assert_equals(cells[5]['column'], """_underscoreAtStart""")
        assert_equals(cells[5]['column_safe'], 'xUnderscoreAtStart')

    @mock.patch('odata.get_entries_in_collection')
    def test_show_collection_uses_escaped_column_names(self, get_entries):
        get_entries.return_value = [{
            'rowid': 1,
            'cells': [{
                'column': 'my favourite column',
                'column_safe': 'myFavouriteColumn',
                'value': 12345678910,
                'type': 'Edm.Int64'
            }]
        }]
        response = self.app.get('/toolid/token/cgi-bin/odata/tweets')
        dom = lxml.html.fromstring(response.data)
        assert_equal(len(dom.cssselect('myFavouriteColumn')), 1)

    @mock.patch('odata.get_entries_in_collection')
    def test_show_collection_returns_valid_xml(self, get_entries):
        get_entries.return_value = [{
            'rowid': 1,
            'cells': [{
                'column': 'id',
                'column_safe': 'id',
                'value': 12345678910,
                'type': 'Edm.Int64'
            }, {
                'column': 'text',
                'column_safe': 'text',
                'value': 'An example cell value',
                'type': 'Edm.String'
            }]
        }]
        response = self.app.get('/toolid/token/cgi-bin/odata/tweets')
        dom = lxml.html.fromstring(response.data)
        assert_equal(len(dom.cssselect('entry')), 1)

    @mock.patch('odata.get_entries_in_collection')
    def test_show_collection_returns_the_right_cell_values(self, get_entries):
        get_entries.return_value = [{
            'rowid': 1,
            'cells': [{
                'column': 'id',
                'column_safe': 'id',
                'value': 12345678910,
                'type': 'Edm.Int64'
            }, {
                'column': 'text',
                'column_safe': 'text',
                'value': 'An example cell value',
                'type': 'Edm.String'
            }]
        }]
        response = self.app.get('/toolid/token/cgi-bin/odata/tweets')
        dom = lxml.html.fromstring(response.data)
        assert_equal(dom.cssselect('properties id')[0].text_content(), '12345678910')
        assert_equal(dom.cssselect('properties id')[0].get('m:type'), 'Edm.Int64')
        assert_equal(dom.cssselect('properties text')[0].text_content(), 'An example cell value')
        assert_equal(dom.cssselect('properties text')[0].get('m:type'), 'Edm.String')

    @mock.patch('odata.get_entries_in_collection')
    def test_show_collection_can_be_paginated(self, get_entries):
        get_entries.return_value = [{
            'rowid': 1,
            'cells': []
        }]
        self.app.get('/toolid/token/cgi-bin/odata/tweets?$skip=100')
        get_entries.assert_called_with(mock.ANY, mock.ANY, limit=100, offset=100, rowid=None)

    @mock.patch('odata.get_entries_in_collection')
    def test_we_can_request_a_single_entry_by_its_rowid(self, get_entries):
        self.app.get('/toolid/token/cgi-bin/odata/tweets(13)')
        get_entries.assert_called_with(mock.ANY, 'tweets', limit=100, offset=0, rowid=13)

    @mock.patch('requests.get')
    def test_single_entry_queries_are_properly_requested(self, requests_get):
        query = 'SELECT rowid, * FROM "tweets" WHERE rowid=13 LIMIT 100 OFFSET 0'
        odata.get_entries_in_collection(
            'http://server.scraperwiki.com/datasetid/token/sql',
            'tweets',
            rowid=13
        )
        args = requests_get.call_args
        assert_equal(args[1]['params']['q'], query)


class TypeDetectionTestCase(unittest.TestCase):

    def test_that_booleans_are_correctly_detected(self):
        t1 = odata.get_cell_type(True)
        assert_equal(t1, 'Edm.Boolean')
        t2 = odata.get_cell_type(False)
        assert_equal(t2, 'Edm.Boolean')

    def test_that_integers_are_correctly_detected(self):
        t = odata.get_cell_type(13)
        assert_equal(t, 'Edm.Int32')

    def test_that_64bit_integers_are_correctly_detected(self):
        t = odata.get_cell_type(4294967296)
        assert_equal(t, 'Edm.Int64')

    def test_that_decimals_are_correctly_detected(self):
        t = odata.get_cell_type(3.14159265)
        assert_equal(t, 'Edm.Double')

    def test_that_nones_are_correctly_detected(self):
        t = odata.get_cell_type(None)
        assert_equal(t, 'Edm.Null')

    def test_that_empty_strings_are_correctly_detected(self):
        t = odata.get_cell_type(b'') # we've imported unicode_literals so we need to force byte encoding here
        assert_equal(t, 'Edm.String')

    def test_that_unicode_strings_are_correctly_detected(self):
        t = odata.get_cell_type('I ♥ unicode')
        assert_equal(t, 'Edm.String')

    def test_that_iso_dates_are_correctly_detected(self):
        t = odata.get_cell_type('2014-02-20T08:31:25Z')
        assert_equal(t, 'Edm.DateTime')

    def test_that_messy_iso_dates_are_correctly_detected(self):
        t = odata.get_cell_type('2014-02-20 08:31:25+00:00')
        assert_equal(t, 'Edm.DateTime')

    def test_that_nonstandard_dates_are_correctly_detected(self):
        t = odata.get_cell_type('Sat, 07 Sep 2002 00:00:01 GMT')
        assert_equal(t, 'Edm.DateTime')

    def test_that_standalone_dates_are_correctly_detected(self):
        t = odata.get_cell_type('2014/01/30')
        assert_equal(t, 'Edm.DateTime')

    def test_that_standalone_times_are_correctly_detected(self):
        t = odata.get_cell_type('13:00')
        assert_equal(t, 'Edm.DateTime')
