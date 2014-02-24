#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import logging
import requests
from logging import FileHandler
from wsgiref.handlers import CGIHandler
import os
import re

from flask import Flask, Response, render_template, request

app = Flask(__name__)

# Avoid default Flask redirect when a
# URL is requested without a final slash
app.url_map.strict_slashes = False

# Stop extra whitespace creeping
# into Jinja templates
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True

# Get the "root" url path, because
# Flask isn't running at the domain root
request_path = os.environ.get('PATH_INFO', '/toolid/token/cgi-bin/odata')
api_path = '/'.join(request_path.split('/')[0:5])
api_server = os.environ.get('HTTP_HOST', 'server.scraperwiki.com')

def get_dataset_url():
    try:
        with open('/home/dataset_url.txt', 'r') as file:
            return file.read()
    except IOError:
        return None

dataset_url = get_dataset_url()


@app.route(api_path + "/")
def show_collections():
    tables = get_tables('{}/sql/meta'.format(dataset_url))
    resp = Response()
    resp.headers[b'Content-Type'] = b'application/xml;charset=utf-8'
    resp.data = render_template(
        'collections.xml',
        api_server=api_server,
        api_path=api_path,
        collections=tables
    )
    return resp


@app.route(api_path + "/<collection>/")
def show_collection(collection):

    # Handle pagination
    if request.args.get('$skiptoken'):
        limit = 100
        offset = int(request.args.get('$skiptoken'))
    else:
        limit = int(request.args.get('$top', 100))
        offset = int(request.args.get('$skip', 0))

    # Handle specific row requests
    rowid_match = re.search(r'^(.*)[(](\d+)[)]$', collection)
    if rowid_match:
        collection = rowid_match.group(1)
        rowid = int(rowid_match.group(2))
    else:
        rowid = None

    # TODO: check that `collection` table actually exists
    entries = get_entries_in_collection(
        '{}/sql'.format(dataset_url),
        collection,
        limit=limit,
        offset=offset,
        rowid=rowid
    )

    # Add pagination links if required
    if len(entries) != limit:
        next_query_string = ''
    elif request.args.get('$skiptoken'):
        next_query_string = '?$skiptoken={}'.format(entries[-1]['rowid'])
    else:
        next_query_string = '?$top={}&$skip={}'.format(limit, limit + offset)

    resp = Response()
    resp.headers[b'Content-Type'] = b'application/xml;charset=utf-8'
    resp.data = render_template(
        'collection.xml',
        api_server=api_server,
        api_path=api_path,
        collection=collection,
        entries=entries,
        next_query_string=next_query_string
    )
    return resp


def get_tables(url):
    try:
        req = requests.get(url)
        meta = req.json()
    except:
        meta = {'table': {}}
    return meta['table'].keys()


def get_entries_in_collection(url, collection, limit=100, offset=0, rowid=None):
    if rowid:
        query = 'SELECT rowid, * FROM "{collection}" WHERE rowid={rowid} LIMIT {limit} OFFSET {offset}'.format(
            collection=collection,
            limit=limit,
            offset=offset,
            rowid=rowid
        )
    else:
        query = 'SELECT rowid, * FROM "{collection}" LIMIT {limit} OFFSET {offset}'.format(
            collection=collection,
            limit=limit,
            offset=offset
        )
    rows = requests.get(url, params={'q': query}).json()
    entries = []
    for row in rows:
        entries.append({
            'rowid': row['rowid'],
            'cells': get_cells_in_row(row)
        })
    return entries


def get_cells_in_row(row):
    # `row` should be a dict, where the keys are
    # column names and the values are cell values
    cells = []
    for column, value in row.iteritems():
        cells.append({
            'column': column,
            'value': format_cell_value(value),
            'type': get_cell_type(value)
        })
    return cells


def format_cell_value(value):
    # Jinja gets this mostly right, so we
    # only have to check for date formatting
    if isinstance(value, (str, unicode)):
        try:
            datetime = dateutil.parser.parse(value)
        except:
            return value
        else:
            return datetime.isoformat()
    else:
        return value


def get_cell_type(value):
    if value is None:
        return 'Edm.Null'
    elif isinstance(value, float):
        return 'Edm.Double'
    elif isinstance(value, int):
        if value.bit_length() < 32:
            return 'Edm.Int32'
        else:
            return 'Edm.Int64'
    elif isinstance(value, bool):
        return 'Edm.Boolean'
    elif isinstance(value, (str, unicode)):
        try:
            dateutil.parser.parse(value)
        except:
            return 'Edm.String'
        else:
            return 'Edm.DateTime'
    else:
        return 'Edm.String'


if __name__ == "__main__":
    # Log exceptions to http/log.txt
    logger = logging.getLogger('odata')
    hdlr = logging.FileHandler('/home/http/log.txt')
    logger.addHandler(hdlr)
    logger.setLevel(logging.INFO)
    app.logger.addHandler(hdlr)

    logger.info('about to run CGIHandler')
    logger.info('os.environ = {}'.format(os.environ))

    try:
        CGIHandler().run(app)
    except Exception, e:
        logger.exception("Something went wrong")
