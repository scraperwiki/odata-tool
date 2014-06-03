#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import dateutil.parser
import logging
import os
import re
import requests

from flask import Flask, Response, render_template, request
from logging import FileHandler
from wsgiref.handlers import CGIHandler

HOME = os.environ.get("HOME", "/home")

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
        with open(HOME + '/dataset_url.txt', 'r') as file:
            return file.read().strip()
    except IOError:
        return None

dataset_url = get_dataset_url()


@app.route(api_path + "/")
def show_collections():
    tables = get_tables('{}/sql/meta'.format(dataset_url))
    if tables is None:
        return Response("Error reading tables", 500)
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

    # Handle specific row requests
    rowid_match = re.search(r'^(.*)[(](\d+)[)]$', collection)
    if rowid_match:
        collection = rowid_match.group(1)
        rowid = int(rowid_match.group(2))
    else:
        rowid = None

    # Check that the table exists
    tables = get_tables('{}/sql/meta'.format(dataset_url))
    if collection not in tables:
        resp = Response()
        resp.headers[b'Content-Type'] = b'application/xml;charset=utf-8'
        resp.data = render_template(
            'error.xml',
            message="Resource not found for the segment '{}'.".format(collection)
        )
        return resp

    # Handle pagination
    if request.args.get('$skiptoken'):
        limit = 500
        offset = int(request.args.get('$skiptoken'))
    else:
        limit = int(request.args.get('$top', 500))
        offset = int(request.args.get('$skip', 0))

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
    req = requests.get(url)
    if req.status_code != 200:
        logger.warning("Unable to get_tables(): {.status_code}".format(req))
        return None
    meta = req.json()
    return meta['table'].keys()


def get_entries_in_collection(url, collection, limit=500, offset=0, rowid=None):
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
            'column_safe': escape_column_name(column),
            'value': format_cell_value(value),
            'type': get_cell_type(value)
        })
    return cells


def escape_column_name(name):
    # returns a version of `name` that is
    # safe to use in as an XML tag name
    if re.match(r'([^a-z]|xml)', name, flags=re.IGNORECASE):
        safe_name = 'x'
    else:
        safe_name = ''
    capitalise_next = False
    for char in name:
        if char in ' -_=()[]}{|+&/\\':
            # ignore this character,
            # and capitalise the next one
            capitalise_next = True
        elif char in '"\'':
            # just ignore this character
            pass
        else:
            if capitalise_next:
                safe_name += char.upper()
                capitalise_next = False
            else:
                safe_name += char
    return safe_name


def format_cell_value(value):
    # Jinja gets this mostly right, so we
    # only have to check for date formatting
    if is_datey(value):
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
    elif isinstance(value, bool):
        return 'Edm.Boolean'
    elif isinstance(value, float):
        return 'Edm.Double'
    elif isinstance(value, int):
        if value.bit_length() < 32:
            return 'Edm.Int32'
        else:
            return 'Edm.Int64'
    elif is_datey(value):
        return 'Edm.DateTime'
    else:
        return 'Edm.String'

import re

DATELIKE_RE = re.compile(
    "\d{2}(?:\d{2})?[/-]?\d{1,2}[/-]?\d{1,2}" # date
    "[T ]"
    "\d{2}:?\d{2}(?::?\d{2})?" # time
    "(?:Z|[-+]\d{2}(:?\d{2})?)?" # timezone
)

def is_datey(value):
    if not isinstance(value, (str, unicode)):
        return False

    if value in " -'":
        return False
    elif isint(value):
        return False
    elif isfloat(value):
        return False

    if DATELIKE_RE.match(value) is not None:
        return True

    return False

def isint(value):
    try:
        int(value)
        return True
    except ValueError:
        return False

def isfloat(value):
    try:
        float(value)
        return True
    except ValueError:
        return False


if __name__ == "__main__":
    # Log exceptions to http/log.txt
    logger = logging.getLogger('odata')
    hdlr = logging.FileHandler(HOME + '/http/log.txt')
    logger.addHandler(hdlr)
    logger.setLevel(logging.INFO)
    app.logger.addHandler(hdlr)

    try:
        CGIHandler().run(app)
    except Exception, e:
        logger.exception("Something went wrong")
