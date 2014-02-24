# Connect with OData

A ScraperWiki tool for opening your data in Tableau, QlikView and Excel Power Query.

## How it works

When the tool is first installed, it records the source dataset url and `pip install`s Flask. The OData endpoint is generated via a CGI script.

## Tests

Unit tests for the CGI script are stored in `/cgi-bin/odata`. You can run them with `nosetest` or `specloud`, like so:

```
cd tool/cgi-bin/odata
specloud
```

## Debugging 500 errors

The Python CGIHandler() we use often soaks up exceptions, making debugging 500 server errors particularly tricky. Try SSHing into your development dataset and running this, to see what's going wrong:

```
SERVER_NAME=premium.scraperwiki.com SERVER_PORT=80 REQUEST_METHOD=GET REQUEST_URI='/dqx2xyq/publishToken/cgi-bin/odata' PATH_INFO='/dqx2xyq/publishToken/cgi-bin/odata' tool/cgi-bin/odata/odata.py
```
