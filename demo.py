#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
This is a demo.
The real code would produce a html file to quickly cross-check CORE and subjects.
Example: http://www-library.desy.de/lists/misc/slp99.html
"""
def perform_inspire_search(query, facets=None, collection="literature"):
    """Perform the search query on INSPIRE.

    Args:
        query (str): the query to perform
        facets (dict): mapping of facet filters to values
        collection (str): collection to search in

    Yields:
        the json response for every record.
    """
    import requests

    INSPIRE_API_ENDPOINT = "https://labs.inspirehep.net/api"

    facets = facets or {}
    response = requests.get(
    "%s/%s" % (INSPIRE_API_ENDPOINT,collection), params={"q": query}, verify=False
    ) 
#    f"{INSPIRE_API_ENDPOINT}/{collection}", params={"q": query, **facets}

    response.raise_for_status()
    content = response.json()

    for result in content["hits"]["hits"]:
        yield result

    while "next" in content.get("links", {}):
        response = requests.get(content["links"]["next"], verify=False)
        response.raise_for_status()
        content = response.json()

        for result in content["hits"]["hits"]:
            yield result

def get_conf_list(query):
    "print info about conferences"""
    
    collection="conferences"
    results = perform_inspire_search(query, collection="conferences")
   
    for result in results: 
        meta = result["metadata"]
        recid = meta["control_number"]
        cnum = meta.get("cnum")
        core = meta.get("core")
       
        # this should not get the alternative_titles:title
        titles = []  
        if meta.get("titles"):
            for title in meta.get("titles"):
                if title.get("title"):
                    fulltitle = title.get("title")
                else:
                    fulltitle = ''
                if title.get("subtitle"):
                    fulltitle += ': %s' % title.get("subtitle")
                titles.append(fulltitle)
        title = '; '.join(titles) 
        if meta.get("acronyms"):
            title += ' (%s)' % (', '.join(meta.get("acronyms")), )
        print '\n%s - %s' % (recid, cnum)
        print title

def main():
    startdate = '2020-02-02'
    stopdate = '2020-02-04'
    query = "_created:[%s TO %s]" % (startdate,stopdate)
    get_conf_list(query)
    
if __name__ == "__main__":
    main()
