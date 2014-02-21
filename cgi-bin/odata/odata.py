#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
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


@app.route(root + "/")
def show_collections():
    tables = get_tables()
    resp = Response()
    resp.headers['Content-Type'] = 'application/xml;charset=utf-8'
    resp.data = render_template('collections.xml', base_url=request_url, collections=tables)
    return resp


def get_tables():
    # This function should call the sql meta endpoint
    return []


if __name__ == "__main__":
    CGIHandler().run(app)
