from abc import abstractmethod, ABCMeta
from enum import IntEnum
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


class _BRTR_Type(IntEnum):
    Null = 0
    Repeat = 1
    Namespace = 2
    Qname = 3
    URI = 4
    Bnode = 5
    PlainLiteral = 6
    LanguageLiteral = 7
    DataLiteral = 8
    Error = 126
    EOF = 127


class _SPARQLHandler(metaclass=ABCMeta):

    """
    Abstract base class for parsing the response stream of a sparql query

    Real classes should subclass from here but should **not** do too much
    during `__init__`

    `__init__` should stop after opening the stream and not read so that
    users have the option to call p.stream.read() to get the rawResults
    """
    mimetype = ""

    def __init__(self, url):
        req = Request(url)
        if self.mimetype:
            req.add_header('Accept', self.mimetype)
        self.stream = urlopen(req)

    @abstractmethod
    def parse(self):
        pass


class _JSONSPARQLHandler(_SPARQLHandler):

    """
    Parse the results of a sparql query returned as json.

    Note: this uses `json.load` which will consume the entire
    stream before returning any results. The XML handler uses a generator
    type return so it returns the first tuple as soon as it's available
    *without* having to consume the entire stream
    """
    mimetype = 'application/sparql-results+json'

    def parse(self):
        ret = json.load(TextIOWrapper(self.stream), encoding=self.stream.info().get_content_charset('utf8'))
        var_names = ret['head']['vars']
        bindings = ret['results']['bindings']
        for bdg in bindings:
            for var, val in bdg.items():
                triple_type = val['type']
                if triple_type == 'uri':
                    bdg[var] = URIRef(val['value'])
                elif triple_type == 'bnode':
                    bdg[var] = BNode(val['value'])
                elif triple_type == 'literal':
                    bdg[var] = Literal(val['value'], lang=val.get('xml:lang'))
                elif triple_type == 'typed-literal':
                    bdg[var] = Literal(val['value'], datatype=val.get('datatype'))
                else:
                    raise AttributeError(f"Binding type error: {triple_type}")
            yield tuple(bdg.get(var) for var in var_names)


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
        idx = 0
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

    .. _BRTR: https://www.openrdf.org/doc/sesame/api/org/openrdf
    /sesame/query/BinaryTableResultConstants.html
    """
    mimetype = "application/x-binary-rdf-results-table"

    def __init__(self, url):
        super().__init__(url)
        self.ns = {}

    def read_int(self):
        return unpack('>i', self.stream.read(4))[0]

    def read_str(self):
        line = self.read_int()
        return self.stream.read(line).decode("utf-8")

    def parse(self):
        if self.stream.read(4) != b'BRTR':
            raise ParseError("First 4 bytes in should be BRTR")
        _ver = self.read_int()  # ver of protocol
        number_columns = self.read_int()
        _keys = tuple(self.read_str() for _ in range(number_columns))
        values = [None, ] * number_columns
        self.ns = {}

        while True:
            for i in range(number_columns):
                val = self.get_val()
                if val == 1:  # REPEAT here is like skip..
                    continue  # the val is already in self.values[i]
                values[i] = val
            yield tuple(values)

    def get_val(self):
        while True:
            rtype = ord(self.stream.read(1))
            if rtype == _BRTR_Type.Null:
                return None
            elif rtype == _BRTR_Type.Repeat:
                return 1
            elif rtype == _BRTR_Type.Namespace:
                namespace_id = self.read_int()
                url = self.read_str()
                self.ns[namespace_id] = url
            elif rtype == _BRTR_Type.Qname:
                namespace_id = self.read_int()
                local_name = self.read_str()
                return URIRef(self.ns[namespace_id] + local_name)
            elif rtype == _BRTR_Type.URI:
                return URIRef(self.read_str())
            elif rtype == _BRTR_Type.Bnode:
                return BNode(self.read_str())
            elif rtype == _BRTR_Type.PlainLiteral:
                return Literal(self.read_str())
            elif rtype == _BRTR_Type.LanguageLiteral:
                lit = self.read_str()
                lang = self.read_str()
                return Literal(lit, lang=lang)
            elif rtype == _BRTR_Type.DataLiteral:
                lit = self.read_str()
                datatype = self.get_val()
                return Literal(lit, datatype=datatype)
            elif rtype == _BRTR_Type.Error:  # ERROR
                errType = ord(self.stream.read(1))
                errStr = self.read_str()
                if errType == 1:
                    raise MalformedQueryError(errStr)
                elif errType == 2:
                    raise QueryEvaluationError(errStr)
                else:
                    raise errStr
            elif rtype == _BRTR_Type.EOF:  # EOF
                raise StopIteration()
            else:
                raise ParseError(f"Undefined record type: {rtype}")
