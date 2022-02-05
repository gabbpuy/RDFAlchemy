"""
"""
import logging
import re
from urllib.request import urlopen, Request
from urllib.error import HTTPError
from urllib.parse import urlencode

from rdflib import URIRef, Literal, BNode, RDF, RDFS
from rdfalchemy.exceptions import (
    MalformedQueryError,
    UniquenessError,
    # QueryEvaluationError,
)
from rdfalchemy.sparql.parsers import (
    _XMLSPARQLHandler,
    _JSONSPARQLHandler,
)

from rdflib import ConjunctiveGraph


__all__ = ["SPARQLGraph"]

log = logging.getLogger(__name__)


class DumpSink(object):

    def __init__(self):
        self.length = 0
        self._triple = tuple()

    def triple(self, s, p, o):
        self.length += 1
        self._triple = (s, p, o)

    def get_triple(self):
        return self._triple


class SPARQLGraph:

    """
    Provides (some) RDFLib API via http to a SPARQL endpoint.

    Gives 'read-only' access to the graph.

    Constructor takes http endpoint and repository name

    e.g.  SPARQLGraph('http://localhost:2020/sparql')
    """

    parsers = {'xml': _XMLSPARQLHandler, 'json': _JSONSPARQLHandler}

    def __init__(self, url, context=None):
        self.url = url
        self.context = context

    def construct(self, strOrTriple, initBindings=None, initNs=None):
        """
        Executes a SPARQL Construct
        :param strOrTriple: can be either

          * a string in which case it it considered a CONSTRUCT query
          * a triple in which case it acts as the rdflib `triples((s,p,o))`

        :param initBindings:  A mapping from a Variable to an RDFLib term
        (used as initial bindings for SPARQL query)
        :param initNs:  A mapping from a namespace prefix to a namespace

        :returns: an instance of rdflib.ConjuctiveGraph('IOMemory')
        """
        if initNs is None:
            initNs = {}
        if initBindings is None:
            initBindings = {}
        if isinstance(strOrTriple, str):
            query = strOrTriple
            if initNs:
                prefixes = ''.join(["prefix %s: <%s>\n" % (
                    p, n) for p, n in initNs.items()])
                query = prefixes + query
        else:
            s, p, o = strOrTriple
            t = '%s %s %s' % (
                (s and s.n3() or '?s'),
                (p and p.n3() or '?p'),
                (o and o.n3() or '?o'))
            query = 'construct {%s} where {%s}' % (t, t)
        query = dict(query=query)

        url = self.url + "?" + urlencode(query)
        req = Request(url)
        req.add_header('Accept', 'application/rdf+xml')
        log.debug("Request url: %s\n  with headers: %s" %
                  (req.get_full_url(), req.header_items()))
        subgraph = ConjunctiveGraph('IOMemory')
        subgraph.parse(urlopen(req))
        return subgraph

    def triples(self, triple, method='CONSTRUCT'):
        """
        :param triple: select triple criteria tuple
        :param method: must be 'CONSTRUCT' or 'SELECT'

             * CONSTRUCT calls CONSTRUCT query and returns a Graph result
             * SELECT calls a SELECT query and returns an interator streaming
               over the results

        Use SELECT if you expect a large result set or may consume less than
        the entire result

        :returns: a generator over triples matching the pattern
        """
        (s, p, o) = triple
        if method == 'CONSTRUCT':
            return self.construct((s, p, o)).triples((None, None, None))
        elif method == 'SELECT':
            pattern = "%s %s %s" % (
                (s and s.n3() or '?s'),
                (p and p.n3() or '?p'),
                (o and o.n3() or '?o'))
            query = "select ?s ?p ?o where { %s . }" % pattern
            return self.query(query)
        else:
            raise ValueError("Unknown method: %s" % method)

    def __iter__(self):
        """
        Iterates over all triples in the store
        """
        return self.triples((None, None, None))

    def __contains__(self, triple):
        """
        Support for 'triple in graph' syntax
        """
        for triple in self.triples(triple):
            return 1
        return 0

    def subjects(self, predicate=None, object=None):
        """
        A generator of subjects with the given predicate and object
        """
        for s, p, o in self.triples((None, predicate, object)):
            yield s

    def predicates(self, subject=None, object=None):
        """
        A generator of predicates with the given subject and object
        """
        for s, p, o in self.triples((subject, None, object)):
            yield p

    def objects(self, subject=None, predicate=None):
        """
        A generator of objects with the given subject and predicate
        """
        for s, p, o in self.triples((subject, predicate, None)):
            yield o

    def subject_predicates(self, object=None):
        """
        A generator of (subject, predicate) tuples for the given object
        """
        for s, p, o in self.triples((None, None, object)):
            yield s, p

    def subject_objects(self, predicate=None):
        """
        A generator of (subject, object) tuples for the given predicate
        """
        for s, p, o in self.triples((None, predicate, None)):
            yield s, o

    def predicate_objects(self, subject=None):
        """
        A generator of (predicate, object) tuples for the given subject
        """
        for s, p, o in self.triples((subject, None, None)):
            yield p, o

    def value(self, subject=None, predicate=RDF.value, object=None, default=None, any=True):
        """
        Get a value for a pair of two criteria

        Exactly one of subject, predicate, object must be None. Useful if one
        knows that there may only be one value.

        It is one of those situations that occur a lot, hence this *macro* like
        utility

        :param  subject, predicate, object: exactly one must be None
        :param default: value to be returned if no values found
        :param any: if more than one answer return **any one** answer,
            otherwise `raise UniquenessError`
        """
        if (subject is None and (predicate is None or object is None)) or (predicate is None and object is None):
            return None

        if object is None:
            values = self.objects(subject, predicate)
        if subject is None:
            values = self.subjects(predicate, object)
        if predicate is None:
            values = self.predicates(subject, object)

        try:
            retval = next(values)
        except StopIteration:
            retval = default
        else:
            if any is False:
                try:
                    next = next(values)
                    assert next
                    msg = ("While trying to find a value for (%s, %s, %s) the "
                           "following multiple values where found:\n" %
                           (subject, predicate, object))
                    triples = self.triples((subject, predicate, object))
                    for (s, p, o) in triples:
                        msg += "(%s, %s, %s)\n" % (s, p, o)
                    raise UniquenessError(msg)
                except StopIteration:
                    pass
        return retval

    def label(self, subject, default=''):
        """
        Query for the RDFS.label of the subject

        Return default if no label exists
        """
        if subject is None:
            return default
        return self.value(subject, RDFS.label, default=default, any=True)

    def comment(self, subject, default=''):
        """
        Query for the RDFS.comment of the subject

        Return default if no comment exists
        """
        if subject is None:
            return default
        return self.value(subject, RDFS.comment, default=default, any=True)

    def items(self, items):
        """
        Generator over all items in the resource specified by items

        items is an RDF collection.
        """
        while items:
            item = self.value(items, RDF.first)
            if item:
                yield item
            items = self.value(items, RDF.rest)

    def transitive_objects(self, subject, property, remember=None):
        """
        Transitively generate objects for the `property` relationship

        Generated objects belong to the depth first transitive closure of the
        `property` relationship starting at `subject`.
        """
        if remember is None:
            remember = {}
        if subject in remember:
            return
        remember[subject] = 1
        yield subject
        for obj in self.objects(subject, property):
            yield from self.transitive_objects(obj, property, remember)

    def transitive_subjects(self, predicate, object, remember=None):
        """
        Transitively generate objects for the `property` relationship

        Generated objects belong to the depth first transitive closure of the
        `property` relationship starting at `subject`.
        """
        if remember is None:
            remember = {}
        if object in remember:
            return
        remember[object] = 1
        yield object
        for subject in self.subjects(predicate, object):
            yield from self.transitive_subjects(predicate, subject, remember)

    def qname(self, uri):
        """
        Turn uri into a qname, given self.namespaces

        This works for rdflib graphs and is defined for SesameGraph
        but is **not** part of SPARQLGraph
        """
        raise NotImplementedError

    def query(self, str_or_query, init_bindings=None, init_ns=None, result_method="xml", processor="sparql",
              raw_results=False):
        """
        Executes a SPARQL query against this Graph

        :param str_or_query: Is either a string consisting of the SPARQL query
        :param init_bindings: *optional* mapping from a Variable to an RDFLib
            term (used as initial bindings for SPARQL query)
        :param init_ns: optional mapping from a namespace prefix to a namespace
        :param result_method: results query requested (must be 'xml' or 'json')
         xml streams over the result set and json must read the entire set to
            succeed
        :param processor: The kind of RDF query (must be 'sparql' or 'serql')
        :param raw_results: If set to `True`, returns the raw xml or json
            stream rather than the parsed results.
        """
        if init_ns is None:
            init_ns = {}
        if init_bindings is None:
            init_bindings = {}
        log.debug("Raw Query: %s", str_or_query)
        prefixes = ''.join("prefix %s: <%s>\n" % (p, n) for p, n in init_ns.items())

        if init_bindings:
            query = self._processInitBindings(
                str_or_query, init_bindings)
        else:
            query = str_or_query
        query = prefixes + query
        log.debug("Prepared Query: %s",  query)
        query = dict(query=query, queryLn=processor)
        url = self.url + "?" + urlencode(query)
        parser = self.get_parser(result_method, url)

        return raw_results and parser.stream or parser.parse()

    def get_parser(self, result_method, url):
        try:
            return self.parsers[result_method](url)
        except LookupError:
            raise ValueError("Invalid result_method: %s" % result_method)
        except HTTPError as e:
            if e.code == 400:  # and e.msg.startswith('Parse_error'):
                errmsg = e.fp.read()
                submsg = re.search("<pre>(.*)</pre>", errmsg, re.MULTILINE | re.DOTALL)
                submsg = submsg and submsg.groups()[0]
                raise MalformedQueryError(submsg or errmsg)
            raise e

    @classmethod
    def _processInitBindings(cls, query, init_bindings):
        """
        _processInitBindings will convert a query by replacing the Variables

        >>> SPARQLGraph._processInitBindings(
        ...     'SELECT ?x { ?x ?y ?z }', {'z' : 'hi'})
        u'SELECT ?x { ?x ?y "hi" }'
        >>> SPARQLGraph._processInitBindings(
        ...     'SELECT ?x { ?x <http://example/?z=1> ?z }', {'z' : 'hi'})
        u'SELECT ?x { ?x <http://example/?z=1> "hi" }'

        :param query: the query to process
        :param init_bindings: a dict of variable to value"""
        # TODO: what if a BNode is the val in the bindings
        #       should it be left at a ?var or converted to a _:bnode ???
        def varval(x):
            var = x.groups()[0]
            if var in init_bindings:
                val = init_bindings[var]
                try:
                    return val.n3()
                except:
                    return Literal(val).n3()
            return x.group()

        re_qvars = re.compile('(?<=[\]\.\;\{\s])\?(%s)' % (
            '|'.join(init_bindings.keys())))
        return re_qvars.sub(varval, query)

    def describe(self, s_or_po, init_bindings=None, init_ns=None):
        """
        Executes a SPARQL describe of resource

        :param s_or_po:  is either

          * a subject ... should be a URIRef
          * a tuple of (predicate,object) ... pred should be inverse functional
          * a describe query string

        :param init_bindings: A mapping from a Variable to an RDFLib term (used
            as initial bindings for SPARQL query)
        :param init_ns: A mapping from a namespace prefix to a namespace
        """
        if init_ns is None:
            init_ns = {}
        if init_bindings is None:
            init_bindings = {}
        if isinstance(s_or_po, str):
            query = s_or_po
            if init_ns:
                prefixes = ''.join(["prefix %s: <%s>\n" % (p, n)
                                    for p, n in init_ns.items()])
                query = prefixes + query
        elif isinstance(s_or_po, URIRef) or isinstance(s_or_po, BNode):
            query = "describe %s" % (s_or_po.n3())
        else:
            p, o = s_or_po
            query = "describe ?s where {?s %s %s}" % (p.n3(), o.n3())
        query = dict(query=query)

        url = self.url + "?" + urlencode(query)
        req = Request(url)
        req.add_header('Accept', 'application/rdf+xml')
        log.debug("opening url: %s\n  with headers: %s" %
                  (req.get_full_url(), req.header_items()))
        subgraph = ConjunctiveGraph()
        subgraph.parse(urlopen(req))
        return subgraph
