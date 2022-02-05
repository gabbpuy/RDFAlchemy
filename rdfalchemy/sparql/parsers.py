from io import TextIOWrapper
import json
import logging
from struct import unpack
from urllib.request import urlopen, Request

import lxml.etree as ET  # ElementTree API using libxml2
from rdflib import URIRef, Literal, BNode

from rdfalchemy.exceptions import MalformedQueryError, QueryEvaluationError, ParseError

__all__ = ["_JSONSPARQLHandler", "_XMLSPARQLHandler", "_BRTRSPARQLHandler"]

log = logging.getLogger(__name__)


class _SPARQLHandler:

    """
    Abstract base class for parsing the response stream of a sparql query

    Real classes should subclass from here but should **not** do too much
    during `__init__`

    `__init__` should stip after opening the stream and not read so that
    users have the option to call p.stream.read() to get the rawResults
    """
    mimetype = ""

    def __init__(self, url):
        req = Request(url)
        if self.mimetype:
            req.add_header('Accept', self.mimetype)
        self.stream = urlopen(req)


class _JSONSPARQLHandler(_SPARQLHandler):

    """Parse the results of a sparql query returned as json.

    Note: this uses json.load which will consume the entire
    stream before returning any results. The XML handler uses a generator
    type return so it returns the first tuple as soon as it's available
    *without* having to comsume the entire stream
    """
    mimetype = 'application/sparql-results+json'

    def parse(self):
        ret = json.load(
            TextIOWrapper(self.stream),
            encoding=self.stream.info().get_content_charset('utf8'))
        var_names = ret['head']['vars']
        bindings = ret['results']['bindings']
        for bdg in bindings:
            for var, val in bdg.items():
                type = val['type']
                if type == 'uri':
                    bdg[var] = URIRef(val['value'])
                elif type == 'bnode':
                    bdg[var] = BNode(val['value'])
                elif type == 'literal':
                    bdg[var] = Literal(val['value'], lang=val.get('xml:lang'))
                elif type == 'typed-literal':
                    bdg[var] = Literal(val['value'], datatype=val.get('datatype'))
                else:
                    raise AttributeError("Binding type error: %s" % (type))
            yield tuple([bdg.get(var) for var in var_names])


# some constants for parsing the xml tree
_S_NS = "{http://www.w3.org/2005/sparql-results#}"
_VARIABLE = _S_NS + "variable"
_BNODE = _S_NS + "bnode"
_URI = _S_NS + "uri"
_BINDING = _S_NS + "binding"
_LITERAL = _S_NS + "literal"
_HEAD = _S_NS + "head"
_RESULT = _S_NS + "result"
_X_NS = "{http://www.w3.org/XML/1998/namespace}"
_LANG = _X_NS + "lang"


class _XMLSPARQLHandler(_SPARQLHandler):

    """
    Parse the results of a sparql query returned as xml.

    Note: returns a generator so that the first tuple is
    available as soon as it is sent.  This does **not** need to consume
    the entire results stream before returning results (that's a good
    thing :-).
    """
    mimetype = 'application/sparql-results+xml'

    def parse(self):
        var_names = []
        bindings = []
        events = iter(ET.iterparse(self.stream, events=('start', 'end')))
        # lets gather up the variable names in head
        for (event, node) in events:
            if event == 'start' and node.tag == _VARIABLE:
                var_names.append(node.get('name'))
            elif event == 'end' and node.tag == _HEAD:
                break
        # now let's yield each result as we parse them
        for (event, node) in events:
            if event == 'start':
                if node.tag == _BINDING:
                    idx = var_names.index(node.get('name'))
                elif node.tag == _RESULT:
                    bindings = [None, ] * len(var_names)
            elif event == 'end':
                if node.tag == _URI:
                    bindings[idx] = URIRef(node.text)
                elif node.tag == _BNODE:
                    bindings[idx] = BNode(node.text)
                elif node.tag == _LITERAL:
                    bindings[idx] = Literal(node.text or '',
                                            datatype=node.get('datatype'),
                                            lang=node.get(_LANG))
                elif node.tag == _RESULT:
                    node.clear()
                    yield tuple(bindings)


class _BRTRSPARQLHandler(_SPARQLHandler):

    """
    Handler for the sesame binary table format BRTR_

    .. _BRTR: http://www.openrdf.org/doc/sesame/api/org/openrdf
    /sesame/query/BinaryTableResultConstants.html
    """
    mimetype = "application/x-binary-rdf-results-table"

    def read_int(self):
        return unpack('>i', self.stream.read(4))[0]

    def read_str(self):
        line = self.read_int()
        return self.stream.read(line).decode("utf-8")

    def parse(self):
        if self.stream.read(4) != b'BRTR':
            raise ParseError("First 4 bytes in should be BRTR")
        self.ver = self.read_int()  # ver of protocol
        self.ncols = self.read_int()
        self.keys = tuple(self.read_str() for x in range(self.ncols))
        self.values = [None, ] * self.ncols
        self.ns = {}
        while True:
            for i in range(self.ncols):
                val = self.get_val()
                if val == 1:  # REPEAT here is like skip..
                    continue  # the val is already in self.values[i]
                self.values[i] = val
            yield tuple(self.values)

    def get_val(self):
        while True:
            rtype = ord(self.stream.read(1))
            if rtype == 0:  # NULL
                return None
            elif rtype == 1:  # REPEAT
                return 1
            elif rtype == 2:  # NAMESPACE
                nsid = self.read_int()
                url = self.read_str()
                self.ns[nsid] = url
            elif rtype == 3:  # QNAME
                nsid = self.read_int()
                localname = self.read_str()
                return URIRef(self.ns[nsid] + localname)
            elif rtype == 4:  # URI
                return URIRef(self.read_str())
            elif rtype == 5:  # BNODE
                return BNode(self.read_str())
            elif rtype == 6:  # PLAIN LITERAL
                return Literal(self.read_str())
            elif rtype == 7:  # LANGUAGE LITERAL
                lit = self.read_str()
                lang = self.read_str()
                return Literal(lit, lang=lang)
            elif rtype == 8:  # DATATYPE LITERAL
                lit = self.read_str()
                datatype = self.get_val()
                return Literal(lit, datatype=datatype)
            elif rtype == 126:  # ERROR
                errType = ord(self.stream.read(1))
                errStr = self.read_str()
                if errType == 1:
                    raise MalformedQueryError(errStr)
                elif errType == 2:
                    raise QueryEvaluationError(errStr)
                else:
                    raise errStr
            elif rtype == 127:  # EOF
                raise StopIteration()
            else:
                raise ParseError("Undefined record type: %s" % rtype)
