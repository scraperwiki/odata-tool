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
        assert len(dom.cssselect('collection')) == 2
        assert dom.cssselect('title')[1].text_content() == 'tweets'
        assert dom.cssselect('title')[2].text_content() == '__status'
