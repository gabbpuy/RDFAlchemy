from io import TextIOWrapper
import json
import logging
import os
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen, Request

# from rdfalchemy import Literal, BNode, Namespace, URIRef
from rdfalchemy.sparql import SPARQLGraph, DumpSink
from rdfalchemy.sparql.parsers import (
    _BRTRSPARQLHandler,
    _XMLSPARQLHandler,
    _JSONSPARQLHandler
)
from rdflib.plugins.serializers.nt import _quoteLiteral
from rdflib.plugins.parsers.ntriples import NTParser as NTriplesParser

__all__ = ["SesameGraph"]

log = logging.getLogger(__name__)


class SesameGraph(SPARQLGraph):

    """
    openrdf-sesame graph via http

    Uses the sesame2 HTTP communication protocol
    to provide rdflib type api constructor takes http endpoint and repository
    name e.g.
    SesameGraph('http://www.openvest.org:8080/sesame/repositories/Test')
    """

    parsers = {'xml': _XMLSPARQLHandler,
               'json': _JSONSPARQLHandler,
               'brtr': _BRTRSPARQLHandler}

    def __init__(self, url, context=None):
        super().__init__(url, context)
        self._namespaces = None
        self._contexts = None

    @property
    def namespaces(self):
        """
        Namespaces dict
        """
        if self._namespaces:
            return self._namespaces

        req = Request(self.url + '/namespaces')
        req.add_header('Accept', 'application/sparql-results+json')
        log.debug("opening url: %s\n  with headers: %s" %
                  (req.get_full_url(), req.header_items()))

        ret = json.load(TextIOWrapper(urlopen(req), encoding='utf8'))
        bindings = ret['results']['bindings']
        self._namespaces = dict([(b['prefix']['value'], b[
                                'namespace']['value']) for b in bindings])
        return self._namespaces

    @property
    def contexts(self):
        """
        context items ... pretty slow
        """
        if self._contexts:
            return self._contexts

        req = Request(self.url + '/contexts')
        req.add_header('Accept', 'application/sparql-results+json')
        ret = json.load(TextIOWrapper(urlopen(req), encoding='utf8'))

        bindings = ret['results']['bindings']
        self._contexts = [(b['contextID']['value']) for b in bindings]
        return self._contexts

    def _statement_encode(self, xxx_todo_changeme, context):
        """
        helper function to encode triples to sesame statement uri's
        """
        (s, p, o) = xxx_todo_changeme
        query = {}
        url = self.url + '/statements'
        if s:
            query['subj'] = s.n3().encode('utf8')
        if p:
            query['pred'] = p.n3()
        if o:
            query['obj'] = _quoteLiteral(o.n3())
            # o.n3()
            # quote_plus(o.n3().encode("utf-8"))
        if context:
            # TODO FIXME what about bnodes like _:adf23123
            query['context'] = "<%s>" % context
        if query:
            url = url + "?" + urlencode(query)
        return url

    def add(self, xxx_todo_changeme1, context=None):
        """
        Add a triple with optional context
        """
        (s, p, o) = xxx_todo_changeme1
        url = self.url + '/statements'
        ctx = context or self.context
        if ctx:
            url = url + "?" + urlencode(dict(context=ctx))
        req = Request(url)
        # req.data = "%s %s %s .\n" % (
        #     s.n3(), p.n3(), _xmlcharref_encode(o.n3()))
        req.data = "<%s> %s %s .\n" % (s, p.n3(), o.n3())
        req.add_header('Content-Type', 'text/rdf+n3')
        try:
            result = urlopen(req).read()
        except HTTPError as e:
            if e.code == 204:
                return
            else:
                log.error(e)
        return result

    def remove(self, xxx_todo_changeme2, context=None):
        """
        Remove a triple from the graph

        If the triple does not provide a context attribute, removes the triple
        from all contexts.
        """
        (s, p, o) = xxx_todo_changeme2
        url = self._statement_encode((s, p, o), context)
        req = Request(url)
        req.get_method = lambda: 'DELETE'
        try:
            result = urlopen(req).read()
        except HTTPError as e:
            if e.code == 204:
                return
            else:
                log.error(e)
        return result

    def triples(self, xxx_todo_changeme3, context=None):
        """
        Generator over the triple store

        Returns triples that match the given triple pattern. If triple pattern
        does not provide a context, all contexts will be searched.
        """
        (s, p, o) = xxx_todo_changeme3
        url = self._statement_encode((s, p, o), context)
        req = Request(url)
        req.add_header('Accept', 'text/plain')
                       # N-Triples is best for generator (one line per triple)
        log.debug("Request: %s" % req.get_full_url())
        dumper = DumpSink()
        parser = NTriplesParser(dumper)

        for l in urlopen(req):
            log.debug('line: %s' % l)
            parser.parsestring(l)
            yield dumper.get_triple()

    def __len__(self):
        """Returns the number of triples in the graph
        calls http://{self.url}/size  very fast
        """
        return int(urlopen(self.url + "/size").read())

    def set(self, xxx_todo_changeme4):
        """Convenience method to update the value of object

        Remove any existing triples for subject and predicate before adding
        (subject, predicate, object).
        """
        (subject, predicate, object) = xxx_todo_changeme4
        self.remove((subject, predicate, None))
        self.add((subject, predicate, object))

    def qname(self, uri):
        """turn uri into a qname given self.namespaces"""
        for p, n in self.namespaces.items():
            if uri.startswith(n):
                return "%s:%s" % (p, uri[len(n):])
        return uri

    def query(
            self, str_or_query, init_bindings={}, init_ns={},
            result_method="brtr", processor="sparql", raw_results=False):
        """
        Executes a SPARQL query against this Graph

        :param str_or_query: Is either a string consisting of the SPARQL query
        :param init_bindings: *optional* mapping from a Variable to an RDFLib
            term (used as initial bindings for SPARQL query)
        :param init_ns: optional mapping from a namespace prefix to a namespace
        :param result_method: results query requested (must be 'xml', 'json'
            or 'brtr')
         xml streams over the result set and json must read the entire set
            to succeed
        :param processor: The kind of RDF query (must be 'sparql' or 'serql')
        :param raw_results: If set to `True`, returns the raw xml or json
            stream rather than the parsed results.
        """
        # same method as super with different result_method default
        return super(SesameGraph, self).query(
            str_or_query, init_bindings, init_ns,
            result_method, processor, raw_results)

    def parse(self, source, publicID=None, format="xml", method='POST'):
        """
        Parse source into Graph

        Graph will get loaded into it's own context (sub graph).
        Format defaults to 'xml' (AKA: rdf/xml).

        :returns: Returns the context into which  the source was parsed.

        :param source: source file in the form of
            "http://....." or "~/dir/file.rdf"
        :param publicID: *optional* the logical URI if it's different
            from the physical source URI.
        :param format: must be one of 'xml' or 'n3'
        :param method: must be one of

          * 'POST' -- method adds data to a context
          * 'PUT' -- method replaces data in a context
        """
        url = self.url + '/statements'
        if not (source.startswith('http://') or source.startswith('file://')):
            source = 'file://' + os.path.abspath(os.path.expanduser(source))

        ctx = "<%s>" % (publicID or source)
        url = url + "?" + urlencode(dict(context=ctx))

        req = Request(url)
        req.get_method = lambda: method

        if format == 'xml':
            req.add_header('Content-Type', 'application/rdf+xml')
        elif format == 'n3':
            req.add_header('Content-Type', 'text/rdf+n3')
        else:
            raise "Unknown format: %s" % format

        req.data = urlopen(source).read()
        log.debug("Request: %s" % req.get_full_url())
        try:
            result = urlopen(req).read()
            log.debug("Result: " + result)
        except HTTPError as e:
            # 204 is actually the "success" code
            if e.code == 204:
                return
            log.error(e)
            raise e
        return result

    def load(self, source, publicID=None, format="xml"):
        self.parse(source, publicID, format)
