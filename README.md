# Connect with OData

A ScraperWiki.com tool for opening your data in Tableau, QlikView and Excel Power Query.

## How it works

This tool is a thin wrapper that presents an OData URL to the
user in a browser so that they can copy/paste it into Tableau or
other application.

All the hard work of actually generating OData is done by the
[odata-cgi CGI script](https://github.com/scraperwiki/odata-cgi)
which is
[installed globally](https://github.com/scraperwiki/global-cgi).
