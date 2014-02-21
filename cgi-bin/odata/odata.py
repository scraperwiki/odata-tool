#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import requests
from logging import FileHandler
from wsgiref.handlers import CGIHandler
import os

from flask import Flask, Response, render_template, request

app = Flask(__name__)

# Avoid default Flask redirect when a
# URL is requested without a final slash
app.url_map.strict_slashes = False

# Get the "root" url path, because
# Flask isn't running at the domain root
path = os.environ.get('PATH_INFO', '/box/token/cgi-bin/odata')
root = '/'.join(path.split('/')[0:5])

# Stop extra whitespace creeping
# into Jinja templates
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True

request_url = 'https://{}{}'.format(
    os.environ.get('HTTP_HOST', 'server.scraperwiki.com'),
    os.environ.get('PATH_INFO', '/box/token/cgi-bin/odata')
)

def get_dataset_url():
    try:
        with open('/home/dataset_url.txt', 'r') as file:
            return file.read()
    except IOError:
        return None


dataset_url = get_dataset_url()


@app.route(root + "/")
def show_collections():
    tables = get_tables('{}/sql/meta'.format(dataset_url))
    resp = Response()
    resp.headers['Content-Type'] = 'application/xml;charset=utf-8'
    resp.data = render_template('collections.xml', base_url=request_url, collections=tables)
    return resp


@app.route(root + "/<collection>/")
def show_collection(collection):
    if request.args.get('$skiptoken'):
        limit = 100
        offset = int(request.args.get('$skiptoken'))
    else:
        limit = int(request.args.get('$top', 100))
        offset = int(request.args.get('$skip', 0))
    # TODO: check that `collection` table actually exists
    entries = get_entries_in_collection(
        '{}/sql'.format(dataset_url),
        collection,
        limit=limit,
        offset=offset
    )
    if len(entries) != limit:
        next_url = None
    elif request.args.get('$skiptoken'):
        next_url = '{}?$skiptoken={}'.format(request_url, entries[-1]['rowid'])
    else:
        next_url = '{}?$top={}&$skip={}'.format(request_url, limit, limit + offset)
    resp = Response()
    resp.headers['Content-Type'] = 'application/xml;charset=utf-8'
    resp.data = render_template('collection.xml', base_url=request_url, collection=collection, entries=entries, next_url=next_url)
    return resp


def get_tables(url):
    try:
        req = requests.get(url)
        meta = req.json()
    except:
        meta = {'table': {}}
    return meta['table'].keys()


def get_entries_in_collection(url, collection, limit=100, offset=0):
    query = 'SELECT rowid, * FROM "{collection}" LIMIT {limit} OFFSET {offset}'.format(
        collection=collection,
        limit=limit,
        offset=offset
    )
    rows = requests.get(url, params={'q': query}).json()
    entries = []
    for row in rows:
        entries.append({
            'url': u"{}({})".format(request_url, row['rowid']),
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

    CGIHandler().run(app)
