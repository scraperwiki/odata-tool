#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import requests
from logging import FileHandler
from wsgiref.handlers import CGIHandler
import os

from flask import Flask, Response, render_template, request

app = Flask(__name__)

# Log exceptions to http/error.txt
logger = FileHandler('/home/http/error.txt')
logger.setLevel(logging.WARNING)
app.logger.addHandler(logger)

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
        with open('../../dataset_url.txt', 'r') as file:
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


def get_tables(url):
    try:
        req = requests.get(url)
        meta = req.json()
    except:
        meta = {'table': {}}
    return meta['table'].keys()


if __name__ == "__main__":
    CGIHandler().run(app)
