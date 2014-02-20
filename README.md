# Connect with OData

A ScraperWiki tool for opening your data in Tableau, QlikView and Excel Power Query.

## How it works

When the tool is first installed, it records the source dataset url and `pip install`s Flask. The OData endpoint is generated via a CGI script.

## Tests

Unit tests for the CGI script are stored in `/test`. You can run them with `nosetest` or `specloud`.
