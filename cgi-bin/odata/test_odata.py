from __future__ import unicode_literals
import sys
import unittest
import tempfile
import mock
import os
import lxml.html

from nose.tools import *
from flask import Response

import odata # this is our Flask script

class CgiTestCase(unittest.TestCase):

    def setUp(self):
        odata.app.config['TESTING'] = True
        self.app = odata.app.test_client()

    def test_show_collections_returns_valid_xml(self):
        with mock.patch('odata.get_tables') as get_tables:
            get_tables.return_value = ['tweets', '__status']
            response = self.app.get('/box/token/cgi-bin/odata/')
        dom = lxml.html.fromstring(response.data)
        assert_equal(len(dom.cssselect('workspace')), 1)

    def test_show_collections_returns_the_right_tables(self):
        with mock.patch('odata.get_tables') as get_tables:
            get_tables.return_value = ['tweets', '__status']
            response = self.app.get('/box/token/cgi-bin/odata/')
        dom = lxml.html.fromstring(response.data)
        assert_equal(len(dom.cssselect('collection')), 2)
        assert_equal(dom.cssselect('title')[1].text_content(), 'tweets')
        assert_equal(dom.cssselect('title')[2].text_content(), '__status')

    def test_get_tables_calls_sql_endpoint(self):
        url = 'https://example.com/sql/meta'
        with mock.patch('requests.get') as requests_get:
            tables = odata.get_tables(url)
        assert requests_get.called
        requests_get.assert_called_with(url)

    def test_get_tables_returns_a_list(self):
        url = 'https://example.com/sql/meta'
        tables = odata.get_tables(url)
        print type(tables)
        assert isinstance(tables, list)

    def test_show_collection_returns_valid_xml(self):
        with mock.patch('odata.get_entries_in_collection') as get_entries:
            get_entries.return_value = [{
                'url': 'http://server.scraperwiki.com/cgi-bin/odata/tweets(1)',
                'rowid': 1,
                'cells': [{
                    'column': 'id',
                    'value': 12345678910,
                    'type': 'Edm.Int64'
                }, {
                    'column': 'text',
                    'value': 'An example cell value',
                    'type': 'Edm.String'
                }]
            }]
            response = self.app.get('/box/token/cgi-bin/odata/tweets')
        dom = lxml.html.fromstring(response.data)
        assert_equal(len(dom.cssselect('entry')), 1)

    def test_show_collection_returns_the_right_cell_values(self):
        with mock.patch('odata.get_entries_in_collection') as get_entries:
            get_entries.return_value = [{
                'url': 'http://server.scraperwiki.com/cgi-bin/odata/tweets(1)',
                'rowid': 1,
                'cells': [{
                    'column': 'id',
                    'value': 12345678910,
                    'type': 'Edm.Int64'
                }, {
                    'column': 'text',
                    'value': 'An example cell value',
                    'type': 'Edm.String'
                }]
            }]
            response = self.app.get('/box/token/cgi-bin/odata/tweets')
        dom = lxml.html.fromstring(response.data)
        assert_equal(dom.cssselect('properties id')[0].text_content(), '12345678910')
        assert_equal(dom.cssselect('properties id')[0].get('m:type'), 'Edm.Int64')
        assert_equal(dom.cssselect('properties text')[0].text_content(), 'An example cell value')
        assert_equal(dom.cssselect('properties text')[0].get('m:type'), 'Edm.String')

    def test_show_collection_can_be_paginated(self):
        with mock.patch('odata.get_entries_in_collection') as get_entries:
            get_entries.return_value = [{
                'url': 'http://server.scraperwiki.com/cgi-bin/odata/tweets(1)',
                'rowid': 1,
                'cells': []
            }]
            self.app.get('/box/token/cgi-bin/odata/tweets?$skip=100')
        get_entries.assert_called_with(mock.ANY, mock.ANY, limit=100, offset=100, rowid=None)

    def test_we_can_request_a_single_entry_by_its_rowid(self):
        with mock.patch('odata.get_entries_in_collection') as get_entries:
            self.app.get('/box/token/cgi-bin/odata/tweets(13)')
        get_entries.assert_called_with(mock.ANY, 'tweets', limit=100, offset=0, rowid=13)

    def test_single_entry_queries_are_properly_requested(self):
        query = 'SELECT rowid, * FROM "tweets" WHERE rowid=13 LIMIT 100 OFFSET 0'
        with mock.patch('requests.get') as requests_get:
            odata.get_entries_in_collection('http://example.com/sql', 'tweets', rowid=13)
        args = requests_get.call_args
        assert_equal(args[1]['params']['q'], query)

